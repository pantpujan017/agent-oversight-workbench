
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
