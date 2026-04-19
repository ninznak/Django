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


def analytics(request):
    """Yandex.Metrica / Top.Mail.ru counter IDs for ``templates/core/includes/analytics.html``."""
    y_raw = getattr(settings, "YANDEX_METRIKA_ID", "") or ""
    m_raw = getattr(settings, "MAILRU_TOP_ID", "") or ""
    yandex_metrika_id = int(y_raw) if y_raw.isdigit() else None
    mailru_top_id = int(m_raw) if m_raw.isdigit() else None
    return {
        "yandex_metrika_id": yandex_metrika_id,
        "mailru_top_id": mailru_top_id,
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
