import threading
import time
from typing import Callable, TypeVar, Any

_T = TypeVar("_T")
_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = threading.RLock()


def get_or_set_cache(key: str, ttl_seconds: int, factory: Callable[[], _T]) -> _T:
    """Simple in-process cache used for read-heavy endpoints.

    The value is invalidated after ttl_seconds and refreshed lazily.
    """
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            expires_at, value = cached
            if now < expires_at:
                return value
        value = factory()
        _cache[key] = (now + ttl_seconds, value)
        return value


def invalidate_cache(key: str | None = None):
    with _cache_lock:
        if key is None:
            _cache.clear()
        else:
            _cache.pop(key, None)
