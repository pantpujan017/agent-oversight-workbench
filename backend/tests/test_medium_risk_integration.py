
import pytest

import main
import policy
import workspace_paths

from ai_service import ActionProposal


@pytest.mark.parametrize(
    "tool, destination, expected_reason, expected_recommendation",
    [
        (
            "rename_file",
            "project/renamed.txt",
            "Renaming changes the original file's name "
            "and location reference.",
            "Carefully review the original filename and new filename.",
        ),
        (
            "move_file",
            "review/moved.txt",
            "Moving changes where the original file is stored.",
            "Carefully review the source and destination folders.",
        ),
    ],
)
def test_medium_risk_is_saved_with_proposal(
    tmp_path,
    monkeypatch,
    tool,
    destination,
    expected_reason,
    expected_recommendation,
):
    project = tmp_path / "project"
    review = tmp_path / "review"

    project.mkdir()
    review.mkdir()

    (project / "plan.txt").write_text("Test content")

    monkeypatch.setattr(
        workspace_paths,
        "WORKSPACE_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        policy,
        "WORKSPACE_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        main,
        "DB_PATH",
        tmp_path / "risk_test.db",
    )

    main.initialize_database()

    proposal = ActionProposal(
        title=f"Test {tool}",
        description="Testing medium-risk classification.",
        tool=tool,
        source_path="project/plan.txt",
        destination_path=destination,
        needs_clarification=False,
        clarification_question="",
    )

    test_user = {
    "id": "test-user-123"
}

    monkeypatch.setattr(
    main,
    "get_user_workspace_root",
    lambda user_id: tmp_path,
)

    monkeypatch.setattr(
        main,
        "generate_action_proposal",
        lambda instruction, workspace_root=None: proposal
    )

    result = main.create_proposal(
    main.ProposalRequest(
        instruction=f"Test {tool}."
    ),
    current_user=test_user,
)

    assert result["status"] == "pending_approval"

    action_id = result["action"]["id"]

    with main.get_db_connection() as connection:
        action = connection.execute(
            """
            SELECT risk_level, risk_reason, review_recommendation
            FROM actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()

    assert action["risk_level"] == "medium"
    assert action["risk_reason"] == expected_reason
    assert action["review_recommendation"] == expected_recommendation
