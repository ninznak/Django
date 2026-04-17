from django.conf import settings
from django.utils.functional import SimpleLazyObject

from .cart_utils import get_cart_summary
from .pricing import format_minor_as_rub
from .seo import get_seo
from .shop_data import SHOP_PREVIEW_PRODUCTS, SHOP_PRODUCTS


def site_seo(request):
    # Lazy: views that provide their own ``seo`` in the template context shadow
    # this entry and the default build is never triggered — saves one full
    # JSON-LD serialization per request on those pages.
    return {
        "seo": SimpleLazyObject(lambda: get_seo(request)),
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
