"""Page-level SEO defaults and helpers for meta tags, Open Graph, and structured data.

Public API (backwards compatible):

* ``get_seo(request, **overrides)`` — build the per-page SEO context dict
  consumed by ``templates/core/base.html``.
* ``PAGE_SEO`` — mapping of ``url_name`` (``core:<name>``) to page-specific
  defaults (title, description, keywords, robots, ``no_json_ld`` …).
* ``SEO_TOPIC_KEYWORDS`` — shared keyword tail used across pages.

Performance notes:

* ``get_seo`` does only shallow dict copies; every PAGE_SEO value is a dict of
  immutable primitives so deepcopy is unnecessary.
* The expensive ``Organization`` + ``WebSite`` JSON-LD nodes depend only on
  effectively-immutable site settings and are cached with ``lru_cache``.
* The template context processor wraps the default ``seo`` dict in
  ``SimpleLazyObject``; views that provide their own ``seo`` in the context
  shadow it without ever triggering the default build.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

# Topics used for meta keywords and schema.org knowsAbout (3D, medals, sculpting, related craft).
SEO_TOPIC_KEYWORDS = (
    "3D моделирование, 3D modeling, скульптурный рельеф, bas-relief, барельеф, низкий рельеф, "
    "медали, medals, медальерное искусство, medallic art, нумизматика, numismatics, монеты, coin design, "
    "цифровая скульптура, digital sculpting, ZBrush, Blender, ArtCAM, Fusion 360, CNC рельеф, "
    "чеканка, casting, памятные медали, commemorative medals, AI арт, generative art, KurilenkoArt"
)

_DEFAULT_DESCRIPTION = (
    "Портфолио художника по 3D-моделированию медалей, монет и барельефов: цифровая скульптура, "
    "медальерное дело, низкий рельеф, ZBrush и AI-визуализация. Магазин моделей, статьи и заказ работ."
)

_DEFAULT_PAGE: dict[str, Any] = {
    "title": "KurilenkoArt — 3D медали, барельефы и цифровая скульптура",
    "description": _DEFAULT_DESCRIPTION,
    "keywords": SEO_TOPIC_KEYWORDS,
    "og_type": "website",
    "robots": "index, follow",
    "no_json_ld": False,
}

# Home SEO is reused by both the ``/`` and ``/homepage/`` URL aliases.
_HOMEPAGE_SEO: dict[str, Any] = {
    "title": "KurilenkoArt — 3D медали, барельефы, скульптура | портфолио и магазин",
    "description": _DEFAULT_DESCRIPTION,
    "keywords": SEO_TOPIC_KEYWORDS,
}

# url_name from core.urls (core:…)
PAGE_SEO: dict[str, dict[str, Any]] = {
    "homepage": _HOMEPAGE_SEO,
    "homepage_path": _HOMEPAGE_SEO,
    "about": {
        "title": "Обо мне — KurilenkoArt | 3D-художник, медали и барельефы",
        "description": (
            "Более 12 лет художественного 3D-моделирования медалей, монет и барельефов; "
            "медальерное и скульптурное направление, ZBrush, низкий рельеф и AI в рабочем процессе. "
            "Заказы и сотрудничество."
        ),
        "keywords": (
            "об авторе, 3D художник, медальер, скульптор 3D, барельеф, медали на заказ, "
            "низкий рельеф, ZBrush, студия KurilenkoArt, " + SEO_TOPIC_KEYWORDS
        ),
    },
    "portfolio": {
        "title": "Портфолио — KurilenkoArt | 3D барельефы, медали, AI-арт",
        "description": (
            "Галерея работ: 3D-барельефы, медали, монеты, скульптурный рельеф и AI-генеративный арт. "
            "ZBrush, Blender, цифровая скульптура и нейросетевые визуализации."
        ),
        "keywords": (
            "портфолио 3D, галерея барельефов, медали 3D, монеты 3D модель, digital sculpting showcase, "
            + SEO_TOPIC_KEYWORDS
        ),
    },
    "portfolio_gallery": {
        "title": "Галерея портфолио — KurilenkoArt",
        "description": (
            "Подборка изображений из портфолио: 3D-барельефы, медали и готовые изделия "
            "(Церковь Преображения Кижи, герб Санкт-Петербурга, Святой Даниил Московский, "
            "шлюпы «Надежда» и «Диана», Великомученик Пантелеймон, герб Кижи, "
            "Св. Великомученица Екатерина, Исаакиевский собор, Церковь Благовещения, "
            "герб Фороса, Храм Воскресения Христова, Собор Святой Софии) или AI-арт."
        ),
        "keywords": (
            "галерея 3D, галерея AI арт, портфолио изображения, готовые изделия медали, "
            "медаль герб Санкт-Петербурга, Кижи медаль, Святой Даниил Московский медаль, "
            "шлюп Надежда, шлюп Диана, Исаакиевский собор медаль, Храм Воскресения Христова, "
            "Собор Святой Софии медаль, " + SEO_TOPIC_KEYWORDS
        ),
    },
    "shop": {
        "title": "Магазин — KurilenkoArt | 3D-модели медалей и STL, принты",
        "description": (
            "Цифровые 3D-модели для ЧПУ и литья: рельефы, медали, STL; художественные принты. "
            "Скачивание и заказ от KurilenkoArt."
        ),
        "keywords": (
            "купить 3D модель медали, STL барельеф, цифровая скульптура магазин, 3D print art, "
            + SEO_TOPIC_KEYWORDS
        ),
    },
    "news": {
        "title": "Новости и статьи — KurilenkoArt | 3D, скульптура и AI",
        "description": (
            "Статьи о 3D-моделировании медалей и барельефов, цифровой скульптуре, ZBrush, "
            "литье и AI в творческом процессе."
        ),
        "keywords": "новости 3D, туториал ZBrush, медальерное дело блог, AI генерация арт, " + SEO_TOPIC_KEYWORDS,
    },
    "news_article": {
        "title": "Статья — KurilenkoArt",
        "description": "Материал о 3D-моделировании, медалях, барельефах и AI — KurilenkoArt.",
        "keywords": "статья 3D, медали моделирование, барельеф, " + SEO_TOPIC_KEYWORDS,
    },
    "forum": {
        "title": "Форум — KurilenkoArt | 3D и AI сообщество",
        "description": (
            "Обсуждения 3D-моделирования, медалей, барельефов, ZBrush, Blender и AI-инструментов."
        ),
        "keywords": "форум 3D художников, ZBrush сообщество, Midjourney, медальерный чат, " + SEO_TOPIC_KEYWORDS,
    },
    "forum_topic": {
        "title": "Тема форума — KurilenkoArt",
        "description": "Обсуждение 3D-моделирования и творческих инструментов на форуме KurilenkoArt.",
        "keywords": "форум 3D, рельеф печать, " + SEO_TOPIC_KEYWORDS,
    },
    "sign_up_login": {
        "title": "Вход и регистрация — KurilenkoArt",
        "description": "Вход в аккаунт KurilenkoArt.",
        "keywords": "вход, регистрация, KurilenkoArt",
        "robots": "noindex, nofollow",
        "no_json_ld": True,
    },
    "logout": {
        "title": "Выход — KurilenkoArt",
        "description": "Выход из аккаунта KurilenkoArt.",
        "keywords": "выход, KurilenkoArt",
        "robots": "noindex, nofollow",
        "no_json_ld": True,
    },
    "copyright": {
        "title": "Авторское право и лицензии — KurilenkoArt | 3D-работы",
        "description": (
            "Авторское право на 3D-модели, медали, изображения и контент KurilenkoArt: лицензии, "
            "заказ и передача прав."
        ),
        "keywords": "авторское право 3D модель, лицензия STL, медаль авторские права, KurilenkoArt",
    },
    "checkout": {
        "title": "Оформление заказа — KurilenkoArt",
        "description": "Корзина: оформление заказа на 3D-модели и цифровое искусство KurilenkoArt.",
        "keywords": "оформление заказа, KurilenkoArt",
        "robots": "noindex, follow",
        "no_json_ld": True,
    },
    "order_confirmation": {
        "title": "Заказ оформлен — KurilenkoArt",
        "description": "Подтверждение заказа в магазине KurilenkoArt.",
        "keywords": "заказ, KurilenkoArt",
        "robots": "noindex, nofollow",
        "no_json_ld": True,
    },
}

# Tuple → immutable; cached JSON-LD nodes share a reference safely.
_KNOWS_ABOUT: tuple[str, ...] = (
    "3D modeling",
    "Medallic art",
    "Numismatics",
    "Bas-relief sculpture",
    "Digital sculpting",
    "Low relief",
    "Commemorative medals",
    "Coin design",
    "ZBrush",
    "Blender 3D",
    "CNC machining relief",
    "AI-assisted art",
    "ArtCAM",
)


# ---------------------------------------------------------------------------
# URL / image helpers
# ---------------------------------------------------------------------------


def _absolute_url(request, path: str) -> str:
    path = path or "/"
    if not path.startswith("/"):
        path = "/" + path
    base = (getattr(settings, "PUBLIC_SITE_URL", "") or "").rstrip("/")
    if base:
        return urljoin(base + "/", path.lstrip("/"))
    return request.build_absolute_uri(path)


def _default_og_image_url(request) -> str:
    rel = static(getattr(settings, "SEO_DEFAULT_OG_IMAGE", "images/news/bas-relief-depth-1920x1200.png"))
    return _absolute_url(request, rel)


def _site_origin(request) -> str:
    """Homepage URL with trailing slash for Schema.org url fields."""
    u = _absolute_url(request, "/")
    return u if u.endswith("/") else u + "/"


# ---------------------------------------------------------------------------
# JSON-LD graph
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _static_graph_nodes(
    site_origin: str,
    site_name: str,
    email: str,
    logo_url: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return cached ``(Organization, WebSite)`` nodes for the site.

    The returned dicts are *shared* across requests — callers must never
    mutate them. Arguments are strings so the result is safely hashable.
    """
    base = site_origin.rstrip("/")
    org_id = f"{base}/#organization"
    web_id = f"{base}/#website"

    org = {
        "@type": "Organization",
        "@id": org_id,
        "name": site_name,
        "url": site_origin,
        "email": email,
        "logo": {"@type": "ImageObject", "url": logo_url},
        "description": _DEFAULT_DESCRIPTION,
        "knowsAbout": list(_KNOWS_ABOUT),
    }
    website = {
        "@type": "WebSite",
        "@id": web_id,
        "name": site_name,
        "url": site_origin,
        "inLanguage": ["ru-RU", "en-US"],
        "publisher": {"@id": org_id},
        "description": _DEFAULT_DESCRIPTION,
    }
    return org, website


