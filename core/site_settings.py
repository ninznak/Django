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


def contact_form_enabled() -> bool:
    """Включён ли приём сообщений с сайта (контактные формы)."""
    return bool(get_site_settings().contact_form_enabled)


def is_contact_email_domain_allowed(email: str) -> bool:
    """Проверка домена email отправителя против фильтра из SiteSetting.

    Режим «any» пропускает всех. В режиме «whitelist» домен письма должен
    совпадать с одним из разрешённых значений или заканчиваться на него
    («ru» покрывает mail.ru, «com» — gmail.com и т.д.). Пустой список
    в whitelist-режиме не блокирует всё подряд (fail-open) — форма настроек
    требует заполнить список при включении этого режима.
    """
    cfg = get_site_settings()
    if cfg.contact_email_domain_mode != "whitelist":
        return True
    allowed = cfg.contact_email_allowed_domains_list
    if not allowed:
        return True
    domain = (email or "").rsplit("@", 1)[-1].strip().lower()
    if not domain:
        return False
    return any(domain == d or domain.endswith("." + d) for d in allowed)
