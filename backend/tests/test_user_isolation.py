
import pytest
from fastapi import HTTPException

import main
import workspace_paths

from ai_service import ActionProposal


USER_A = {
    "id": "11111111-1111-4111-8111-111111111111"
}

USER_B = {
    "id": "22222222-2222-4222-8222-222222222222"
}


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    """Give each test its own temporary SQLite database."""

    monkeypatch.setattr(
        main,
        "DB_PATH",
        tmp_path / "test_user_isolation.db",
    )

    main.initialize_database()

    return tmp_path


def insert_action(
    user_id,
    status="pending",
    execution_status="not_started",
):
    """Insert an action owned by a specific user."""

    with main.get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO actions (
                user_id,
                title,
                description,
                tool,
                target,
                status,
                execution_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "Test action",
                "Testing user ownership.",
                "copy_file",
                "project/plan.txt → review/result.txt",
                status,
                execution_status,
            ),
        )

        return cursor.lastrowid


def test_users_receive_separate_workspaces(
    tmp_path,
    monkeypatch,
):
    """User A and User B must receive different directories."""

    workspaces_root = tmp_path / "user_workspaces"

    monkeypatch.setattr(
        workspace_paths,
        "USER_WORKSPACES_ROOT",
        workspaces_root,
    )

    root_a = workspace_paths.get_user_workspace_root(
        USER_A["id"]
    )

    root_b = workspace_paths.get_user_workspace_root(
        USER_B["id"]
    )

    assert root_a != root_b

    assert root_a.is_relative_to(workspaces_root)
    assert root_b.is_relative_to(workspaces_root)

    # Create a private file for User A.
    private_file = root_a / "private.txt"
    private_file.write_text("User A private information")

    # User B must not have that file.
    assert not (root_b / "private.txt").exists()

    with pytest.raises(FileNotFoundError):
        workspace_paths.resolve_workspace_path(
            "private.txt",
            must_exist=True,
            workspace_root=root_b,
        )


@pytest.mark.parametrize(
    "invalid_user_id",
    [
        "",
        "../another-user",
        None,
        123,
    ],
)
def test_invalid_user_ids_are_rejected(
    tmp_path,
    monkeypatch,
    invalid_user_id,
):
    """Invalid IDs must not create or select user workspaces."""

    monkeypatch.setattr(
        workspace_paths,
        "USER_WORKSPACES_ROOT",
        tmp_path / "user_workspaces",
    )

    with pytest.raises(ValueError):
        workspace_paths.get_user_workspace_root(
            invalid_user_id
        )


def test_symbolic_link_workspace_is_rejected(
    tmp_path,
    monkeypatch,
):
    """A user's workspace must not be a link to another directory."""

    workspaces_root = tmp_path / "user_workspaces"
    workspaces_root.mkdir()

    outside_directory = tmp_path / "outside"
    outside_directory.mkdir()

    user_workspace = workspaces_root / USER_A["id"]

    try:
        user_workspace.symlink_to(
            outside_directory,
            target_is_directory=True,
        )
    except (OSError, NotImplementedError):
        pytest.skip(
            "Directory symbolic links are unavailable on this system."
        )

    monkeypatch.setattr(
        workspace_paths,
        "USER_WORKSPACES_ROOT",
        workspaces_root,
    )

    with pytest.raises(ValueError):
        workspace_paths.get_user_workspace_root(
            USER_A["id"]
        )


def test_user_cannot_view_another_users_actions(
    isolated_database,
):
    """User B must not see actions created by User A."""

    action_id = insert_action(USER_A["id"])

    actions_a = main.get_actions(
        current_user=USER_A
    )

    actions_b = main.get_actions(
        current_user=USER_B
    )

    assert any(
        action["id"] == action_id
        for action in actions_a
    )

    assert not any(
        action["id"] == action_id
        for action in actions_b
    )


def test_user_cannot_decide_another_users_action(
    isolated_database,
):
    """User B must not approve or reject User A's action."""

    action_id = insert_action(
        USER_A["id"],
        status="pending",
    )

    request = main.DecisionRequest(
        decision="approved"
    )

    with pytest.raises(HTTPException) as error:
        main.decide_action(
            action_id,
            request,
            current_user=USER_B,
        )

    assert error.value.status_code == 404

    # The action must remain pending.
    with main.get_db_connection() as connection:
        action = connection.execute(
            """
            SELECT status
            FROM actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()

        audit_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit_log
            WHERE action_id = ?
            """,
            (action_id,),
        ).fetchone()[0]

    assert action["status"] == "pending"
    assert audit_count == 0


