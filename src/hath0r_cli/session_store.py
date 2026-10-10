"""Session store for cross-process agent state (HAHP handoffs, L2WS warm-starts, MCP session memory).

Backends
--------
* ``local`` (default): a JSON file shared by every process in the group, at
  ``<group root>/.hath0r/cache/session_memory.json`` (override with ``HATH0R_SESSION_PATH``).
  Writes are file-locked and atomic; TTLs are enforced on read and purged on write.
* ``redis`` (optional, ``pip install 'hath0r-cli[redis]'``): selected with
  ``HATH0R_SESSION_BACKEND=redis``; connection from ``HATH0R_REDIS_URL``
  (default ``redis://localhost:6379/0``). Keys are namespaced with ``hath0r:``.

Backend failures raise :class:`SessionStoreError` so callers can report them instead of
silently pretending a sync happened.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

try:  # POSIX advisory locking; on platforms without fcntl writes are still atomic.
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

BACKEND_ENV = "HATH0R_SESSION_BACKEND"
PATH_ENV = "HATH0R_SESSION_PATH"
REDIS_URL_ENV = "HATH0R_REDIS_URL"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
REDIS_PREFIX = "hath0r:"
_FORMAT_VERSION = 1


class SessionStoreError(RuntimeError):
    """Raised when the session backend cannot be read or written."""


class SessionStore(ABC):
    """Key/value session store with optional per-key TTL. Values must be JSON-serializable."""

    backend: str = "abstract"

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Return the value for ``key`` or ``None`` if missing or expired."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if ``key`` is present and not expired."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Store ``value`` under ``key``; returns ``{"key", "expires_at"}``."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete ``key``; returns True if it existed."""

    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        """List live keys starting with ``prefix`` (sorted)."""

    def describe(self) -> Dict[str, Any]:
        return {"backend": self.backend}


def _check_ttl(ttl_seconds: Optional[int]) -> None:
    if ttl_seconds is not None and ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be a positive integer")


