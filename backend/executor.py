
import shutil
from pathlib import Path


# The agent is only allowed to work inside this folder.
WORKSPACE_ROOT = (
    Path(__file__).resolve().parent / "agent_workspace"
).resolve()


def resolve_workspace_path(
    relative_path: str,
    must_exist: bool = False,
) -> Path:
    """
    Convert a relative workspace path into a safe absolute path.
    Reject paths that try to access files outside the workspace.
    """

    relative_path = relative_path.strip()

    if not relative_path:
        raise ValueError("File path cannot be empty.")

    path = Path(relative_path)

    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Access outside the agent workspace is not allowed.")

    resolved_path = (
        WORKSPACE_ROOT / path
    ).resolve(strict=must_exist)

    if not resolved_path.is_relative_to(WORKSPACE_ROOT):
        raise ValueError("Access outside the agent workspace is not allowed.")

    return resolved_path


def execute_file_action(tool: str, target: str) -> dict:
    """
    Execute an approved file operation inside agent_workspace.
    Supported operations: copy_file, move_file, rename_file.
    """

    if tool not in {"copy_file", "move_file", "rename_file"}:
        raise ValueError(f"Unsupported tool: {tool}")

    if "→" not in target:
        raise ValueError("Invalid target format.")

    source_text, destination_text = target.split("→", 1)

    source_text = source_text.strip()
    destination_text = destination_text.strip()

    # Check that the source exists inside the workspace.
    source_path = resolve_workspace_path(
        source_text,
        must_exist=True,
    )

    if not source_path.is_file():
        raise ValueError("The source must be an existing file.")

    # Detect whether the destination represents a folder.
    destination_is_folder = destination_text.endswith(("/", "\\"))

    destination_path = resolve_workspace_path(
        destination_text,
        must_exist=False,
    )

    # For folder destinations, use the original filename.
    if destination_is_folder:
        if not destination_path.is_dir():
            raise ValueError("The destination folder does not exist.")

        destination_path = destination_path / source_path.name

    elif tool == "move_file" and destination_path.is_dir():
        destination_path = destination_path / source_path.name

    # Check the final destination remains inside the workspace.
    destination_path = destination_path.resolve()

    if not destination_path.is_relative_to(WORKSPACE_ROOT):
        raise ValueError("Destination outside the workspace is not allowed.")

    if destination_path.exists():
        raise ValueError("A file already exists at the destination.")

    if not destination_path.parent.is_dir():
        raise ValueError("The destination folder does not exist.")

    # Perform the requested operation.
    try:
        if tool == "copy_file":
            shutil.copy2(source_path, destination_path)

        elif tool == "move_file":
            shutil.move(str(source_path), str(destination_path))

        elif tool == "rename_file":
            source_path.rename(destination_path)

    except OSError as error:
        raise ValueError(f"File operation failed: {error}") from error

    return {
        "status": "completed",
        "tool": tool,
        "source": source_text,
        "destination": str(
            destination_path.relative_to(WORKSPACE_ROOT)
        ).replace("\\", "/"),
        "message": "File operation completed successfully.",
    }
