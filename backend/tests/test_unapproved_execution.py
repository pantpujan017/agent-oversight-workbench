
import pytest
from fastapi import HTTPException

import main


def test_unapproved_action_cannot_execute(tmp_path, monkeypatch):
    # Use a separate temporary database.
    monkeypatch.setattr(
        main,
        "DB_PATH",
        tmp_path / "test_oversight.db",
    )

    main.initialize_database()

    test_user = {
        "id": "test-user-123"
    }

    monkeypatch.setattr(
        main,
        "get_user_workspace_root",
        lambda user_id: tmp_path,
    )

    # Insert an action that has NOT been approved.
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
            VALUES (?, ?, ?, ?, ?, 'pending', 'not_started')
            """,
            (
                test_user["id"],
                "Unapproved copy test",
                "Testing execution without approval.",
                "copy_file",
                "project/plan.txt → review/unapproved_copy.txt",
            ),
        )

        action_id = cursor.lastrowid

    # Detect whether the executor is incorrectly called.
    def executor_must_not_run(
        tool,
        target,
        workspace_root=None,
    ):
        raise AssertionError(
            "Executor was called without human approval!"
        )

    monkeypatch.setattr(
        main,
        "execute_file_action",
        executor_must_not_run,
    )

    # Attempt to execute the pending action.
    with pytest.raises(HTTPException) as error:
        main.execute_approved_action(
            action_id,
            current_user=test_user,
        )

    # The backend must reject the request.
    assert error.value.status_code == 403

    # Confirm the action remains pending and unexecuted.
    with main.get_db_connection() as connection:
        action = connection.execute(
            """
            SELECT status, execution_status
            FROM actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()

    assert action["status"] == "pending"
    assert action["execution_status"] == "not_started"


def test_rejected_action_cannot_execute(tmp_path, monkeypatch):
    monkeypatch.setattr(
        main,
        "DB_PATH",
        tmp_path / "rejected_test.db",
    )

    main.initialize_database()

    test_user = {
        "id": "test-user-123"
    }

    monkeypatch.setattr(
        main,
        "get_user_workspace_root",
        lambda user_id: tmp_path,
    )

    # Insert an action that has been rejected.
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
            VALUES (?, ?, ?, ?, ?, 'rejected', 'not_started')
            """,
            (
                test_user["id"],
                "Rejected copy test",
                "Testing execution after rejection.",
                "copy_file",
                "project/plan.txt → review/rejected_copy.txt",
            ),
        )

        action_id = cursor.lastrowid

    # The Executor must never be called.
    def executor_must_not_run(
        tool,
        target,
        workspace_root=None,
    ):
        raise AssertionError(
            "Executor was called for a rejected action!"
        )

    monkeypatch.setattr(
        main,
        "execute_file_action",
        executor_must_not_run,
    )

    # Attempt to execute the rejected action.
    with pytest.raises(HTTPException) as error:
        main.execute_approved_action(
            action_id,
            current_user=test_user,
        )

    assert error.value.status_code == 403

    # Confirm that the action remains rejected and unexecuted.
    with main.get_db_connection() as connection:
        action = connection.execute(
            """
            SELECT status, execution_status
            FROM actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()

    assert action["status"] == "rejected"
    assert action["execution_status"] == "not_started"
