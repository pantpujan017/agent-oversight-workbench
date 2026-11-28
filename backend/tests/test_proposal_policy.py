
import main
import policy
import workspace_paths

from ai_service import ActionProposal


def test_backend_policy_blocks_unsafe_ai_proposal(
    tmp_path,
    monkeypatch,
):
    # Create an isolated test workspace.
    project = tmp_path / "project"
    project.mkdir()

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

    # Record the number of actions before the test.
    with main.get_db_connection() as connection:
        action_count_before = connection.execute(
            "SELECT COUNT(*) FROM actions"
        ).fetchone()[0]

    # Simulate Gemini returning an unsafe proposal.
    unsafe_proposal = ActionProposal(
        title="Copy project plan",
        description="Copy a project document.",
        tool="copy_file",
        source_path="project/plan.txt",
        destination_path="../outside.txt",
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

    # Replace Gemini with our controlled proposal.
    monkeypatch.setattr(
        main,
        "generate_action_proposal",
        lambda instruction, workspace_root=None: unsafe_proposal
    )

    # Submit the proposal through the actual backend route.
    result = main.create_proposal(
    main.ProposalRequest(
        instruction="Copy the project plan outside the workspace."
    ),
    current_user=test_user,
)

    # Confirm that the independent policy blocks it.
    assert result["status"] == "policy_blocked"

    assert "workspace" in result["message"].lower()

    # Confirm that the blocked proposal was not saved.
    with main.get_db_connection() as connection:
        action_count_after = connection.execute(
            "SELECT COUNT(*) FROM actions"
        ).fetchone()[0]

    assert action_count_after == action_count_before