def _build_json_ld_graph(
    request,
    data: dict[str, Any],
    article_ld: dict[str, Any] | None,
) -> str:
    """Render the JSON-LD ``@graph`` as a ``mark_safe`` JSON string.

    ``get_seo`` always pre-populates ``data["og_image"]`` and ``data["canonical_url"]``
    before calling this, so no fallbacks are needed here.
    """
    site_origin = _site_origin(request)
    site_name = data["site_name"]
    email = getattr(settings, "SEO_CONTACT_EMAIL", "me@nobito.ru")
    logo_url = data["og_image"]

    org, website = _static_graph_nodes(site_origin, site_name, email, logo_url)
    graph: list[dict[str, Any]] = [org, website]

    if article_ld:
        art = dict(article_ld)
        art.setdefault("@type", "Article")
        art.setdefault("image", logo_url)
        art.setdefault("inLanguage", "ru-RU")
        art.setdefault("mainEntityOfPage", data["canonical_url"])
        art["isPartOf"] = {"@id": website["@id"]}
        art.setdefault("publisher", {"@id": org["@id"]})
        graph.append(art)

    payload = {"@context": "https://schema.org", "@graph": graph}
    json_str = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return mark_safe(json_str)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def get_seo(request, **overrides: Any) -> dict[str, Any]:
    """Build SEO context for the current request.

    Any keyword override replaces the matching field in the merged
    ``_DEFAULT_PAGE`` + ``PAGE_SEO[url_name]`` dict. Special overrides:

    * ``canonical_path`` — path used for canonical and OG URLs; defaults
      to ``request.path``.
    * ``og_image_url`` — absolute image URL; defaults to the site's
      ``SEO_DEFAULT_OG_IMAGE``.
    * ``article_ld`` — dict merged into a schema.org ``Article`` node
      appended to the JSON-LD ``@graph`` (news article pages).
    * ``no_json_ld`` — when truthy, ``json_ld`` is emitted as an empty
      string.
    """
    article_ld = overrides.pop("article_ld", None)
    canonical_path = overrides.pop("canonical_path", None) or request.path
    og_image_url = overrides.pop("og_image_url", None) or _default_og_image_url(request)

    match = getattr(request, "resolver_match", None)
    url_name = match.url_name if match else ""

    # Shallow copies are safe: every value in the base dicts is a string / bool / None.
    data = dict(_DEFAULT_PAGE)
    page = PAGE_SEO.get(url_name)
    if page:
        data.update(page)
    data.update(overrides)

    data["canonical_url"] = _absolute_url(request, canonical_path)
    data["og_image"] = og_image_url
    data.setdefault("site_name", getattr(settings, "SEO_SITE_NAME", "KurilenkoArt"))

    data["json_ld"] = "" if data.get("no_json_ld") else _build_json_ld_graph(request, data, article_ld)

    return data
