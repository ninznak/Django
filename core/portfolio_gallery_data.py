"""Static image lists for portfolio sub-galleries (/portfolio/3d/, /portfolio/ai/)."""

from __future__ import annotations

from typing import Any, TypedDict


class GalleryItem(TypedDict):
    image: str
    title_i18: str
    subtitle_i18: str
    alt: str


class GalleryMeta(TypedDict):
    slug: str
    portfolio_hash: str
    items: list[GalleryItem]


PORTFOLIO_GALLERIES: dict[str, GalleryMeta] = {
    "3d": {
        "slug": "3d",
        "portfolio_hash": "portfolio-3d",
        "items": [
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
        ],
    },
    "ai": {
        "slug": "ai",
        "portfolio_hash": "portfolio-ai",
        "items": [
            {
                "image": "images/featured/cosmic-weave-1920x1080.png",
                "title_i18": "portfolio_cosmic",
                "subtitle_i18": "portfolio_cosmic_cat",
                "alt": "Cosmic Weave",
            },
            {
                "image": "images/featured/verdant-machine-1920x2400.png",
                "title_i18": "portfolio_verdant",
                "subtitle_i18": "portfolio_verdant_cat",
                "alt": "Verdant Machine",
            },
            {
                "image": "images/shop/verdant-dreamscape-print-1920x1440.png",
                "title_i18": "portfolio_surreal",
                "subtitle_i18": "portfolio_surreal_cat",
                "alt": "Surreal Landscape",
            },
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
