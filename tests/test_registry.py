# ==================================================================================================
# 📜 mattslib :: tests :: registry
# --------------------------------------------------------------------------------------------------
#  File         : tests/test_registry.py
#  Author       : Mathew Varghese <removed@example.invalid>
#  Created      : 2026-11-03
#  Version      : V1.1
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Proves registration, creation, lazy built-in loading and the error messages.
#
#  🧠 TESTING APPROACH
#    The lazy built-in is a real module written to tmp_path and put on sys.path, so the test
#    exercises the actual import mechanism rather than a mock of it.
#
#  📂 VERSION HISTORY
#
#    V1.1 (2026-11-03) - Mathew Varghese
#      - Initial test suite for Registry.
# ==================================================================================================

# ========================================
# 📂 Imports
# ========================================
import sys
import textwrap
from pathlib import Path

import pytest

from mattslib import Registry


class Plugin:
    def __init__(self, level: int = 1) -> None:
        self.level = level


# ========================================
# 📂 Registry Tests
# ========================================
def test_register_create_and_unregister() -> None:
    plugins: Registry[Plugin] = Registry("plugin")
    plugins.register("basic")(Plugin)
    assert plugins.create("basic", level=3).level == 3
    assert "basic" in plugins and plugins.available() == ["basic"]
    plugins.unregister("basic")
    plugins.unregister("never-registered")  # no error
    assert "basic" not in plugins


def test_duplicate_and_unknown_names_fail_clearly() -> None:
    plugins: Registry[Plugin] = Registry("plugin", builtins={"lazy": "some.module"})
    plugins.register("basic")(Plugin)
    with pytest.raises(ValueError, match="plugin 'basic' is already registered"):
        plugins.register("basic")(Plugin)
    with pytest.raises(ValueError, match=r"unknown plugin 'typo'; available: basic, lazy"):
        plugins.create("typo")


def test_builtins_are_imported_only_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins: Registry[Plugin] = Registry("plugin", builtins={"heavy": "heavy_plugin"})
    (tmp_path / "heavy_plugin.py").write_text(
        textwrap.dedent(
            """
            from test_registry import Plugin, REGISTRY
            REGISTRY.register("heavy")(Plugin)
            """
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(sys.modules[__name__], "REGISTRY", plugins, raising=False)
    monkeypatch.setitem(sys.modules, "test_registry", sys.modules[__name__])

    assert "heavy_plugin" not in sys.modules  # listed, but not imported yet
    assert "heavy" in plugins.available()
    assert plugins.create("heavy", level=5).level == 5
    assert "heavy_plugin" in sys.modules
    monkeypatch.delitem(sys.modules, "heavy_plugin")


def test_plugin_option_called_name_does_not_clash() -> None:
    class Named:
        def __init__(self, name: str) -> None:
            self.name = name

    named: Registry[Named] = Registry("named")
    named.register("n")(Named)
    assert named.create("n", name="inner").name == "inner"
