"""Shared pytest fixtures for er_save_manager tests."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SANITIZED_SAVE_ZIP = FIXTURES_DIR / "ER0000_sanitized.co2.zip"
SANITIZED_SAVE_NAME = "ER0000_sanitized.co2"


@pytest.fixture(scope="session")
def sanitized_save_path(tmp_path_factory) -> Path:
    """Path to the sanitized real Elden Ring save fixture.

    SteamID and character names are zeroed; all other slot data,
    including checksums, is real and structurally valid.

    The fixture is committed as a zip (*.co2 is gitignored project-wide),
    so it is extracted once per test session to a temp directory here.
    """
    extract_dir = tmp_path_factory.mktemp("er_save_manager_fixtures")
    with zipfile.ZipFile(SANITIZED_SAVE_ZIP) as zf:
        zf.extract(SANITIZED_SAVE_NAME, extract_dir)
    return extract_dir / SANITIZED_SAVE_NAME


@pytest.fixture
def sanitized_save(sanitized_save_path):
    """Freshly parsed Save object from the sanitized fixture.

    Function-scoped: Save._raw_data is a mutable bytearray, so each test
    gets its own Save instance rather than sharing mutation state with
    other tests. The underlying extracted file (session-scoped) is never
    written to directly, so re-parsing it per test is safe.
    """
    from er_save_manager.parser import load_save

    return load_save(str(sanitized_save_path))


@pytest.fixture
def sanitized_save_copy(sanitized_save_path, tmp_path):
    """A writable on-disk copy of the sanitized fixture.

    Use this when a test needs to call save.to_file() or otherwise persist
    changes, so the session-scoped extracted fixture is never modified.
    """
    dest = tmp_path / "ER0000_sanitized_copy.co2"
    shutil.copyfile(sanitized_save_path, dest)
    return dest
