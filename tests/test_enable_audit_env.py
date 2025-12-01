import importlib
import sys
import os

import pytest


def reload_main_with_env(env_value: str):
    # Ensure environment is set before importing/reloading
    if env_value is None:
        if 'ENABLE_AUDIT' in os.environ:
            del os.environ['ENABLE_AUDIT']
    else:
        os.environ['ENABLE_AUDIT'] = env_value

    # Remove main from sys.modules so import runs top-level code again
    if 'main' in sys.modules:
        del sys.modules['main']

    # Import main (executes startup wiring)
    m = importlib.import_module('main')
    # Ensure audit module is available
    import core.audit as audit
    return audit


def test_enable_audit_false(monkeypatch):
    monkeypatch.setenv('ENABLE_AUDIT', 'false')
    # Ensure metrics disabled to avoid starting servers
    monkeypatch.delenv('ENABLE_METRICS', raising=False)

    if 'main' in sys.modules:
        del sys.modules['main']

    m = importlib.import_module('main')
    import core.audit as audit
    assert audit.is_audit_enabled() is False

    # cleanup
    audit.set_audit_enabled(True)
    if 'main' in sys.modules:
        del sys.modules['main']


def test_enable_audit_true(monkeypatch):
    monkeypatch.setenv('ENABLE_AUDIT', 'true')
    monkeypatch.delenv('ENABLE_METRICS', raising=False)

    if 'main' in sys.modules:
        del sys.modules['main']

    m = importlib.import_module('main')
    import core.audit as audit
    assert audit.is_audit_enabled() is True

    # cleanup
    audit.set_audit_enabled(True)
    if 'main' in sys.modules:
        del sys.modules['main']
