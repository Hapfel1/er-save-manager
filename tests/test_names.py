"""Tests for validation.names."""

from __future__ import annotations

from er_save_manager.validation.names import name_problem, utf16_len


def test_utf16_len_counts_astral_characters_twice():
    assert utf16_len("Tarnished") == 9
    assert utf16_len("ü") == 1
    assert utf16_len("a\U0001f600") == 3


def test_valid_name():
    assert name_problem("Melina", 16) is None
    assert name_problem("x" * 16, 16) is None


def test_empty_and_blank():
    assert name_problem("", 16) == "Name is empty."
    assert name_problem("   ", 16, "Preset name") == "Preset name is empty."


def test_control_characters():
    assert "control character (U+0009)" in name_problem("a\tb", 16)
    assert "control character (U+000A)" in name_problem("a\nb", 16)


def test_lone_surrogate():
    assert "invalid character (U+D800)" in name_problem("a\ud800", 16)


def test_length_in_utf16_units():
    assert name_problem("x" * 15 + "\U0001f600", 16).startswith(
        "Name is too long: 17 of 16"
    )
    assert name_problem("x" * 14 + "\U0001f600", 16) is None
