
import shutil
from pathlib import Path, PureWindowsPath


# The agent can only access this dedicated workspace.
WORKSPACE_ROOT = (
    Path(__file__).resolve().parent / "agent_workspace"
).resolve()


def resolve_workspace_path(
    relative_path: str,
    must_exist: bool = False,
) -> Path:
    """
    Resolve a relative path and reject access outside
    the dedicated agent workspace.
    """

    if not isinstance(relative_path, str):
        raise ValueError("File path must be text.")

    relative_path = relative_path.strip()

    if not relative_path:
        raise ValueError("File path cannot be empty.")

    if "\x00" in relative_path:
        raise ValueError("Invalid file path.")

    # Check both Windows and normal path formats.
    windows_path = PureWindowsPath(relative_path)
    path = Path(relative_path)

    # Reject absolute paths, drive paths and parent traversal.
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in path.parts
        or ".." in windows_path.parts
    ):
        raise ValueError(
            "Access outside the agent workspace is not allowed."
        )

    # Resolve symlinks and normalize the path.
    resolved_path = (
        WORKSPACE_ROOT / path
    ).resolve(strict=must_exist)

    # Confirm the final resolved location stays inside the workspace.
    if not resolved_path.is_relative_to(WORKSPACE_ROOT):
        raise ValueError(
            "Access outside the agent workspace is not allowed."
        )

    return resolved_path


def execute_file_action(tool: str, target: str) -> dict:
    """
    Revalidate and execute an approved file operation.

    Supported operations:
    - copy_file
    - move_file
    - rename_file
    """

    # Check supported operations.
    if tool not in {
        "copy_file",
        "move_file",
        "rename_file",
    }:
        raise ValueError(
            f"Unsupported file operation: {tool}"
        )

    if not isinstance(target, str) or target.count("→") != 1:
        raise ValueError("Invalid file operation target.")

    source_text, destination_text = target.split("→", 1)

    source_text = source_text.strip()
    destination_text = destination_text.strip()

    if not source_text or not destination_text:
        raise ValueError(
            "Both source and destination paths are required."
        )

    # Validate the source again at execution time.
    source_path = resolve_workspace_path(
        source_text,
        must_exist=True,
    )

    if not source_path.is_file():
        raise ValueError(
            "The source must be an existing file."
        )

    # Validate the destination again.
    destination_path = resolve_workspace_path(
        destination_text,
        must_exist=False,
    )

    destination_is_folder = (
        destination_text.endswith(("/", "\\"))
    )

    # Copy and move may target an existing folder.
    if tool in {"copy_file", "move_file"}:

        if destination_is_folder or destination_path.is_dir():

            if not destination_path.is_dir():
                raise ValueError(
                    "The destination folder does not exist."
                )

            destination_path = (
                destination_path / source_path.name
            )

    # Rename must specify a filename, not a folder.
    elif tool == "rename_file":

        if destination_is_folder or destination_path.is_dir():
            raise ValueError(
                "Rename destination must be a file path."
            )

    # Resolve the final destination after adding the filename.
    destination_path = destination_path.resolve()

    if not destination_path.is_relative_to(WORKSPACE_ROOT):
        raise ValueError(
            "Destination outside the workspace is not allowed."
        )

    # Prevent a file from being copied or moved onto itself.
    if source_path == destination_path:
        raise ValueError(
            "Source and destination cannot be the same file."
        )

    # Never overwrite an existing file.
    if destination_path.exists():
        raise ValueError(
            "A file already exists at the destination."
        )

    # Require the destination folder to exist.
    if not destination_path.parent.is_dir():
        raise ValueError(
            "The destination folder does not exist."
        )

    # Perform the operation only after all checks pass.
    try:

        if tool == "copy_file":
            shutil.copy2(
                source_path,
                destination_path,
            )

        elif tool in {"move_file", "rename_file"}:
            source_path.rename(destination_path)

    except OSError as error:
        raise ValueError(
            f"File operation failed: {error}"
        ) from error

    return {
        "status": "completed",
        "tool": tool,
        "source": source_text,
        "destination": destination_path.relative_to(
            WORKSPACE_ROOT
        ).as_posix(),
        "message": "File operation completed successfully.",
    }
