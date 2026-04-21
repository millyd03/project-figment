import time
import json
from typing import Optional
from config import settings

try:
    import redis
except Exception:
    redis = None


class AuthStore:
    """Simple abstraction for PKCE state storage.

    Uses Redis when `settings.redis_url` is set, otherwise falls back to an in-memory dict
    (suitable only for local single-process development).
    """

    def __init__(self):
        self._mem = {}
        self._use_redis = bool(settings.redis_url) and redis is not None
        self._client = None
        if self._use_redis:
            self._client = redis.from_url(settings.redis_url)

    def put_state(self, state: str, data: dict, ttl: int = 600):
        payload = json.dumps({**data, "created_at": time.time()})
        if self._use_redis:
            # Use simple setex for TTL
            self._client.setex(f"pkce:{state}", ttl, payload)
        else:
            self._mem[state] = {**data, "created_at": time.time(), "ttl": ttl}

    def pop_state(self, state: str) -> Optional[dict]:
        if self._use_redis:
            key = f"pkce:{state}"
            raw = self._client.get(key)
            if not raw:
                return None
            try:
                self._client.delete(key)
            except Exception:
                pass
            return json.loads(raw)
        else:
            item = self._mem.pop(state, None)
            if not item:
                return None
            # Check TTL
            if time.time() - item.get("created_at", 0) > item.get("ttl", 600):
                return None
            return item

    def has_state(self, state: str) -> bool:
        if self._use_redis:
            return self._client.exists(f"pkce:{state}") == 1
        return state in self._mem

    def cleanup(self):
        # No-op for Redis (TTL handles it); for mem store, remove expired
        if self._use_redis:
            return
        now = time.time()
        for k in list(self._mem.keys()):
            item = self._mem.get(k)
            if now - item.get("created_at", 0) > item.get("ttl", 600):
                del self._mem[k]


auth_store = AuthStore()
