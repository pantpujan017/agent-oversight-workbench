
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI application
app = FastAPI(
    title="AI Agent Oversight Workbench",
    description="Backend API for supervising AI agent actions",
    version="0.1.0",
)

# Allow our React frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# Root endpoint
@app.get("/")
def home():
    return {
        "message": "AI Agent Oversight Workbench backend is running"
    }


# Health-check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "AI Agent Oversight Workbench",
        "version": "0.1.0",
    }



# Return the available agent actions
@app.get("/actions")
def get_actions():
    return [
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
