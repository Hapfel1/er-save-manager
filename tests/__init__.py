"""Placeholder tests for er_save_manager."""


def test_version():
    """Test that version is defined."""
    from er_save_manager import __version__

    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0