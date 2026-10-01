"""Linux emoji fallbacks for Tk widget text."""

from er_save_manager.ui.emoji_fallback import to_monochrome


def test_mapped_emoji_become_symbols():
    assert (
        to_monochrome("\N{THUMBS UP SIGN} Like")
        == "\N{BLACK UP-POINTING TRIANGLE} Like"
    )
    assert (
        to_monochrome("\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Warning")
        == "\N{WARNING SIGN} Warning"
    )


def test_unmapped_emoji_are_dropped_with_their_space():
    assert to_monochrome("\N{PACKAGE} GitHub Releases") == "GitHub Releases"
    assert to_monochrome("\N{HOT BEVERAGE} Support me") == "Support me"


def test_plain_text_is_unchanged():
    assert (
        to_monochrome(" padded \N{RIGHTWARDS ARROW} text ")
        == " padded \N{RIGHTWARDS ARROW} text "
    )
