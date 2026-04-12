from django.conf import settings

from .cart_utils import get_cart_summary
from .pricing import format_minor_as_rub
from .seo import get_seo
from .shop_data import SHOP_PREVIEW_PRODUCTS, SHOP_PRODUCTS


def site_seo(request):
    return {
        "seo": get_seo(request),
        "contact_email": getattr(settings, "SEO_CONTACT_EMAIL", "me@nobito.ru"),
    }


def shop_cart(request):
    summary = get_cart_summary(request)
    cents = summary["cart_subtotal_cents"]
    return {
        "shop_products": SHOP_PRODUCTS,
        "shop_preview_products": SHOP_PREVIEW_PRODUCTS,
        **summary,
        "cart_subtotal_formatted": format_minor_as_rub(cents),
    }
