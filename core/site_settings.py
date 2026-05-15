"""Кэшированный доступ к singleton ``SiteSetting``."""

from __future__ import annotations

from django.core.cache import cache

from .models import SiteSetting

_CACHE_KEY = "core:site_setting:v1"
_CACHE_TTL = 300


def get_site_settings() -> SiteSetting:
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached
    obj = SiteSetting.load()
    cache.set(_CACHE_KEY, obj, timeout=_CACHE_TTL)
    return obj


def invalidate_site_settings_cache() -> None:
    cache.delete(_CACHE_KEY)
