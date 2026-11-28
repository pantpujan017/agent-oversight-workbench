
import main
import policy
import workspace_paths

from ai_service import ActionProposal


def test_duplicate_proposal_is_not_added_twice(
    tmp_path,
    monkeypatch,
):
    # Create an isolated workspace.
    project = tmp_path / "project"
    review = tmp_path / "review"

    project.mkdir()
    review.mkdir()

    (project / "plan.txt").write_text("Test content")

    # Redirect path validation to the temporary workspace.
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

    # Use a separate temporary database.
    monkeypatch.setattr(
        main,
        "DB_PATH",
        tmp_path / "test_oversight.db",
    )

    main.initialize_database()

    # Simulate Gemini generating the same proposal each time.
    proposal = ActionProposal(
        title="Copy project plan",
        description="Copy a project document.",
        tool="copy_file",
        source_path="project/plan.txt",
        destination_path="review/duplicate_test.txt",
        needs_clarification=False,
        clarification_question="",
    )

    monkeypatch.setattr(
        main,
        "generate_action_proposal",
        lambda instruction, workspace_root=None: proposal
    )

    

    request = main.ProposalRequest(
        instruction="Copy plan.txt into review as duplicate_test.txt."
    )

    test_user = {
    "id": "test-user-123"
}

    monkeypatch.setattr(
    main,
    "get_user_workspace_root",
    lambda user_id: tmp_path,
)

    # Submit the first proposal.
    first_result = main.create_proposal(
    request,
    current_user=test_user,
)

    assert first_result["status"] == "pending_approval"

    first_action_id = first_result["action"]["id"]

    # Submit exactly the same proposal again.
    second_result = main.create_proposal(
    request,
    current_user=test_user,
)

    assert second_result["status"] == "duplicate"

    assert second_result["action"]["id"] == first_action_id

    # Confirm that the second submission created no new action.
    with main.get_db_connection() as connection:
        matching_actions = connection.execute(
            """
            SELECT COUNT(*)
            FROM actions
            WHERE tool = ?
              AND TRIM(target) = ?
            """,
            (
                "copy_file",
                "project/plan.txt → review/duplicate_test.txt",
            ),
        ).fetchone()[0]

    assert matching_actions == 1