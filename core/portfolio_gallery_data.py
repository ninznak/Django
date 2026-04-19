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
        "image": "images/news/zdanie.png",
        "title_i18": "portfolio_moscow_building",
        "subtitle_i18": "portfolio_moscow_building_cat",
        "alt": "Moscow Building Bas-Relief",
    },
]


# Явный порядок работ, которые должны идти первыми в галерее 3D.
# Имена — нормализованные stem'ы файлов (без расширения, в нижнем регистре).
_PORTFOLIO_3D_TOP_ORDER: tuple[str, ...] = (
    "model9",
    "model8",
    "model99",
    "efrosyn777",
    "georg777",
    "ushak777",
    "model4",
    "model00",
    "modelmid",
    "model10",
    "jimm",
    "model000",
)


# Работы (по stem'у), которые НЕ должны появляться в 3D-галерее.
_PORTFOLIO_3D_EXCLUDED: frozenset[str] = frozenset({
    "model6",
    "model11",
})


# Особые подписи для приоритетных работ. Ключ — stem файла (lower-case).
_PORTFOLIO_3D_CAPTIONS: dict[str, tuple[str, str, str]] = {
    "model9": (
        "portfolio_model9_title",
        "portfolio_model9_cat",
        "3D модель портрет (барельеф)",
    ),
    "jimm": (
        "featured_jimm_title",
        "featured_jimm_cat",
        "Трехмерная модель персонажа Червяк Джимм",
    ),
    "efrosyn777": (
        "portfolio_efrosyn_title",
        "portfolio_efrosyn_cat",
        "Святая Евфросиния Полоцкая",
    ),
    "georg777": (
        "portfolio_georg_title",
        "portfolio_georg_cat",
        "Святой Георгий Победоносец",
    ),
    "ushak777": (
        "portfolio_ushak_title",
        "portfolio_ushak_cat",
        "Святой праведный воин Феодор Ушаков",
    ),
}


def _news_3d_items() -> list[GalleryItem]:
    """Все 3D-иллюстрации из ``static/images/news`` (``model*``, ``*777*``, ``jimm``), отсортированные по имени."""
    if not _NEWS_IMAGES_DIR.is_dir():
        return []
    items: list[GalleryItem] = []
    for path in sorted(_NEWS_IMAGES_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        name_lower = path.name.lower()
        stem = path.stem.lower()
        if (
            "model" not in name_lower
            and "777" not in name_lower
            and stem != "jimm"
        ):
            continue
        if stem in _PORTFOLIO_3D_EXCLUDED:
            continue
        alt_default = path.stem.replace("_", " ").replace("-", " ")
        title_i18, subtitle_i18, alt = _PORTFOLIO_3D_CAPTIONS.get(
            stem,
            ("portfolio_3d_model_piece", "portfolio_3d_model_piece_cat", alt_default),
        )
        items.append(
            {
                "image": f"images/news/{path.name}",
                "title_i18": title_i18,
                "subtitle_i18": subtitle_i18,
                "alt": alt,
            }
        )
    return items


def portfolio_3d_gallery_items() -> list[GalleryItem]:
    """Приоритетные работы (``_PORTFOLIO_3D_TOP_ORDER``) в заданном порядке,
    затем курируемая база (``_PORTFOLIO_3D_BASE``), затем остальные ``model*``
    из папки news в алфавитном порядке. Для каждого приоритетного имени берётся
    первый подходящий файл (на случай ``.jpg``/``.jpeg``-дубликатов)."""
    pool = _news_3d_items()
    used_paths: set[str] = set()
    top: list[GalleryItem] = []
    for stem in _PORTFOLIO_3D_TOP_ORDER:
        for item in pool:
            if item["image"] in used_paths:
                continue
            if Path(item["image"]).stem.lower() == stem:
                top.append(item)
                used_paths.add(item["image"])
                break
    rest = [item for item in pool if item["image"] not in used_paths]
    return top + _PORTFOLIO_3D_BASE + rest


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
