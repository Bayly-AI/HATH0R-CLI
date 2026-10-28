"""Shared test double: a bot whose every method returns a canned result."""

from __future__ import annotations

from typing import Any


class Seq(list):
    """Successive return values for successive method calls on a FakeBot."""


class FakeBot:
    """Stand-in for any bot: every method call returns ``result`` (or the next item of a Seq)."""

    def __init__(self, result: Any) -> None:
        self._results = list(result) if isinstance(result, Seq) else None
        self._result = result

    def __getattr__(self, name: str):
        def method(*args: Any, **kwargs: Any) -> Any:
            if self._results is not None:
                return self._results.pop(0) if len(self._results) > 1 else self._results[0]
            return self._result

        return method


def patch_bot(monkeypatch, module, name: str, result: Any) -> None:
    monkeypatch.setattr(module, name, lambda *a, **k: FakeBot(result))
