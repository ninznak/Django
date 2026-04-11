from .cart_utils import get_cart_summary
from .seo import get_seo
from .shop_data import SHOP_PREVIEW_PRODUCTS, SHOP_PRODUCTS


def site_seo(request):
    return {"seo": get_seo(request)}


def shop_cart(request):
    summary = get_cart_summary(request)
    cents = summary["cart_subtotal_cents"]
    return {
        "shop_products": SHOP_PRODUCTS,
        "shop_preview_products": SHOP_PREVIEW_PRODUCTS,
        **summary,
        "cart_subtotal_dollars": f"{cents / 100:.2f}",
    }
