"""Page-level SEO defaults and helpers for meta tags, Open Graph, and structured data."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

# Topics for meta keywords and schema.org knowsAbout (3D, medals, sculpting, related craft).
SEO_TOPIC_KEYWORDS = (
    "3D моделирование, 3D modeling, скульптурный рельеф, bas-relief, барельеф, низкий рельеф, "
    "медали, medals, медальерное искусство, medallic art, нумизматика, numismatics, монеты, coin design, "
    "цифровая скульптура, digital sculpting, ZBrush, Blender, ArtCAM, Fusion 360, CNC рельеф, "
    "чеканка, casting, памятные медали, commemorative medals, AI арт, generative art, KurilenkoArt"
)

_DEFAULT_PAGE = {
    "title": "KurilenkoArt — 3D медали, барельефы и цифровая скульптура",
    "description": (
        "Портфолио художника по 3D-моделированию медалей, монет и барельефов: цифровая скульптура, "
        "медальерное дело, низкий рельеф, ZBrush и AI-визуализация. Магазин моделей, статьи и заказ работ."
    ),
    "keywords": SEO_TOPIC_KEYWORDS,
    "og_type": "website",
    "robots": "index, follow",
    "no_json_ld": False,
}

# url_name from core.urls (core:…)
PAGE_SEO: dict[str, dict[str, Any]] = {
    "homepage": {
        "title": "KurilenkoArt — 3D медали, барельефы, скульптура | портфолио и магазин",
        "description": _DEFAULT_PAGE["description"],
        "keywords": SEO_TOPIC_KEYWORDS,
    },
    "homepage_path": {
        "title": "KurilenkoArt — 3D медали, барельефы, скульптура | портфолио и магазин",
        "description": _DEFAULT_PAGE["description"],
        "keywords": SEO_TOPIC_KEYWORDS,
    },
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

_KNOWS_ABOUT: list[str] = [
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
]


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


def _site_origin(request) -> str:
    """Homepage URL with trailing slash for Schema.org url fields."""
    u = _absolute_url(request, "/")
    return u if u.endswith("/") else u + "/"


def _build_json_ld_graph(
    request,
    data: dict[str, Any],
    article_ld: dict[str, Any] | None,
) -> str:
    site_origin = _site_origin(request)
    base = site_origin.rstrip("/")
    org_id = f"{base}/#organization"
    web_id = f"{base}/#website"

    site_name = data.get("site_name", "KurilenkoArt")
    email = getattr(settings, "SEO_CONTACT_EMAIL", "me@nobito.ru")
    logo_url = data.get("og_image") or _default_og_image_url(request)
    desc = data.get("description") or _DEFAULT_PAGE["description"]

    org: dict[str, Any] = {
        "@type": "Organization",
        "@id": org_id,
        "name": site_name,
        "url": site_origin,
        "email": email,
        "logo": {"@type": "ImageObject", "url": logo_url},
        "description": desc,
        "knowsAbout": _KNOWS_ABOUT,
    }

    website: dict[str, Any] = {
        "@type": "WebSite",
        "@id": web_id,
        "name": site_name,
        "url": site_origin,
        "inLanguage": ["ru-RU", "en-US"],
        "publisher": {"@id": org_id},
        "description": _DEFAULT_PAGE["description"],
    }

    graph: list[dict[str, Any]] = [org, website]

    if article_ld:
        art = dict(article_ld)
        art.setdefault("image", logo_url)
        art.setdefault("@type", "Article")
        art.setdefault("mainEntityOfPage", data["canonical_url"])
        art["isPartOf"] = {"@id": web_id}
        if "publisher" not in art:
            art["publisher"] = {"@id": org_id}
        graph.append(art)

    payload = {"@context": "https://schema.org", "@graph": graph}
    json_str = json.dumps(payload, ensure_ascii=False)
    json_str = json_str.replace("</", "<\\/")
    return mark_safe(json_str)


def get_seo(request, **overrides: Any) -> dict[str, Any]:
    """
    Build SEO context for the current request. View-specific values can be passed
    as keyword overrides (title, description, keywords, canonical_path, og_image_url, robots, etc.).

    Optional override ``article_ld``: dict for schema.org Article appended to JSON-LD @graph
    (used on news article pages). Populated fields may include headline, description, datePublished, etc.
    """
    match = getattr(request, "resolver_match", None)
    url_name = match.url_name if match else None
    key = url_name or ""

    article_ld = overrides.pop("article_ld", None)

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
        data["json_ld"] = _build_json_ld_graph(request, data, article_ld)

    return data
