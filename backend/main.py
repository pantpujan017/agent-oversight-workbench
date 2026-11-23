
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from executor import execute_file_action
from ai_service import generate_action_proposal


app = FastAPI(
    title="AI Agent Oversight Workbench",
    description="Backend API for supervising AI agent actions",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# Database file inside the backend folder.
DB_PATH = Path(__file__).resolve().parent / "oversight.db"


# Open and safely close a database connection.
@contextmanager
def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# Create database tables and update existing database columns.
def initialize_database():
    with get_db_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                tool TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('pending', 'approved', 'rejected'))
            )
        """)

        # Add execution columns to existing databases when needed.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(actions)"
            ).fetchall()
        }

        if "execution_status" not in columns:
            connection.execute("""
                ALTER TABLE actions
                ADD COLUMN execution_status TEXT NOT NULL
                DEFAULT 'not_started'
                CHECK (
                    execution_status IN (
                        'not_started', 'running', 'completed', 'failed'
                    )
                )
            """)

        if "execution_message" not in columns:
            connection.execute("""
                ALTER TABLE actions
                ADD COLUMN execution_message TEXT NOT NULL DEFAULT ''
            """)

        # Decision history.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                decision TEXT NOT NULL
                    CHECK(decision IN ('approved', 'rejected')),
                decided_at TEXT NOT NULL
            )
        """)

        # File execution history.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                tool TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('completed', 'failed')),
                message TEXT NOT NULL,
                executed_at TEXT NOT NULL
            )
        """)

        # Insert sample actions only if the table is empty.
        count = connection.execute(
            "SELECT COUNT(*) FROM actions"
        ).fetchone()[0]

        if count == 0:
            sample_actions = [
                (
                    1,
                    "Copy project plan",
                    "Agent wants to copy a project document.",
                    "copy_file",
                    "project/plan.txt → review/plan.txt",
                    "pending",
                ),
                (
                    2,
                    "Move meeting notes",
                    "Agent wants to move a meeting document.",
                    "move_file",
                    "project/meeting_notes.txt → archive/",
                    "pending",
                ),
                (
                    3,
                    "Rename draft document",
                    "Agent wants to rename a draft file.",
                    "rename_file",
                    "draft.docx → final_draft.docx",
                    "pending",
                ),
            ]

            connection.executemany(
                """
                INSERT INTO actions
                (id, title, description, tool, target, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                sample_actions,
            )


# Initialize the database when the backend starts.
initialize_database()


# Request format for approval or rejection.
class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]

class ProposalRequest(BaseModel):
    instruction: str


@app.get("/")
def home():
    return {
        "message": "AI Agent Oversight Workbench backend is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "AI Agent Oversight Workbench",
        "version": "0.1.0",
    }


# Get all actions from SQLite.
@app.get("/actions")
def get_actions():
    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM actions ORDER BY id"
        ).fetchall()

    return [dict(row) for row in rows]


