"""Shop catalog — IDs match SiteReplitVersion / Next.js for consistency."""

from __future__ import annotations

SHOP_PRODUCTS: list[dict] = [
    {
        "id": 1,
        "title": "Eagle Relief — STL File",
        "type_i18": "shop_digital",
        "price": "$29",
        "price_cents": 2900,
        "img": "images/shop/eagle-relief-stl-1920x1440.png",
        "alt": "Eagle bas relief 3D model STL preview",
        "badge": "Best Seller",
        "description": "High-quality bas relief 3D model ready for CNC machining and casting.",
    },
    {
        "id": 2,
        "title": "Heritage Coin Pack (5 designs)",
        "type_i18": "shop_3d_bundle",
        "price": "$49",
        "price_cents": 4900,
        "img": "images/shop/heritage-coin-pack-1920x1440.png",
        "alt": "Heritage coin collection 3D model bundle",
        "badge": "Bundle",
        "description": "Five unique commemorative coin designs in production-ready format.",
    },
    {
        "id": 3,
        "title": "Verdant Dreamscape — Print",
        "type_i18": "shop_fine_art",
        "price": "$75",
        "price_cents": 7500,
        "img": "images/shop/verdant-dreamscape-print-1920x1440.png",
        "alt": "Verdant dreamscape fine art print",
        "badge": "Limited",
        "description": "Museum-quality fine art print of AI-generated landscape.",
    },
    {
        "id": 4,
        "title": "Medal Base Template",
        "type_i18": "shop_digital",
        "price": "$19",
        "price_cents": 1900,
        "img": "images/shop/medal-base-template-1920x1440.png",
        "alt": "Medal base template",
        "badge": None,
        "description": "Professional starting template for custom medal designs.",
    },
    {
        "id": 5,
        "title": "Roman Panel Relief",
        "type_i18": "shop_digital",
        "price": "$35",
        "price_cents": 3500,
        "img": "images/featured/bronze-victory-relief-1920x2400.jpg",
        "alt": "Roman-style bas relief panel",
        "badge": "New",
        "description": "Classical Roman-style decorative panel relief model.",
    },
    {
        "id": 6,
        "title": "AI Concept Pack",
        "type_i18": "shop_digital",
        "price": "$25",
        "price_cents": 2500,
        "img": "images/news/midjourney-1920x1200.png",
        "alt": "AI-generated concept art pack",
        "badge": None,
        "description": "Collection of AI-generated concept art for inspiration.",
    },
]

SHOP_PREVIEW_PRODUCTS = SHOP_PRODUCTS[:4]

_BY_ID = {p["id"]: p for p in SHOP_PRODUCTS}


def get_product(product_id: int) -> dict | None:
    return _BY_ID.get(int(product_id))
