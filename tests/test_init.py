"""Tests for er_save_manager."""


def test_version():
    """Test that version is defined."""
    from er_save_manager import __version__

    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_imports():
    """Test that main imports work."""
    from er_save_manager import HorseState, MapId, Save, UserDataX, load_save

    assert Save is not None
    assert load_save is not None
    assert UserDataX is not None
    assert MapId is not None
    assert HorseState is not None


def test_fixes_imports():
    """Test that fix modules import correctly."""
    from er_save_manager.fixes import (
        ALL_FIXES,
        BaseFix,
        FixResult,
        TorrentFix,
    )

    assert len(ALL_FIXES) > 0
    assert BaseFix is not None
    assert FixResult is not None
    assert TorrentFix is not None


def test_backup_imports():
    """Test that backup module imports correctly."""
    from er_save_manager.backup import BackupManager

    assert BackupManager is not None


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