def test_user_cannot_execute_another_users_action(
    isolated_database,
    tmp_path,
    monkeypatch,
):
    """User B must not execute User A's approved action."""

    action_id = insert_action(
        USER_A["id"],
        status="approved",
    )

    user_b_workspace = (
        tmp_path / "user_workspaces" / USER_B["id"]
    )
    user_b_workspace.mkdir(parents=True)

    monkeypatch.setattr(
        main,
        "get_user_workspace_root",
        lambda user_id: user_b_workspace,
    )

    def executor_must_not_run(*args, **kwargs):
        pytest.fail(
            "Executor was called for another user's action!"
        )

    monkeypatch.setattr(
        main,
        "execute_file_action",
        executor_must_not_run,
    )

    with pytest.raises(HTTPException) as error:
        main.execute_approved_action(
            action_id,
            current_user=USER_B,
        )

    assert error.value.status_code == 404

    # Confirm that execution never started.
    with main.get_db_connection() as connection:
        action = connection.execute(
            """
            SELECT status, execution_status
            FROM actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()

        execution_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM execution_log
            WHERE action_id = ?
            """,
            (action_id,),
        ).fetchone()[0]

    assert action["status"] == "approved"
    assert action["execution_status"] == "not_started"
    assert execution_count == 0


def test_user_cannot_view_another_users_audit_history(
    isolated_database,
):
    """User B must not see User A's approval history."""

    action_id = insert_action(USER_A["id"])

    with main.get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_log (
                action_id,
                decision,
                decided_at
            )
            VALUES (?, 'approved', ?)
            """,
            (action_id, "2026-11-28T10:00:00+00:00"),
        )

    audit_a = main.get_audit_log(
        current_user=USER_A
    )

    audit_b = main.get_audit_log(
        current_user=USER_B
    )

    assert any(
        entry["action_id"] == action_id
        for entry in audit_a
    )

    assert not any(
        entry["action_id"] == action_id
        for entry in audit_b
    )


def test_user_cannot_view_another_users_execution_history(
    isolated_database,
):
    """User B must not see User A's execution history."""

    action_id = insert_action(
        USER_A["id"],
        status="approved",
        execution_status="completed",
    )

    with main.get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO execution_log (
                action_id,
                tool,
                target,
                status,
                message,
                executed_at
            )
            VALUES (?, ?, ?, 'completed', ?, ?)
            """,
            (
                action_id,
                "copy_file",
                "project/plan.txt → review/result.txt",
                "Execution successful.",
                "2026-11-28T10:00:00+00:00",
            ),
        )

    logs_a = main.get_execution_log(
        current_user=USER_A
    )

    logs_b = main.get_execution_log(
        current_user=USER_B
    )

    assert any(
        entry["action_id"] == action_id
        for entry in logs_a
    )

    assert not any(
        entry["action_id"] == action_id
        for entry in logs_b
    )


def test_identical_proposals_are_separate_for_different_users(
    isolated_database,
    tmp_path,
    monkeypatch,
):
    """
    A proposal from User A must not count as a duplicate
    for User B.
    """

    workspace_a = tmp_path / "workspace_a"
    workspace_b = tmp_path / "workspace_b"

    workspaces = {
        USER_A["id"]: workspace_a,
        USER_B["id"]: workspace_b,
    }

    for workspace in workspaces.values():
        project = workspace / "project"
        review = workspace / "review"

        project.mkdir(parents=True)
        review.mkdir(parents=True)

        (project / "plan.txt").write_text(
            "Test project plan"
        )

    monkeypatch.setattr(
        main,
        "get_user_workspace_root",
        lambda user_id: workspaces[user_id],
    )

    proposal = ActionProposal(
        title="Copy project plan",
        description="Copy a project document.",
        tool="copy_file",
        source_path="project/plan.txt",
        destination_path="review/shared_test.txt",
        needs_clarification=False,
        clarification_question="",
    )

    monkeypatch.setattr(
        main,
        "generate_action_proposal",
        lambda instruction, workspace_root=None: proposal,
    )

    request = main.ProposalRequest(
        instruction="Copy the project plan."
    )

    result_a = main.create_proposal(
        request,
        current_user=USER_A,
    )

    result_b = main.create_proposal(
        request,
        current_user=USER_B,
    )

    assert result_a["status"] == "pending_approval"
    assert result_b["status"] == "pending_approval"

    assert (
        result_a["action"]["id"]
        != result_b["action"]["id"]
    )

    assert result_a["action"]["user_id"] == USER_A["id"]
    assert result_b["action"]["user_id"] == USER_B["id"]
