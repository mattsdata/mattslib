# ==================================================================================================
# 📜 mattslib :: registry
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/registry.py
#  Author       : Mathew Varghese <removed@example.invalid>
#  Created      : 2026-11-03
#  Version      : V1.1
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Many systems need "choose the implementation by name": a detection model, a sentiment
#    model, a storage backend, a notification channel. This module provides one small, typed
#    plugin registry for all of them, so each project does not reinvent it slightly differently.
#
#  🔧 WHAT IT DOES
#    - Registry[T]          : a named collection of factories that build objects of type T.
#    - Registry.register    : decorator that adds a class or factory under a name.
#    - Registry.create      : builds an instance by name, passing options through.
#    - Registry.available   : lists every name, including built-ins not yet imported.
#    - Registry.unregister  : removes a name (plugin unloading, test isolation).
#
#  🧠 DESIGN NOTES
#    - Built-ins are lazy: the registry knows "yolo lives in module X" and imports X only when
#      "yolo" is first requested. Heavy dependencies (PyTorch, transformers) never load unless used.
#    - Duplicate names fail loudly. Silently replacing a registered backend is a classic source of
#      "works on my machine" bugs when two plugins pick the same name.
#    - Unknown names fail with the list of valid ones, so a typo is a one-second fix.
#    - `name` is positional-only in create(), so a plugin may itself take an option called `name`.
#    - Extracted from ailab-vision when ailab-nlp became its second user (AI Lab ADR-0003).
#
#  📂 VERSION HISTORY
#
#    V1.1 (2026-11-03) - Mathew Varghese
#      - Initial release of the registry module (mattslib 1.1.0).
# ==================================================================================================
"""A small typed plugin registry with lazily imported built-ins.

Example:
    >>> class Greeter:
    ...     def __init__(self, name: str = "world") -> None:
    ...         self.name = name
    >>> greeters: Registry[Greeter] = Registry("greeter")
    >>> _ = greeters.register("plain")(Greeter)
    >>> greeters.create("plain", name="Mathew").name
    'Mathew'
"""

# ========================================
# 📂 Imports
# ========================================
from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from typing import Any, Generic, TypeVar

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# ========================================
# 📂 Registry
# ========================================
class Registry(Generic[T]):
    """Named factories for objects of type ``T``."""

    def __init__(self, kind: str, builtins: Mapping[str, str] | None = None) -> None:
        self.kind = kind  # used in error messages, e.g. "detector"
        self._builtins = dict(builtins or {})  # name -> module that registers it on import
        self._factories: dict[str, Callable[..., T]] = {}

    def register(self, name: str) -> Callable[[F], F]:
        """Decorator: register a class or factory under ``name``."""

        def decorator(factory: F) -> F:
            if name in self._factories:
                raise ValueError(f"{self.kind} {name!r} is already registered")
            self._factories[name] = factory
            return factory

        return decorator

    def unregister(self, name: str) -> None:
        """Remove ``name`` if present (no error if it is not registered)."""
        self._factories.pop(name, None)

    def available(self) -> list[str]:
        """All names create() accepts, including built-ins not yet imported."""
        return sorted(set(self._factories) | set(self._builtins))

    def __contains__(self, name: object) -> bool:
        return name in self._factories or name in self._builtins

    def create(self, name: str, /, **options: Any) -> T:
        """Build the object registered as ``name``, passing ``options`` to its factory."""
        if name not in self._factories and name in self._builtins:
            importlib.import_module(self._builtins[name])  # the module registers itself
        try:
            factory = self._factories[name]
        except KeyError:
            raise ValueError(
                f"unknown {self.kind} {name!r}; available: {', '.join(self.available())}"
            ) from None
        instance: T = factory(**options)
        return instance
