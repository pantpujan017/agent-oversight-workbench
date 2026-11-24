
import pytest

import executor
import workspace_paths

from executor import execute_file_action


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Create an isolated workspace for executor testing."""

    monkeypatch.setattr(workspace_paths, "WORKSPACE_ROOT", tmp_path)

    monkeypatch.setattr(executor, "WORKSPACE_ROOT", tmp_path)

    project = tmp_path / "project"
    review = tmp_path / "review"

    project.mkdir()
    review.mkdir()

    (project / "plan.txt").write_text("Test content")

    return tmp_path


def test_copy_file(workspace):
    result = execute_file_action(
        "copy_file",
        "project/plan.txt → review/copy.txt",
    )

    assert result["status"] == "completed"
    assert (workspace / "review" / "copy.txt").read_text() == "Test content"
    assert (workspace / "project" / "plan.txt").exists()


def test_move_file(workspace):
    result = execute_file_action(
        "move_file",
        "project/plan.txt → review/moved.txt",
    )

    assert result["status"] == "completed"
    assert (workspace / "review" / "moved.txt").exists()
    assert not (workspace / "project" / "plan.txt").exists()


def test_rename_file(workspace):
    result = execute_file_action(
        "rename_file",
        "project/plan.txt → project/new_name.txt",
    )

    assert result["status"] == "completed"
    assert (workspace / "project" / "new_name.txt").exists()
    assert not (workspace / "project" / "plan.txt").exists()


def test_copy_into_existing_folder(workspace):
    result = execute_file_action(
        "copy_file",
        "project/plan.txt → review/",
    )

    assert result["status"] == "completed"
    assert (workspace / "review" / "plan.txt").exists()


def test_external_path_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "project/plan.txt → ../outside.txt",
        )


def test_absolute_path_is_rejected(workspace, tmp_path):
    outside_path = tmp_path.parent / "outside.txt"

    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            f"project/plan.txt → {outside_path}",
        )


def test_missing_source_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "missing.txt → review/copy.txt",
        )


def test_source_directory_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "project → review/copied",
        )


def test_existing_destination_is_rejected(workspace):
    (workspace / "review" / "existing.txt").write_text("Existing content")

    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "project/plan.txt → review/existing.txt",
        )


def test_missing_destination_folder_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "project/plan.txt → missing/copy.txt",
        )


def test_same_source_and_destination_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "project/plan.txt → project/plan.txt",
        )


def test_unsupported_operation_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "delete_file",
            "project/plan.txt → review/plan.txt",
        )


def test_malformed_target_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "project/plan.txt",
        )


def test_empty_destination_is_rejected(workspace):
    with pytest.raises(ValueError):
        execute_file_action(
            "copy_file",
            "project/plan.txt → ",
        )

def test_source_symlink_cannot_escape_workspace(workspace, tmp_path):
    outside_file = tmp_path.parent / f"{tmp_path.name}_outside.txt"
    outside_file.write_text("Sensitive external content")

    symlink = workspace / "project" / "external_link.txt"

    try:
        symlink.symlink_to(outside_file)

        with pytest.raises(ValueError):
            execute_file_action(
                "copy_file",
                "project/external_link.txt → review/copied.txt",
            )

    except (OSError, NotImplementedError) as error:
        pytest.skip(f"Symlink creation unavailable: {error}")

    finally:
        if outside_file.exists():
            outside_file.unlink()


def test_destination_symlink_cannot_escape_workspace(workspace, tmp_path):
    outside_folder = tmp_path.parent / f"{tmp_path.name}_outside_folder"
    outside_folder.mkdir()

    symlink = workspace / "review" / "external_link"

    try:
        symlink.symlink_to(outside_folder, target_is_directory=True)

        with pytest.raises(ValueError):
            execute_file_action(
                "copy_file",
                "project/plan.txt → review/external_link/copied.txt",
            )

    except (OSError, NotImplementedError) as error:
        pytest.skip(f"Symlink creation unavailable: {error}")

    finally:
        if outside_folder.exists():
            outside_folder.rmdir()
