"""
Imports every module in the er_save_manager package, to catch NameError,
ImportError and SyntaxError anywhere without per-module tests.

pkgutil.walk_packages silently drops a package it fails to import unless
given an onerror callback, so walk errors are collected and asserted on too.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys

import er_save_manager


def test_every_module_imports():
    failed: dict[str, BaseException] = {}
    names = [er_save_manager.__name__] + [
        m.name
        for m in pkgutil.walk_packages(
            er_save_manager.__path__,
            prefix=f"{er_save_manager.__name__}.",
            onerror=lambda name: failed.setdefault(name, sys.exc_info()[1]),
        )
    ]
    assert len(names) > 1
    for name in names:
        try:
            importlib.import_module(name)
        except Exception as e:
            failed[name] = e
    assert not failed