# Generate an AI proposal and add it to the approval queue.
@app.post("/proposals")
def create_proposal(request: ProposalRequest):

    # Ask Gemini to interpret the user's instruction.
    try:
        proposal = generate_action_proposal(
            request.instruction
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print(f"Gemini proposal generation failed: {error}")

        raise HTTPException(
            status_code=502,
            detail="AI service is temporarily unavailable or could not generate a proposal.",
        )

    # Do not add unclear or unsupported requests to the queue.
    if proposal.needs_clarification or proposal.tool == "unsupported":
        return {
            "status": "needs_clarification",
            "proposal": proposal.model_dump(),
            "message": proposal.clarification_question,
        }

    # Combine source and destination into the format
    # already understood by our file executor.
    target = (
        f"{proposal.source_path} → "
        f"{proposal.destination_path}"
    )


    # Check whether an identical action is already waiting.
    with get_db_connection() as connection:

        existing_action = connection.execute(
            """
            SELECT * FROM actions
            WHERE tool = ?
              AND TRIM(target) = ?
              AND (
                  status = 'pending'
                  OR (
                      status = 'approved'
                      AND execution_status IN ('not_started', 'running')
                  )
              )
            ORDER BY id
            LIMIT 1
            """,
            (proposal.tool, target),
        ).fetchone()

        if existing_action is not None:
            return {
                "status": "duplicate",
                "message": (
                    "This action already exists in the approval queue. "
                    "No duplicate was created."
                ),
                "action": dict(existing_action),
            }


    # Save the AI proposal as pending human approval.
    with get_db_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO actions (
                title,
                description,
                tool,
                target,
                status,
                execution_status,
                execution_message
            )
            VALUES (?, ?, ?, ?, 'pending', 'not_started', '')
            """,
            (
                proposal.title,
                proposal.description,
                proposal.tool,
                target,
            ),
        )

        action_id = cursor.lastrowid

        created_action = connection.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()

    return {
        "status": "pending_approval",
        "message": "AI proposal added to the approval queue. It has not been executed.",
        "action": dict(created_action),
    }



# Approve or reject an action and record the decision.
@app.post("/actions/{action_id}/decision")
def decide_action(action_id: int, request: DecisionRequest):

    with get_db_connection() as connection:

        action = connection.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()

        if action is None:
            raise HTTPException(
                status_code=404,
                detail="Action not found",
            )

        if action["status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail="This action has already been reviewed",
            )

        connection.execute(
            "UPDATE actions SET status = ? WHERE id = ?",
            (request.decision, action_id),
        )

        connection.execute(
            """
            INSERT INTO audit_log (action_id, decision, decided_at)
            VALUES (?, ?, ?)
            """,
            (
                action_id,
                request.decision,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )

        updated_action = connection.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()

    return {
        "message": f"Action {request.decision} successfully",
        "action": dict(updated_action),
    }


# Get approval and rejection history.
@app.get("/audit-log")
def get_audit_log():
    with get_db_connection() as connection:
        rows = connection.execute("""
            SELECT
                audit_log.id,
                audit_log.action_id,
                actions.title,
                audit_log.decision,
                audit_log.decided_at
            FROM audit_log
            JOIN actions ON actions.id = audit_log.action_id
            ORDER BY audit_log.id DESC
        """).fetchall()

    return [dict(row) for row in rows]


# Execute an action only after human approval.
@app.post("/actions/{action_id}/execute")
def execute_approved_action(action_id: int):

    # First check the approval status and reserve the action.
    with get_db_connection() as connection:

        action = connection.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()

        if action is None:
            raise HTTPException(
                status_code=404,
                detail="Action not found",
            )

        if action["status"] != "approved":
            raise HTTPException(
                status_code=403,
                detail="Human approval is required before execution.",
            )

        if action["execution_status"] != "not_started":
            raise HTTPException(
                status_code=409,
                detail="This action has already been attempted or executed.",
            )

        cursor = connection.execute(
            """
            UPDATE actions
            SET execution_status = 'running'
            WHERE id = ?
              AND status = 'approved'
              AND execution_status = 'not_started'
            """,
            (action_id,),
        )

        if cursor.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail="This action is no longer available for execution.",
            )

        action_data = dict(action)

    # Now perform the approved file operation.
    try:
        result = execute_file_action(
            action_data["tool"],
            action_data["target"],
        )

    except Exception as error:

        error_message = str(error)

        with get_db_connection() as connection:

            connection.execute(
                """
                UPDATE actions
                SET execution_status = 'failed',
                    execution_message = ?
                WHERE id = ?
                """,
                (error_message, action_id),
            )

            connection.execute(
                """
                INSERT INTO execution_log
                (action_id, tool, target, status, message, executed_at)
                VALUES (?, ?, ?, 'failed', ?, ?)
                """,
                (
                    action_id,
                    action_data["tool"],
                    action_data["target"],
                    error_message,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )

        raise HTTPException(
            status_code=400,
            detail=f"File execution failed: {error_message}",
        )

    # Save the successful execution.
    with get_db_connection() as connection:

        connection.execute(
            """
            UPDATE actions
            SET execution_status = 'completed',
                execution_message = ?
            WHERE id = ?
            """,
            (result["message"], action_id),
        )

        connection.execute(
            """
            INSERT INTO execution_log
            (action_id, tool, target, status, message, executed_at)
            VALUES (?, ?, ?, 'completed', ?, ?)
            """,
            (
                action_id,
                action_data["tool"],
                action_data["target"],
                result["message"],
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )

        updated_action = connection.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()

    return {
        "message": "Approved action executed successfully.",
        "action": dict(updated_action),
        "execution": result,
    }


# Get file execution history.
@app.get("/execution-log")
def get_execution_log():
    with get_db_connection() as connection:
        rows = connection.execute("""
            SELECT
                execution_log.id,
                execution_log.action_id,
                actions.title,
                execution_log.tool,
                execution_log.target,
                execution_log.status,
                execution_log.message,
                execution_log.executed_at
            FROM execution_log
            JOIN actions ON actions.id = execution_log.action_id
            ORDER BY execution_log.id DESC
        """).fetchall()

    return [dict(row) for row in rows]
