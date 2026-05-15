"""HTTP views package — re-exports for ``core.urls``."""

from ..view_utils import (  # noqa: F401 — tests patch ``core.views.*``
    AUTH_POST_LIMIT,
    AUTH_WINDOW_SECONDS,
    CART_API_POST_LIMIT,
    CART_API_WINDOW_SECONDS,
    CHECKOUT_IDEMPOTENCY_SESSION_KEY,
    CHECKOUT_IDEMPOTENCY_TTL_SECONDS,
    CHECKOUT_POST_LIMIT,
    CHECKOUT_WINDOW_SECONDS,
    CONFIRMED_ORDERS_MAX_KEPT,
    CONFIRMED_ORDERS_SESSION_KEY,
    CONTACT_FORM_POST_LIMIT,
    CONTACT_FORM_WINDOW_SECONDS,
    checkout_idempotency_key as _checkout_idempotency_key,
    client_ip as _client_ip,
    is_rate_limited as _is_rate_limited,
    remember_confirmed_order as _remember_confirmed_order,
    send_contact_email as _send_contact_email,
    session_owns_order as _session_owns_order,
)
from .shop import SHOP_PAGE_SIZE, _SHOP_ROW_LCM  # noqa: F401

from .auth import (
    CorePasswordResetCompleteView,
    CorePasswordResetConfirmView,
    CorePasswordResetDoneView,
    CorePasswordResetView,
    logout_view,
    profile_password_change,
    sign_up_login,
)
from .checkout_views import checkout, order_confirmation
from .errors import (
    forum,
    forum_topic,
    handler404,
    handler500,
    page_not_found_catchall,
    page_not_found_response,
    robots_txt,
)
from .pages import (
    about,
    copyright,
    homepage,
    news,
    news_article,
    portfolio,
    portfolio_gallery,
)
from .profile import (
    profile,
    profile_add_article,
    profile_add_product,
    profile_site_settings,
)
from .shop import cart_api, free_models, shop

__all__ = [
    "CorePasswordResetCompleteView",
    "CorePasswordResetConfirmView",
    "CorePasswordResetDoneView",
    "CorePasswordResetView",
    "about",
    "cart_api",
    "checkout",
    "copyright",
    "forum",
    "forum_topic",
    "free_models",
    "handler404",
    "handler500",
    "homepage",
    "logout_view",
    "news",
    "news_article",
    "order_confirmation",
    "page_not_found_catchall",
    "page_not_found_response",
    "portfolio",
    "portfolio_gallery",
    "profile",
    "profile_add_article",
    "profile_add_product",
    "profile_password_change",
    "profile_site_settings",
    "robots_txt",
    "shop",
    "sign_up_login",
]
