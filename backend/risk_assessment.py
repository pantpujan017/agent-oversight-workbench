
from dataclasses import dataclass
from typing import Literal


RiskLevel = Literal["low", "medium"]


@dataclass(frozen=True)
class RiskAssessment:
    risk_level: RiskLevel
    reason: str
    review_recommendation: str


def assess_action_risk(tool: str) -> RiskAssessment:
    """
    Assess the potential risk of a supported file operation.

    This function only classifies risk.
    It does not approve, reject, or execute actions.
    """

    if tool == "copy_file":
        return RiskAssessment(
            risk_level="low",
            reason=(
                "Copying creates another file while preserving "
                "the original."
            ),
            review_recommendation=(
                "Standard human review of the source and destination."
            ),
        )

    if tool == "rename_file":
        return RiskAssessment(
            risk_level="medium",
            reason=(
                "Renaming changes the original file's name "
                "and location reference."
            ),
            review_recommendation=(
                "Carefully review the original filename and new filename."
            ),
        )

    if tool == "move_file":
        return RiskAssessment(
            risk_level="medium",
            reason=(
                "Moving changes where the original file is stored."
            ),
            review_recommendation=(
                "Carefully review the source and destination folders."
            ),
        )

    raise ValueError(
        "Risk can only be assessed for supported file operations."
    )
