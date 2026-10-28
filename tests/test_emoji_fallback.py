"""Linux emoji fallbacks for Tk widget text."""

from er_save_manager.ui.emoji_fallback import to_monochrome


def test_to_monochrome():
    # Mapped emoji become symbols, unmapped ones are dropped with their space
    assert (
        to_monochrome("\N{THUMBS UP SIGN} Like")
        == "\N{BLACK UP-POINTING TRIANGLE} Like"
    )
    assert (
        to_monochrome("\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Warning")
        == "\N{WARNING SIGN} Warning"
    )
    assert to_monochrome("\N{PACKAGE} GitHub Releases") == "GitHub Releases"
    text = " padded \N{RIGHTWARDS ARROW} text "
    assert to_monochrome(text) == text
