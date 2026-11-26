
import pytest

from risk_assessment import assess_action_risk


def test_copy_file_has_low_risk():
    result = assess_action_risk("copy_file")

    assert result.risk_level == "low"
    assert "original" in result.reason.lower()


def test_rename_file_has_medium_risk():
    result = assess_action_risk("rename_file")

    assert result.risk_level == "medium"
    assert result.reason


def test_move_file_has_medium_risk():
    result = assess_action_risk("move_file")

    assert result.risk_level == "medium"
    assert result.reason


def test_unsupported_operation_cannot_be_assessed():
    with pytest.raises(ValueError):
        assess_action_risk("delete_file")
