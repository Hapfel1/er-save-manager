"""Tests for scripts/third_party_notices.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "third_party_notices.py"
_spec = importlib.util.spec_from_file_location("third_party_notices", _SCRIPT)
notices = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(notices)


def test_notices_cover_every_runtime_dependency():
    names = {d.metadata["Name"].lower() for d in notices.runtime_distributions()}
    assert {"customtkinter", "pillow", "requests", "certifi", "pycryptodome"} <= names
    assert "pytest" not in names

    text = notices.build(bundle=None)
    for dist in notices.runtime_distributions():
        assert f"{dist.metadata['Name']} {dist.version}" in text
    for project, *_ in notices.MIT_SOURCES:
        assert f"{project} (MIT)" in text
    assert "PSF" in text
