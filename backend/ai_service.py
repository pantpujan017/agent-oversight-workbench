
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


# Load private environment variables.
ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)

WORKSPACE_ROOT = (
    Path(__file__).resolve().parent / "agent_workspace"
).resolve()


class ActionProposal(BaseModel):
    title: str = Field(
        description="A short title for the proposed action."
    )

    description: str = Field(
        description="A short explanation of the proposed action."
    )

    tool: Literal[
        "copy_file",
        "move_file",
        "rename_file",
        "unsupported",
    ]

    source_path: str = Field(
        description="Exact source file path relative to agent_workspace."
    )

    destination_path: str = Field(
        description="Destination folder or file path relative to agent_workspace."
    )

    needs_clarification: bool

    clarification_question: str



SYSTEM_INSTRUCTION = """
You are an action-planning assistant for an AI Agent Oversight Workbench.

Your job is ONLY to create one structured file-operation proposal.

Supported tools:
- copy_file
- move_file
- rename_file

Security rules:
- NEVER execute file operations.
- NEVER claim that a file has been modified.
- All paths must be relative to the assigned user workspace.
- Never use absolute paths or paths containing '..'.
- Never invent source filenames or folder names.
- Use only exact source filenames and existing directories supplied in the workspace inventory.
- A new destination filename is allowed ONLY when the user explicitly provides that exact filename.
- When the user provides a destination filename, use it exactly.
- Do not ask the user to choose an existing filename when they have already provided a new one.
- Do not propose deleting files or running programs.
- Do not overwrite existing destination files.

Path rules:
- source_path must be the exact existing source filename from the inventory.
- When the user asks to copy or move a file into a folder without specifying a new filename, destination_path must be that existing folder name ending in '/'.
- When the user explicitly specifies a new destination filename, destination_path must contain that exact filename.
- For renaming, destination_path must contain the user-provided new filename.
- The destination's parent folder must already exist in the workspace.
- The destination file must not already exist.
- Never guess a filename or folder name.

When a request is ambiguous:
- Set tool to unsupported.
- Set needs_clarification to true.
- Explain what is missing in clarification_question.
- Leave source_path and destination_path empty.

A human must approve every proposal before execution.
"""


def get_workspace_inventory(
    workspace_root: Path | None = None,
):
    """
    List files and folders available inside the selected workspace.

    If a user workspace is provided, inventory is restricted
    to that workspace. Otherwise, use the legacy workspace.
    """

    root = Path(
        workspace_root if workspace_root is not None
        else WORKSPACE_ROOT
    ).resolve()

    if not root.is_dir():
        raise RuntimeError("Agent workspace folder does not exist.")

    files = []
    directories = []

    for item in root.rglob("*"):

        resolved = item.resolve()

        # Ignore symbolic links that point outside the workspace.
        if not resolved.is_relative_to(root):
            continue

        relative_path = item.relative_to(
            root
        ).as_posix()

        if item.is_file():
            files.append(relative_path)

        elif item.is_dir():
            directories.append(relative_path + "/")

    return sorted(files), sorted(directories)



def invalid_proposal(
    proposal: ActionProposal,
    reason: str,
) -> ActionProposal:
    """
    Convert an invalid AI suggestion into a clarification request.
    """

    return ActionProposal(
        title=proposal.title,
        description=proposal.description,
        tool="unsupported",
        source_path="",
        destination_path="",
        needs_clarification=True,
        clarification_question=reason,
    )



