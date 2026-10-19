"""Tests for er_save_manager."""


def test_map_id():
    """Test MapId functionality."""
    from er_save_manager.parser import MapId

    # Test Limgrave map ID
    limgrave = MapId(bytes([0, 36, 42, 60]))
    assert limgrave.to_decimal() == "60 42 36 0"
    assert not limgrave.is_dlc()

    # Test DLC map ID
    dlc = MapId(bytes([0, 0, 0, 61]))
    assert dlc.is_dlc()


def test_fix_result():
    """Test FixResult dataclass."""
    from er_save_manager.fixes import FixResult

    # Not applied
    result = FixResult(applied=False, description="Not needed")
    assert not result
    assert result.description == "Not needed"

    # Applied
    result = FixResult(applied=True, description="Fixed", details=["Detail 1"])
    assert result
    assert len(result.details) == 1
