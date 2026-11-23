
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


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


# Create database tables and insert sample actions if needed.
def initialize_database():
    with get_db_connection() as connection:

        # Actions table
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

        # Audit log table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                decision TEXT NOT NULL
                    CHECK(decision IN ('approved', 'rejected')),
                decided_at TEXT NOT NULL
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


# Approve or reject an action and record the decision.
@app.post("/actions/{action_id}/decision")
def decide_action(action_id: int, request: DecisionRequest):

    with get_db_connection() as connection:

        # Find the requested action.
        action = connection.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()

        if action is None:
            raise HTTPException(
                status_code=404,
                detail="Action not found",
            )

        # Prevent changing an already reviewed action.
        if action["status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail="This action has already been reviewed",
            )

        # Update the action status.
        connection.execute(
            "UPDATE actions SET status = ? WHERE id = ?",
            (request.decision, action_id),
        )

        # Record the decision in the audit log.
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

        # Get the updated action.
        updated_action = connection.execute(
            "SELECT * FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()

    return {
        "message": f"Action {request.decision} successfully",
        "action": dict(updated_action),
    }


# Get the decision history.
@app.get("/audit-log")
def get_audit_log():

    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                audit_log.id,
                audit_log.action_id,
                actions.title,
                audit_log.decision,
                audit_log.decided_at
            FROM audit_log
            JOIN actions ON actions.id = audit_log.action_id
            ORDER BY audit_log.id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]
