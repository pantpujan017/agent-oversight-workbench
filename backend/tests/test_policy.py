
import pytest

import executor
import policy
import workspace_paths

from policy import evaluate_action


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Create an isolated workspace for each test."""

    monkeypatch.setattr(workspace_paths, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(executor, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(policy, "WORKSPACE_ROOT", tmp_path)

    project = tmp_path / "project"
    review = tmp_path / "review"

    project.mkdir()
    review.mkdir()

    (project / "plan.txt").write_text("Test content")

    return tmp_path


def test_valid_copy_is_allowed(workspace):
    result = evaluate_action(
        "copy_file",
        "project/plan.txt",
        "review/copy.txt",
    )

    assert result.allowed is True
    assert result.destination == "review/copy.txt"

    # Policy evaluation must not execute the operation.
    assert not (workspace / "review" / "copy.txt").exists()


def test_valid_move_is_allowed(workspace):
    result = evaluate_action(
        "move_file",
        "project/plan.txt",
        "review/moved.txt",
    )

    assert result.allowed is True


def test_valid_rename_is_allowed(workspace):
    result = evaluate_action(
        "rename_file",
        "project/plan.txt",
        "review/renamed.txt",
    )

    assert result.allowed is True


def test_external_destination_is_blocked(workspace):
    result = evaluate_action(
        "copy_file",
        "project/plan.txt",
        "../outside.txt",
    )

    assert result.allowed is False


def test_existing_destination_is_blocked(workspace):
    (workspace / "review" / "plan.txt").write_text("Existing file")

    result = evaluate_action(
        "copy_file",
        "project/plan.txt",
        "review/plan.txt",
    )

    assert result.allowed is False


def test_missing_source_is_blocked(workspace):
    result = evaluate_action(
        "copy_file",
        "missing.txt",
        "review/missing.txt",
    )

    assert result.allowed is False


def test_unsupported_operation_is_blocked(workspace):
    result = evaluate_action(
        "delete_file",
        "project/plan.txt",
        "review/plan.txt",
    )

    assert result.allowed is False


def test_empty_paths_are_blocked(workspace):
    result = evaluate_action(
        "copy_file",
        "",
        "review/copy.txt",
    )

    assert result.allowed is False


def test_source_directory_is_blocked(workspace):
    result = evaluate_action(
        "copy_file",
        "project",
        "review/copy",
    )

    assert result.allowed is False


def test_same_source_and_destination_are_blocked(workspace):
    result = evaluate_action(
        "copy_file",
        "project/plan.txt",
        "project/plan.txt",
    )

    assert result.allowed is False


def test_copy_into_existing_folder_is_allowed(workspace):
    result = evaluate_action(
        "copy_file",
        "project/plan.txt",
        "review/",
    )

    assert result.allowed is True
    assert result.destination == "review/plan.txt"


def test_missing_destination_folder_is_blocked(workspace):
    result = evaluate_action(
        "copy_file",
        "project/plan.txt",
        "missing_folder/copy.txt",
    )

    assert result.allowed is False


def test_rename_into_folder_is_blocked(workspace):
    result = evaluate_action(
        "rename_file",
        "project/plan.txt",
        "review/",
    )

    assert result.allowed is False
