"""Static image lists for portfolio sub-galleries (/portfolio/3d/, /portfolio/ai/)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

_NEWS_IMAGES_DIR = Path(__file__).resolve().parent.parent / "static" / "images" / "news"
_MEDALS_IMAGES_DIR = Path(__file__).resolve().parent.parent / "static" / "images" / "medals"


class GalleryItem(TypedDict):
    image: str
    title_i18: str
    subtitle_i18: str
    alt: str


class GalleryMeta(TypedDict):
    slug: str
    portfolio_hash: str
    items: list[GalleryItem]


def news_model_gallery_items() -> list[GalleryItem]:
    """Файлы в ``static/images/news``, в имени которых есть ``model`` (без учёта регистра)."""
    if not _NEWS_IMAGES_DIR.is_dir():
        return []
    out: list[GalleryItem] = []
    for path in sorted(_NEWS_IMAGES_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or "model" not in path.name.lower():
            continue
        stem = path.stem.replace("_", " ").replace("-", " ")
        out.append(
            {
                "image": f"images/news/{path.name}",
                "title_i18": "portfolio_3d_model_piece",
                "subtitle_i18": "portfolio_3d_model_piece_cat",
                "alt": stem,
            }
        )
    return out


def _ai_sort_key(path: Path) -> tuple[int, str]:
    """Сортировка: сначала ``AI1``, ``AI2`` … по номеру, потом остальное по имени."""
    stem = path.stem.lower()
    if stem.startswith("ai"):
        tail = stem[len("ai"):]
        if tail.isdigit():
            return (0, f"{int(tail):04d}")
    return (1, stem)


def news_ai_gallery_items() -> list[GalleryItem]:
    """Файлы в ``static/images/news``, в имени которых есть ``ai`` (без учёта регистра)."""
    if not _NEWS_IMAGES_DIR.is_dir():
        return []
    out: list[GalleryItem] = []
    for path in sorted(_NEWS_IMAGES_DIR.iterdir(), key=_ai_sort_key):
        if not path.is_file() or "ai" not in path.name.lower():
            continue
        stem = path.stem.replace("_", " ").replace("-", " ")
        out.append(
            {
                "image": f"images/news/{path.name}",
                "title_i18": "portfolio_ai_piece",
                "subtitle_i18": "portfolio_ai_piece_cat",
                "alt": stem,
            }
        )
    return out


_PORTFOLIO_3D_BASE: list[GalleryItem] = [
    {
        "image": "images/featured/bronze-victory-relief-1920x2400.jpg",
        "title_i18": "portfolio_bronze_victory",
        "subtitle_i18": "portfolio_bronze_victory_cat",
        "alt": "Bronze Victory Relief",
    },
    {
        "image": "images/featured/numismatic-heritage-1920x1280.jpg",
        "title_i18": "portfolio_numismatic",
        "subtitle_i18": "portfolio_numismatic_cat",
        "alt": "Numismatic Heritage",
    },
    {
        "image": "images/shop/eagle-relief-stl-1920x1440.png",
        "title_i18": "portfolio_commemorative",
        "subtitle_i18": "portfolio_commemorative_cat",
        "alt": "Commemorative Medal",
    },
]


def portfolio_3d_gallery_items() -> list[GalleryItem]:
    """Сначала model9 из news (если есть), затем три основных работы, затем остальные model*."""
    extras = news_model_gallery_items()
    model9_lead: list[GalleryItem] = []
    rest: list[GalleryItem] = []
    for item in extras:
        stem = Path(item["image"]).stem.lower()
        if stem == "model9":
            if not model9_lead:
                model9_lead.append(
                    {
                        **item,
                        "title_i18": "portfolio_model9_title",
                        "subtitle_i18": "portfolio_model9_cat",
                        "alt": "3D модельпортрет (барельеф)",
                    }
                )
        else:
            rest.append(item)
    return model9_lead + _PORTFOLIO_3D_BASE + rest


# Per-file captions for готовые изделия (медали). Keys are the lowercased
# filename stem; values carry i18n key, Russian caption, English caption and
# alt text (used on the preview card and in SEO descriptions).
MEDAL_CAPTIONS: dict[str, dict[str, str]] = {
    "medal1":  {"i18": "portfolio_medal_1",  "ru": "Медаль герб Санкт-Петербурга",     "en": "Saint Petersburg Coat of Arms Medal"},
    "medal2":  {"i18": "portfolio_medal_2",  "ru": "Шлюп «Надежда»",                    "en": "Sloop Nadezhda"},
    "medal3":  {"i18": "portfolio_medal_3",  "ru": "Великомученик Пантелеймон",         "en": "Great Martyr Panteleimon"},
    "medal4":  {"i18": "portfolio_medal_4",  "ru": "Шлюп «Диана»",                      "en": "Sloop Diana"},
    "medal5":  {"i18": "portfolio_medal_5",  "ru": "Церковь Преображения, Кижи",        "en": "Church of the Transfiguration, Kizhi"},
    "medal6":  {"i18": "portfolio_medal_6",  "ru": "Святой Даниил Московский",          "en": "Saint Daniel of Moscow"},
    "medal7":  {"i18": "portfolio_medal_7",  "ru": "Герб города Кижи",                  "en": "Kizhi Coat of Arms"},
    "medal8":  {"i18": "portfolio_medal_8",  "ru": "Шлюп «Надежда»",                    "en": "Sloop Nadezhda"},
    "medal9":  {"i18": "portfolio_medal_9",  "ru": "Св. Великомученица Екатерина",      "en": "Great Martyr Catherine"},
    "medal10": {"i18": "portfolio_medal_10", "ru": "Исаакиевский собор",                "en": "Saint Isaac's Cathedral"},
    "medal11": {"i18": "portfolio_medal_11", "ru": "Церковь Благовещения",              "en": "Church of the Annunciation"},
    "medal12": {"i18": "portfolio_medal_12", "ru": "Герб Фороса",                       "en": "Foros Coat of Arms"},
    "medal13": {"i18": "portfolio_medal_13", "ru": "Храм Воскресения Христова",         "en": "Church of the Resurrection of Christ"},
    "img_2097": {"i18": "portfolio_medal_sofia", "ru": "Собор Святой Софии",            "en": "Hagia Sophia Cathedral"},
}


def _medal_stem(path: Path) -> str:
    """Нормализованный ключ для ``MEDAL_CAPTIONS`` (lower-case, дефисы → подчёркивания)."""
    return path.stem.lower().replace("-", "_")


def _medal_sort_key(path: Path) -> tuple[int, str]:
    """Сортировка: сначала medal1, medal2, ..., medal13, потом всё остальное по имени."""
    stem = path.stem.lower()
    if stem.startswith("medal"):
        tail = stem[len("medal"):]
        if tail.isdigit():
            return (0, f"{int(tail):04d}")
    return (1, stem)


def portfolio_products_gallery_items() -> list[GalleryItem]:
    """Все изображения из ``static/images/medals`` с индивидуальными подписями."""
    if not _MEDALS_IMAGES_DIR.is_dir():
        return []
    out: list[GalleryItem] = []
    for path in sorted(_MEDALS_IMAGES_DIR.iterdir(), key=_medal_sort_key):
        if not path.is_file():
            continue
        caption = MEDAL_CAPTIONS.get(_medal_stem(path))
        if caption:
            title_i18 = caption["i18"]
            alt = caption["en"]
        else:
            title_i18 = "portfolio_products_item"
            alt = path.stem.replace("_", " ").replace("-", " ")
        out.append(
            {
                "image": f"images/medals/{path.name}",
                "title_i18": title_i18,
                "subtitle_i18": "portfolio_products_item_cat",
                "alt": alt,
            }
        )
    return out


def _medal_seo_description() -> str:
    """Человеко-читаемая строка всех готовых изделий для meta description."""
    names = [MEDAL_CAPTIONS[k]["ru"] for k in (
        "medal1", "medal2", "medal3", "medal4", "medal5", "medal6", "medal7",
        "medal8", "medal9", "medal10", "medal11", "medal12", "medal13", "img_2097",
    )]
    return ", ".join(names)


PORTFOLIO_GALLERIES: dict[str, GalleryMeta] = {
    "3d": {
        "slug": "3d",
        "portfolio_hash": "portfolio-3d",
        "items": portfolio_3d_gallery_items(),
    },
    "products": {
        "slug": "products",
        "portfolio_hash": "portfolio-products",
        "items": portfolio_products_gallery_items(),
    },
    "ai": {
        "slug": "ai",
        "portfolio_hash": "portfolio-ai",
        "items": [
            {
                "image": "images/featured/verdant-machine-1920x2400.png",
                "title_i18": "portfolio_verdant",
                "subtitle_i18": "portfolio_verdant_cat",
                "alt": "Verdant Machine",
            },
            *news_ai_gallery_items(),
        ],
    },
}


# Russian defaults match site SEO style; view can still override via get_seo.
PORTFOLIO_GALLERY_SEO: dict[str, dict[str, str]] = {
    "3d": {
        "title": "3D барельефы и медали — галерея | KurilenkoArt",
        "description": (
            "Галерея 3D-работ: бронзовые барельефы, нумизматика, памятные медали и цифровая скульптура."
        ),
    },
    "products": {
        "title": "Готовые изделия — галерея медалей | KurilenkoArt",
        "description": (
            "Галерея готовых изделий по авторским 3D-моделям KurilenkoArt: "
            + _medal_seo_description()
            + ". Отлитые и изготовленные медали и памятные награды — частные заказы."
        ),
    },
    "ai": {
        "title": "AI-арт — галерея | KurilenkoArt",
        "description": (
            "Галерея AI-изображений: генеративный арт, нейросетевые пейзажи и художественные визуализации."
        ),
    },
}


def gallery_context(slug: str) -> dict[str, Any] | None:
    slug = slug.strip().lower()
    meta = PORTFOLIO_GALLERIES.get(slug)
    if not meta:
        return None
    seo = PORTFOLIO_GALLERY_SEO.get(slug, PORTFOLIO_GALLERY_SEO["3d"])
    return {"gallery": meta, "gallery_slug": slug, "gallery_seo": seo}