def validate_proposal(
    proposal: ActionProposal,
    available_files: list[str],
    available_directories: list[str],
    workspace_root: Path | None = None,
) -> ActionProposal:
    """
    Validate a proposed file operation against the selected workspace.
    """

    root = Path(
        workspace_root if workspace_root is not None
        else WORKSPACE_ROOT
    ).resolve()

    if proposal.needs_clarification:
        return proposal

    if proposal.tool == "unsupported":
        return proposal

    # Source must match an actual file in this workspace.
    if proposal.source_path not in available_files:
        return invalid_proposal(
            proposal,
            "The suggested source file does not exist in the workspace. "
            "Please specify an available file.",
        )

    destination = proposal.destination_path.strip()

    if not destination:
        return invalid_proposal(
            proposal,
            "Please specify a destination.",
        )

    destination_object = Path(destination)

    if (
        destination_object.is_absolute()
        or ".." in destination_object.parts
    ):
        return invalid_proposal(
            proposal,
            "The destination path is not allowed.",
        )

    # Destination folder must already exist.
    if destination.endswith(("/", "\\")):
        normalized_folder = (
            destination.replace("\\", "/").rstrip("/") + "/"
        )

        if normalized_folder not in available_directories:
            return invalid_proposal(
                proposal,
                "The destination folder does not exist in the workspace.",
            )

        return proposal

    # Destination parent must exist.
    parent_folder = destination_object.parent.as_posix()

    if parent_folder == ".":
        parent_folder = ""

    normalized_parent = (
        parent_folder + "/" if parent_folder else ""
    )

    if normalized_parent and normalized_parent not in available_directories:
        return invalid_proposal(
            proposal,
            "The destination's parent folder does not exist.",
        )

    destination_path = (
        root / destination_object
    ).resolve()

    if not destination_path.is_relative_to(root):
        return invalid_proposal(
            proposal,
            "The destination is outside the workspace.",
        )

    if destination_path.exists():
        return invalid_proposal(
            proposal,
            "A file or folder already exists at the destination.",
        )

    return proposal

    """
    Check that Gemini selected a real source file
    and a valid destination inside the workspace.
    """

    if proposal.needs_clarification:
        return proposal

    if proposal.tool == "unsupported":
        return proposal

    # Source must match an actual workspace file.
    if proposal.source_path not in available_files:
        return invalid_proposal(
            proposal,
            "The suggested source file does not exist in the workspace. "
            "Please specify an available file.",
        )

    destination = proposal.destination_path.strip()

    if not destination:
        return invalid_proposal(
            proposal,
            "Please specify a destination.",
        )

    destination_object = Path(destination)

    if (
        destination_object.is_absolute()
        or ".." in destination_object.parts
    ):
        return invalid_proposal(
            proposal,
            "The destination path is not allowed.",
        )

    # If the destination ends in '/', it must be an existing folder.
    if destination.endswith(("/", "\\")):

        normalized_folder = (
            destination.replace("\\", "/").rstrip("/") + "/"
        )

        if normalized_folder not in available_directories:
            return invalid_proposal(
                proposal,
                "The destination folder does not exist in the workspace.",
            )

        return proposal

    # For a destination filename, its parent folder must exist.
    parent_folder = destination_object.parent.as_posix()

    if parent_folder == ".":
        parent_folder = ""

    normalized_parent = (
        parent_folder + "/" if parent_folder else ""
    )

    if normalized_parent and normalized_parent not in available_directories:
        return invalid_proposal(
            proposal,
            "The destination's parent folder does not exist.",
        )

    destination_path = (
        WORKSPACE_ROOT / destination_object
    ).resolve()

    if not destination_path.is_relative_to(WORKSPACE_ROOT):
        return invalid_proposal(
            proposal,
            "The destination is outside the workspace.",
        )

    if destination_path.exists():
        return invalid_proposal(
            proposal,
            "A file or folder already exists at the destination.",
        )

    return proposal



def generate_action_proposal(
    user_instruction: str,
    workspace_root: Path | None = None,
) -> ActionProposal:
    """
    Ask Gemini to interpret a user instruction and create
    a validated proposal inside the selected workspace.

    This function never executes file operations.
    """

    instruction = user_instruction.strip()

    if not instruction:
        raise ValueError("Please enter an instruction.")

    if len(instruction) > 2000:
        raise ValueError(
            "Instruction cannot exceed 2000 characters."
        )

    api_key = os.getenv("GEMINI_API_KEY")

    model_name = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash-lite",
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Check backend/.env."
        )

    # Select the authenticated user's workspace.
    root = Path(
        workspace_root if workspace_root is not None
        else WORKSPACE_ROOT
    ).resolve()

    if not root.is_dir():
        raise RuntimeError(
            "The selected agent workspace does not exist."
        )

    # Read only files belonging to this workspace.
    available_files, available_directories = (
        get_workspace_inventory(root)
    )

    workspace_information = f"""
AVAILABLE WORKSPACE FILES:
{available_files}

AVAILABLE WORKSPACE FOLDERS:
{available_directories}
"""

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model_name,
        contents=(
            workspace_information
            + "\nUser request:\n"
            + instruction
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_json_schema=ActionProposal.model_json_schema(),
            temperature=0.1,
            max_output_tokens=600,
        ),
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    proposal = ActionProposal.model_validate_json(
        response.text
    )

    # Validate against the same user's workspace.
    return validate_proposal(
        proposal,
        available_files,
        available_directories,
        workspace_root=root,
    )