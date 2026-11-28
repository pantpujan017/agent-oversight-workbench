
from pathlib import Path, PureWindowsPath
from uuid import UUID


# Existing workspace retained for backward compatibility.
WORKSPACE_ROOT = (
    Path(__file__).resolve().parent / "agent_workspace"
).resolve()


# Root directory containing individual user workspaces.
USER_WORKSPACES_ROOT = (
    Path(__file__).resolve().parent / "user_workspaces"
).resolve()


def get_user_workspace_root(user_id: str) -> Path:
    """
    Create or retrieve an isolated workspace for one authenticated user.

    Supabase user IDs are UUIDs. Validating the ID prevents path
    traversal and prevents users from choosing another workspace.
    """

    if not isinstance(user_id, str):
        raise ValueError("Invalid user ID.")

    try:
        normalized_user_id = str(UUID(user_id))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("Invalid user ID.") from error

    USER_WORKSPACES_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    user_workspace = (
        USER_WORKSPACES_ROOT / normalized_user_id
    )

    # Do not follow a workspace directory that is a symbolic link.
    if user_workspace.is_symlink():
        raise ValueError(
            "User workspace cannot be a symbolic link."
        )

    user_workspace.mkdir(exist_ok=True)

    resolved_workspace = user_workspace.resolve()

    # Ensure the final directory is exactly the user's expected directory.
    if resolved_workspace != user_workspace.resolve():
        raise ValueError("Invalid user workspace.")

    if not resolved_workspace.is_relative_to(
        USER_WORKSPACES_ROOT
    ):
        raise ValueError(
            "User workspace outside the workspace directory is not allowed."
        )

    return resolved_workspace


def resolve_workspace_path(
    relative_path: str,
    must_exist: bool = False,
    workspace_root: Path | None = None,
) -> Path:
    """
    Resolve a relative path inside the selected workspace.

    When workspace_root is omitted, use the existing legacy workspace.
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

    root = Path(
        workspace_root if workspace_root is not None
        else WORKSPACE_ROOT
    ).resolve()

    if not root.is_dir():
        raise FileNotFoundError(
            "The selected workspace does not exist."
        )

    # Resolve symlinks and normalize the path.
    resolved_path = (
        root / path
    ).resolve(strict=must_exist)

    # Confirm the final resolved location stays inside the workspace.
    if not resolved_path.is_relative_to(root):
        raise ValueError(
            "Access outside the agent workspace is not allowed."
        )

    return resolved_path
