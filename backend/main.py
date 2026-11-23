
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


# Temporary in-memory action storage
ACTIONS = [
    {
        "id": 1,
        "title": "Copy project plan",
        "description": "Agent wants to copy a project document.",
        "tool": "copy_file",
        "target": "project/plan.txt → review/plan.txt",
        "status": "pending",
    },
    {
        "id": 2,
        "title": "Move meeting notes",
        "description": "Agent wants to move a meeting document.",
        "tool": "move_file",
        "target": "project/meeting_notes.txt → archive/",
        "status": "pending",
    },
    {
        "id": 3,
        "title": "Rename draft document",
        "description": "Agent wants to rename a draft file.",
        "tool": "rename_file",
        "target": "draft.docx → final_draft.docx",
        "status": "pending",
    },
]


# Request format for approval or rejection
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


@app.get("/actions")
def get_actions():
    return ACTIONS


@app.post("/actions/{action_id}/decision")
def decide_action(action_id: int, request: DecisionRequest):

    # Find the requested action
    action = next(
        (item for item in ACTIONS if item["id"] == action_id),
        None,
    )

    if action is None:
        raise HTTPException(
            status_code=404,
            detail="Action not found",
        )

    # Prevent changing an already reviewed action
    if action["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail="This action has already been reviewed",
        )

    # Update the decision
    action["status"] = request.decision

    return {
        "message": f"Action {request.decision} successfully",
        "action": action,
    }
