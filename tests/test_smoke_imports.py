"""
Import-smoke test.

Walks every module in the er_save_manager package and imports it. Catches
NameError, AttributeError, ImportError, and SyntaxError introduced by a
change anywhere in the codebase (e.g. a missing variable, a broken import,
a typo in a name), without needing per-module behavioral tests.

pkgutil.walk_packages must import each package to recurse into its
submodules, and silently drops any package it fails to import unless
given an onerror callback. Without that callback, a genuinely broken
package (e.g. a missing dependency) would vanish from MODULE_NAMES
instead of failing the suite, so failures are recorded and asserted on
separately below.

This does not exercise GUI widget behavior, only module-level import.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys

import pytest

import er_save_manager

_WALK_ERRORS: dict[str, BaseException] = {}


def _record_walk_error(module_name: str) -> None:
    _WALK_ERRORS[module_name] = sys.exc_info()[1]


def _discover_modules() -> list[str]:
    modules = [er_save_manager.__name__]
    for module_info in pkgutil.walk_packages(
        er_save_manager.__path__,
        prefix=f"{er_save_manager.__name__}.",
        onerror=_record_walk_error,
    ):
        modules.append(module_info.name)
    return modules


MODULE_NAMES = _discover_modules()


def test_discovered_at_least_one_module():
    assert len(MODULE_NAMES) > 1, "walk_packages found no er_save_manager submodules"


def test_no_package_walk_errors():
    """A package that fails to import during discovery must fail loudly,
    not just be silently excluded from the module list below.
    """
    assert not _WALK_ERRORS, f"failed to walk packages: {_WALK_ERRORS}"


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_imports(module_name):
    importlib.import_module(module_name)