def _encode(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise SessionStoreError(f"Value is not JSON-serializable: {exc}") from exc


class LocalJSONSessionStore(SessionStore):
    """File-backed store shared across processes on one machine."""

    backend = "local"

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def describe(self) -> Dict[str, Any]:
        return {"backend": self.backend, "path": str(self.path)}

    # -- file helpers -------------------------------------------------
    @contextmanager
    def _locked(self) -> Iterator[None]:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = self.path.with_name(self.path.name + ".lock")
            with open(lock_path, "a+", encoding="utf-8") as lock:
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    if fcntl is not None:
                        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        except OSError as exc:
            raise SessionStoreError(f"Session store not writable at {self.path}: {exc}") from exc

    def _read(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.is_file():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (OSError, ValueError) as exc:
            raise SessionStoreError(f"Session store unreadable at {self.path}: {exc}") from exc
        if not isinstance(raw, dict):
            return {}
        if raw.get("version") == _FORMAT_VERSION and isinstance(raw.get("entries"), dict):
            return dict(raw["entries"])
        # Legacy flat format written by hath0r <= 1.2: {key: value, "<key>__ttl": seconds}; TTL never enforced.
        return {
            k: {"value": v, "expires_at": None, "updated_at": None} for k, v in raw.items() if not k.endswith("__ttl")
        }

    def _write(self, entries: Dict[str, Dict[str, Any]]) -> None:
        payload = json.dumps({"version": _FORMAT_VERSION, "entries": entries}, indent=2, ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".session_memory.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self.path)
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise SessionStoreError(f"Session store not writable at {self.path}: {exc}") from exc

    @staticmethod
    def _live(entry: Dict[str, Any], now: float) -> bool:
        exp = entry.get("expires_at")
        return exp is None or float(exp) > now

    # -- API ------------------------------------------------------------
    def get(self, key: str) -> Optional[Any]:
        entry = self._read().get(key)
        if entry is None or not self._live(entry, time.time()):
            return None
        return entry.get("value")

    def exists(self, key: str) -> bool:
        entry = self._read().get(key)
        return entry is not None and self._live(entry, time.time())

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        _check_ttl(ttl_seconds)
        _encode(value)  # validate before touching the file
        now = time.time()
        expires_at = now + ttl_seconds if ttl_seconds else None
        with self._locked():
            entries = {k: e for k, e in self._read().items() if self._live(e, now)}
            entries[key] = {"value": value, "expires_at": expires_at, "updated_at": now}
            self._write(entries)
        return {"key": key, "expires_at": expires_at}

    def delete(self, key: str) -> bool:
        now = time.time()
        with self._locked():
            entries = {k: e for k, e in self._read().items() if self._live(e, now)}
            existed = entries.pop(key, None) is not None
            self._write(entries)
        return existed

    def list_keys(self, prefix: str = "") -> List[str]:
        now = time.time()
        return sorted(k for k, e in self._read().items() if k.startswith(prefix) and self._live(e, now))


class RedisSessionStore(SessionStore):
    """Redis-backed store (optional dependency ``redis``)."""

    backend = "redis"

    def __init__(self, url: str, client: Any = None) -> None:
        self.url = url
        if client is None:
            try:
                import redis  # type: ignore[import-not-found]
            except ImportError as exc:
                raise SessionStoreError(
                    "HATH0R_SESSION_BACKEND=redis requires the 'redis' package: pip install 'hath0r-cli[redis]'"
                ) from exc
            client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        self._client = client

    def describe(self) -> Dict[str, Any]:
        safe_url = self.url.split("@")[-1]  # never echo credentials
        return {"backend": self.backend, "url": safe_url}

    def _call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # redis.exceptions.* plus socket errors
            raise SessionStoreError(f"Redis session store unavailable ({self.describe()['url']}): {exc}") from exc

    def get(self, key: str) -> Optional[Any]:
        raw = self._call(self._client.get, REDIS_PREFIX + key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def exists(self, key: str) -> bool:
        return bool(self._call(self._client.exists, REDIS_PREFIX + key))

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        _check_ttl(ttl_seconds)
        payload = _encode(value)
        self._call(self._client.set, REDIS_PREFIX + key, payload, ex=ttl_seconds)
        return {"key": key, "expires_at": time.time() + ttl_seconds if ttl_seconds else None}

    def delete(self, key: str) -> bool:
        return bool(self._call(self._client.delete, REDIS_PREFIX + key))

    def list_keys(self, prefix: str = "") -> List[str]:
        keys = self._call(lambda: list(self._client.scan_iter(match=f"{REDIS_PREFIX}{prefix}*")))
        out = [(k.decode("utf-8") if isinstance(k, bytes) else k)[len(REDIS_PREFIX) :] for k in keys]
        return sorted(out)


def default_session_path() -> Path:
    """Shared local store location: ``HATH0R_SESSION_PATH`` or ``<group root>/.hath0r/cache/session_memory.json``."""
    override = os.environ.get(PATH_ENV)
    if override:
        return Path(override).expanduser()
    from hath0r_cli.common import _discover_group_root

    root = _discover_group_root() or Path.cwd()
    return root / ".hath0r" / "cache" / "session_memory.json"


def get_session_store() -> SessionStore:
    """Return the configured session store (``HATH0R_SESSION_BACKEND``: ``local`` | ``redis``)."""
    backend = (os.environ.get(BACKEND_ENV) or "local").strip().lower()
    if backend == "local":
        return LocalJSONSessionStore(default_session_path())
    if backend == "redis":
        return RedisSessionStore(os.environ.get(REDIS_URL_ENV) or DEFAULT_REDIS_URL)
    raise SessionStoreError(f"Unknown {BACKEND_ENV}={backend!r}; expected 'local' or 'redis'.")
