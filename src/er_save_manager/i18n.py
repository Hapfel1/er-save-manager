"""Translation runtime for ER Save Manager.

Uses the standard library gettext module against compiled .mo catalogs in
``locales/<lang>/LC_MESSAGES/er_save_manager.mo``. No third-party runtime
dependency; Babel is only required to extract and compile catalogs.

Import the short aliases at module level and call them at widget construction:

    from er_save_manager.i18n import t

    ctk.CTkLabel(frame, text=t("Backup Manager"))

Do not call ``t()`` at import time on module-level constants. The catalog is
selected in ``init()`` during startup, so any string resolved before that point
is frozen to English.
"""

from __future__ import annotations

import gettext
import locale
import sys
from pathlib import Path

DOMAIN = "er_save_manager"

# Endonyms, shown untranslated in the language selector so a user who cannot
# read the current interface language can still find their own.
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "de": "Deutsch",
}

_translation: gettext.NullTranslations = gettext.NullTranslations()
_active_language: str = "en"


def get_locales_dir() -> Path:
    """Resolve the locales directory for source and frozen builds."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            # PyInstaller (Linux AppImage)
            return Path(sys._MEIPASS) / "er_save_manager" / "locales"
        # cx_Freeze (Windows)
        return Path(sys.executable).parent / "er_save_manager" / "locales"
    return Path(__file__).parent / "locales"


def available_languages() -> list[str]:
    """Return language codes that have a compiled catalog, English first.

    English is always present because it is the msgid source and needs no
    catalog.
    """
    codes = ["en"]
    locales_dir = get_locales_dir()
    if locales_dir.is_dir():
        for entry in sorted(locales_dir.iterdir()):
            if entry.name == "en":
                continue
            if (entry / "LC_MESSAGES" / f"{DOMAIN}.mo").is_file():
                codes.append(entry.name)
    return codes


def detect_system_language() -> str:
    """Return the system language code if a catalog exists for it, else 'en'."""
    try:
        code, _ = locale.getdefaultlocale()
    except (ValueError, TypeError):
        return "en"
    if not code:
        return "en"
    # Match the base language, so de_AT and de_CH both resolve to de
    base = code.split("_")[0].lower()
    return base if base in available_languages() else "en"


def init(language: str | None = None) -> str:
    """Activate a translation catalog and return the language actually used.

    Defaults to English. Only an explicit "auto" resolves via the system locale.
    Falls back to English if the requested catalog is missing or fails to load.
    """
    global _translation, _active_language

    if language == "auto":
        language = detect_system_language()
    elif language in (None, ""):
        language = "en"

    if language == "en":
        _translation = gettext.NullTranslations()
        _active_language = "en"
        return "en"

    try:
        _translation = gettext.translation(
            DOMAIN,
            localedir=str(get_locales_dir()),
            languages=[language],
            fallback=False,
        )
        _active_language = language
    except (OSError, FileNotFoundError):
        _translation = gettext.NullTranslations()
        _active_language = "en"

    return _active_language


def get_language() -> str:
    """Return the currently active language code."""
    return _active_language


def language_display_name(code: str) -> str:
    """Return the endonym for a language code, or the code itself if unknown."""
    return LANGUAGE_NAMES.get(code, code)


def N_(message: str) -> str:
    """Mark a string for extraction without translating it here.

    For strings that must stay English at the point of use because they double
    as a lookup key, but still need to reach translators. TranslatedTabview
    translates tab names at draw time, so the name passed to ``add()`` stays the
    key while the label the user sees is translated.

        tabs.add(N_("World State"))
        frame = tabs.tab("World State")
    """
    return message


def t(message: str) -> str:
    """Translate a string. Returns the original if untranslated."""
    return _translation.gettext(message)


def tn(singular: str, plural: str, n: int) -> str:
    """Translate a countable string using the catalog's plural rules.

    Both forms are needed even in English so translators receive the full set
    of forms their language requires.
    """
    return _translation.ngettext(singular, plural, n)


def tc(context: str, message: str) -> str:
    """Translate a string disambiguated by context.

    Use where the same English word needs different translations, for example
    ``tc("button", "Save")`` versus ``tc("noun", "Save")``.
    """
    return _translation.pgettext(context, message)
