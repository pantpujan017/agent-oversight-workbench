
from dataclasses import dataclass
from workspace_paths import WORKSPACE_ROOT, resolve_workspace_path


# Tools that the policy engine permits.
ALLOWED_TOOLS = {
    "copy_file",
    "move_file",
    "rename_file",
}


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reason: str
    destination: str = ""


def evaluate_action(
    tool: str,
    source_text: str,
    destination_text: str,
) -> PolicyResult:
    """
    Independently evaluate a proposed file operation.

    This function only checks the operation.
    It does not execute or modify any files.
    """

    # Rule 1: Only approved tool types are permitted.
    if tool not in ALLOWED_TOOLS:
        return PolicyResult(
            allowed=False,
            reason="This file operation is not permitted.",
        )

    try:
        source_text = source_text.strip()
        destination_text = destination_text.strip()

        # Rule 2: Both paths must be provided.
        if not source_text or not destination_text:
            return PolicyResult(
                allowed=False,
                reason="Source and destination paths are required.",
            )

        # Rule 3: Source must exist inside the workspace.
        source_path = resolve_workspace_path(
            source_text,
            must_exist=True,
        )

        if not source_path.is_file():
            return PolicyResult(
                allowed=False,
                reason="The source must be an existing file.",
            )

        # Rule 4: Destination must remain inside the workspace.
        destination_is_folder = destination_text.endswith(
            ("/", "\\")
        )

        destination_path = resolve_workspace_path(
            destination_text,
            must_exist=False,
        )

        # Rule 5: Rename must specify a filename.
        if tool == "rename_file" and (
            destination_is_folder or destination_path.is_dir()
        ):
            return PolicyResult(
                allowed=False,
                reason="Rename must specify a destination filename.",
            )

        # Copy and move may target an existing folder.
        if tool in {"copy_file", "move_file"}:

            if destination_is_folder or destination_path.is_dir():

                if not destination_path.is_dir():
                    return PolicyResult(
                        allowed=False,
                        reason="The destination folder does not exist.",
                    )

                destination_path = (
                    destination_path / source_path.name
                )

        # Resolve the final destination.
        destination_path = destination_path.resolve()

        # Rule 6: Confirm the resolved destination is safe.
        if not destination_path.is_relative_to(WORKSPACE_ROOT):
            return PolicyResult(
                allowed=False,
                reason="Access outside the workspace is not allowed.",
            )

        # Rule 7: Prevent operations on the same file.
        if source_path == destination_path:
            return PolicyResult(
                allowed=False,
                reason="Source and destination cannot be identical.",
            )

        # Rule 8: Never overwrite an existing file.
        if destination_path.exists():
            return PolicyResult(
                allowed=False,
                reason="A file already exists at the destination.",
            )

        # Rule 9: Destination folder must already exist.
        if not destination_path.parent.is_dir():
            return PolicyResult(
                allowed=False,
                reason="The destination folder does not exist.",
            )

        # All policy checks passed.
        normalized_destination = (
            destination_path.relative_to(
                WORKSPACE_ROOT
            ).as_posix()
        )

        return PolicyResult(
            allowed=True,
            reason="All policy checks passed.",
            destination=normalized_destination,
        )

    except (ValueError, OSError) as error:
        return PolicyResult(
            allowed=False,
            reason=str(error),
        )
