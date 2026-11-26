
import main
import policy
import workspace_paths

from ai_service import ActionProposal


def test_new_proposal_saves_risk_information(
    tmp_path,
    monkeypatch,
):
    # Create an isolated workspace.
    project = tmp_path / "project"
    review = tmp_path / "review"

    project.mkdir()
    review.mkdir()

    (project / "plan.txt").write_text("Test content")

    # Redirect workspace validation.
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
        tmp_path / "risk_test.db",
    )

    main.initialize_database()

    # Simulate a safe AI-generated proposal.
    proposal = ActionProposal(
        title="Copy project plan",
        description="Copy a project document.",
        tool="copy_file",
        source_path="project/plan.txt",
        destination_path="review/risk_test.txt",
        needs_clarification=False,
        clarification_question="",
    )

    monkeypatch.setattr(
        main,
        "generate_action_proposal",
        lambda instruction: proposal,
    )

    # Submit the proposal through the backend.
    result = main.create_proposal(
        main.ProposalRequest(
            instruction="Copy the project plan."
        )
    )

    assert result["status"] == "pending_approval"

    action_id = result["action"]["id"]

    # Verify risk information was saved in SQLite.
    with main.get_db_connection() as connection:
        action = connection.execute(
            """
            SELECT
                risk_level,
                risk_reason,
                review_recommendation
            FROM actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()

    assert action["risk_level"] == "low"

    assert (
        action["risk_reason"]
        == "Copying creates another file while preserving the original."
    )

    assert (
        action["review_recommendation"]
        == "Standard human review of the source and destination."
    )
