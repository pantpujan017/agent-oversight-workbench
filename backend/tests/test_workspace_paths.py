
import pytest

import workspace_paths
from workspace_paths import resolve_workspace_path


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(
        workspace_paths,
        "WORKSPACE_ROOT",
        tmp_path,
    )

    folder = tmp_path / "project"
    folder.mkdir()

    (folder / "plan.txt").write_text("Test content")

    return tmp_path


def test_resolves_existing_file(workspace):
    result = resolve_workspace_path(
        "project/plan.txt",
        must_exist=True,
    )

    assert result == workspace / "project" / "plan.txt"


def test_resolves_new_destination(workspace):
    result = resolve_workspace_path(
        "project/new.txt",
    )

    assert result == workspace / "project" / "new.txt"


def test_rejects_parent_traversal(workspace):
    with pytest.raises(ValueError):
        resolve_workspace_path("../outside.txt")


def test_rejects_absolute_path(workspace, tmp_path):
    outside = tmp_path.parent / "outside.txt"

    with pytest.raises(ValueError):
        resolve_workspace_path(str(outside))


def test_rejects_windows_drive_path(workspace):
    with pytest.raises(ValueError):
        resolve_workspace_path("C:\\outside.txt")


def test_rejects_empty_path(workspace):
    with pytest.raises(ValueError):
        resolve_workspace_path("")


def test_rejects_non_text_path(workspace):
    with pytest.raises(ValueError):
        resolve_workspace_path(None)


def test_rejects_null_byte(workspace):
    with pytest.raises(ValueError):
        resolve_workspace_path("project/bad\x00file.txt")


def test_missing_file_raises_error(workspace):
    with pytest.raises(FileNotFoundError):
        resolve_workspace_path(
            "project/missing.txt",
            must_exist=True,
        )
