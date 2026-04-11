"""Page-level SEO defaults and helpers for meta tags, Open Graph, and canonical URLs."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe


def _absolute_url(request, path: str) -> str:
    path = path or "/"
    if not path.startswith("/"):
        path = "/" + path
    base = getattr(settings, "PUBLIC_SITE_URL", "") or ""
    base = base.rstrip("/")
    if base:
        return urljoin(base + "/", path.lstrip("/"))
    return request.build_absolute_uri(path)


def _default_og_image_url(request) -> str:
    rel = static(getattr(settings, "SEO_DEFAULT_OG_IMAGE", "images/news/bas-relief-depth-1920x1200.png"))
    return _absolute_url(request, rel)


_DEFAULT_PAGE = {
    "title": "KurilenkoArt — Творческое портфолио",
    "description": (
        "3D барельефы, медали и монеты вместе с AI-изображениями и видео — "
        "одна творческая вселенная. Портфолио, магазин и новости."
    ),
    "keywords": (
        "3D моделирование, барельеф, медали, монеты, AI арт, портфолио, "
        "ZBrush, Blender, генеративный арт, KurilenkoArt"
    ),
    "og_type": "website",
    "robots": "index, follow",
    "no_json_ld": False,
}

# url_name from core.urls (core:…)
PAGE_SEO: dict[str, dict[str, Any]] = {
    "homepage": {
        "title": "KurilenkoArt — Творческое портфолио | 3D и AI",
        "description": _DEFAULT_PAGE["description"],
        "keywords": _DEFAULT_PAGE["keywords"],
    },
    "homepage_path": {
        "title": "KurilenkoArt — Творческое портфолио | 3D и AI",
        "description": _DEFAULT_PAGE["description"],
        "keywords": _DEFAULT_PAGE["keywords"],
    },
    "about": {
        "title": "Обо мне — KurilenkoArt | Мастерство и AI",
        "description": (
            "Моя студия: более 12 лет 3D-моделей медалей, монет и барельефов "
            "и исследование AI-изображений и видео. Заказы и сотрудничество."
        ),
        "keywords": "об авторе, 3D художник, медальерное дело, AI контент, моя студия, KurilenkoArt",
    },
    "portfolio": {
        "title": "Портфолио — KurilenkoArt | 3D барельефы и AI арт",
        "description": (
            "Галерея 3D барельефов, медалей, монет и AI-генеративного арта. "
            "Работы в ZBrush, Blender и нейросетевых пайплайнах."
        ),
        "keywords": "портфолио 3D, барельефы, медали, AI арт, галерея работ",
    },
    "shop": {
        "title": "Магазин — KurilenkoArt | Цифровые модели и принты",
        "description": (
            "Цифровые загрузки, файлы 3D-моделей и эксклюзивные принты "
            "от KurilenkoArt."
        ),
        "keywords": "магазин 3D моделей, цифровые загрузки, принты, медали",
    },
    "news": {
        "title": "Новости и статьи — KurilenkoArt | 3D и AI",
        "description": (
            "Материалы о 3D-моделировании, AI-генерации контента и пересечении "
            "традиционного мастерства с нейросетями."
        ),
        "keywords": "новости 3D, AI генерация, статьи, туториалы",
    },
    "news_article": {
        "title": "Статья — KurilenkoArt",
        "description": "Материал из раздела новостей KurilenkoArt о 3D и AI.",
        "keywords": "новости, статья, KurilenkoArt",
    },
    "forum": {
        "title": "Форум — KurilenkoArt | Сообщество 3D и AI",
        "description": (
            "Обсуждения 3D-моделирования, AI-инструментов и творческой практики "
            "с художниками и энтузиастами."
        ),
        "keywords": "форум 3D, Blender, ZBrush, Midjourney, сообщество",
    },
    "forum_topic": {
        "title": "Тема форума — KurilenkoArt",
        "description": "Обсуждение на форуме KurilenkoArt.",
        "keywords": "форум, обсуждение, KurilenkoArt",
    },
    "sign_up_login": {
        "title": "Вход и регистрация — KurilenkoArt",
        "description": "Вход в аккаунт KurilenkoArt.",
        "keywords": "вход, регистрация",
        "robots": "noindex, nofollow",
    },
    "copyright": {
        "title": "Авторское право — KurilenkoArt",
        "description": (
            "Информация об авторских правах на контент и работы KurilenkoArt / моя студия."
        ),
        "keywords": "авторское право, лицензия, KurilenkoArt",
    },
}


def organization_json_ld(seo: dict[str, Any]) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": seo.get("site_name", "KurilenkoArt"),
        "url": seo["canonical_url"],
        "email": getattr(settings, "SEO_CONTACT_EMAIL", "hello@creativesphere.art"),
    }


def get_seo(request, **overrides: Any) -> dict[str, Any]:
    """
    Build SEO context for the current request. View-specific values can be passed
    as keyword overrides (title, description, keywords, canonical_path, og_image_url, robots, etc.).
    """
    match = getattr(request, "resolver_match", None)
    url_name = match.url_name if match else None
    key = url_name or ""

    data = deepcopy(_DEFAULT_PAGE)
    page = PAGE_SEO.get(key)
    if page:
        data.update(deepcopy(page))

    canonical_path = overrides.pop("canonical_path", None)
    if canonical_path is None and match:
        canonical_path = request.path
    elif canonical_path is None:
        canonical_path = request.path

    og_image_url = overrides.pop("og_image_url", None)
    if og_image_url is None:
        og_image_url = _default_og_image_url(request)

    data.update(overrides)

    data["canonical_url"] = _absolute_url(request, canonical_path or "/")
    data["og_image"] = og_image_url

    site_name = getattr(settings, "SEO_SITE_NAME", "KurilenkoArt")
    data.setdefault("site_name", site_name)

    if data.get("no_json_ld"):
        data["json_ld"] = ""
    else:
        data["json_ld"] = mark_safe(
            json.dumps(organization_json_ld(data), ensure_ascii=False)
        )

    return data
