"""Resilient Redis cache backend for FlexyRide Corporate.
Tries Redis first. If Redis is unavailable or down, gracefully falls back
to an in-memory LocMemCache so caching continues to work seamlessly without
raising 500 ConnectionRefused errors.
"""
import logging
import redis
from django.core.cache.backends.locmem import LocMemCache
from django.core.cache.backends.redis import RedisCache

logger = logging.getLogger(__name__)


class ResilientRedisCache(RedisCache):
    """Redis cache backend that falls back to in-memory cache on connection errors."""

    def __init__(self, server, params):
        super().__init__(server, params)
        self._server = server
        self._servers = getattr(self, '_servers', [server] if isinstance(server, str) else server)
        self._fallback = LocMemCache('flexyride-corp-locmem-fallback', params)
        self._logged_down = False

    def _on_error(self, operation, key, error):
        if not self._logged_down:
            logger.warning(
                "[Cache] Redis on %s unavailable (%s). Falling back to in-memory LocMemCache.",
                self._server,
                error
            )
            self._logged_down = True

    def get(self, key, default=None, version=None):
        try:
            val = super().get(key, default=default, version=version)
            self._logged_down = False
            return val
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("get", key, e)
            return self._fallback.get(key, default=default, version=version)

    def set(self, key, value, timeout=None, version=None):
        try:
            res = super().set(key, value, timeout=timeout, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("set", key, e)
            return self._fallback.set(key, value, timeout=timeout, version=version)

    def add(self, key, value, timeout=None, version=None):
        try:
            res = super().add(key, value, timeout=timeout, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("add", key, e)
            return self._fallback.add(key, value, timeout=timeout, version=version)

    def delete(self, key, version=None):
        try:
            res = super().delete(key, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("delete", key, e)
            return self._fallback.delete(key, version=version)

    def touch(self, key, timeout=None, version=None):
        try:
            res = super().touch(key, timeout=timeout, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("touch", key, e)
            return self._fallback.touch(key, timeout=timeout, version=version)

    def clear(self):
        try:
            res = super().clear()
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("clear", None, e)
            return self._fallback.clear()

    def has_key(self, key, version=None):
        try:
            res = super().has_key(key, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("has_key", key, e)
            return self._fallback.has_key(key, version=version)

    def incr(self, key, delta=1, version=None):
        try:
            res = super().incr(key, delta=delta, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("incr", key, e)
            return self._fallback.incr(key, delta=delta, version=version)

    def decr(self, key, delta=1, version=None):
        try:
            res = super().decr(key, delta=delta, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("decr", key, e)
            return self._fallback.decr(key, delta=delta, version=version)

    def get_many(self, keys, version=None):
        try:
            res = super().get_many(keys, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("get_many", keys, e)
            return self._fallback.get_many(keys, version=version)

    def set_many(self, data, timeout=None, version=None):
        try:
            res = super().set_many(data, timeout=timeout, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("set_many", None, e)
            return self._fallback.set_many(data, timeout=timeout, version=version)

    def delete_many(self, keys, version=None):
        try:
            res = super().delete_many(keys, version=version)
            self._logged_down = False
            return res
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            self._on_error("delete_many", keys, e)
            return self._fallback.delete_many(keys, version=version)
