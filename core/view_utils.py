"""Общие хелперы для HTTP-views (rate limit, сессия заказов, email)."""

from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)

CONTACT_FORM_POST_LIMIT = getattr(settings, "CONTACT_FORM_POST_LIMIT", 5)
CONTACT_FORM_WINDOW_SECONDS = getattr(settings, "CONTACT_FORM_WINDOW_SECONDS", 600)
AUTH_POST_LIMIT = getattr(settings, "AUTH_POST_LIMIT", 20)
AUTH_WINDOW_SECONDS = getattr(settings, "AUTH_WINDOW_SECONDS", 300)
CART_API_POST_LIMIT = getattr(settings, "CART_API_POST_LIMIT", 120)
CART_API_WINDOW_SECONDS = getattr(settings, "CART_API_WINDOW_SECONDS", 60)
CHECKOUT_POST_LIMIT = getattr(settings, "CHECKOUT_POST_LIMIT", 8)
CHECKOUT_WINDOW_SECONDS = getattr(settings, "CHECKOUT_WINDOW_SECONDS", 600)
CHECKOUT_IDEMPOTENCY_SESSION_KEY = getattr(
    settings, "CHECKOUT_IDEMPOTENCY_SESSION_KEY", "checkout_idempotency_key"
)
CHECKOUT_IDEMPOTENCY_TTL_SECONDS = getattr(
    settings, "CHECKOUT_IDEMPOTENCY_TTL_SECONDS", 60 * 60 * 24
)

CONFIRMED_ORDERS_SESSION_KEY = "confirmed_order_ids"
CONFIRMED_ORDERS_MAX_KEPT = 20


def remember_confirmed_order(request, order_id: int) -> None:
    ids = list(request.session.get(CONFIRMED_ORDERS_SESSION_KEY) or [])
    if order_id in ids:
        return
    ids.append(int(order_id))
    if len(ids) > CONFIRMED_ORDERS_MAX_KEPT:
        ids = ids[-CONFIRMED_ORDERS_MAX_KEPT:]
    request.session[CONFIRMED_ORDERS_SESSION_KEY] = ids


def session_owns_order(request, order_id: int) -> bool:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_staff", False):
        return True
    ids = request.session.get(CONFIRMED_ORDERS_SESSION_KEY) or []
    try:
        return int(order_id) in {int(x) for x in ids}
    except (TypeError, ValueError):
        return False


def client_ip(request) -> str:
    # X-Real-IP is set by our Nginx to $remote_addr (overwriting any client
    # value), so it cannot be spoofed through the proxy. X-Forwarded-For is
    # built with $proxy_add_x_forwarded_for, which APPENDS the real IP to
    # client-supplied values — only the LAST entry is trustworthy. Never use
    # the first entry: that would let clients rotate fake IPs to bypass
    # rate limiting and poison Order.ip_address.
    real_ip = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if real_ip:
        return real_ip
    forwarded_for = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip() or "unknown"
    return (request.META.get("REMOTE_ADDR") or "unknown").strip() or "unknown"


def rate_limit_key_hit(key: str, limit: int, window_seconds: int) -> bool:
    """Increment a cache counter; return True when over *limit*."""
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        hits = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        hits = 1
    return hits > limit


def rate_limit_key_exceeded(key: str, limit: int) -> bool:
    """Peek at a counter without incrementing."""
    hits = cache.get(key)
    if hits is None:
        return False
    try:
        return int(hits) >= limit
    except (TypeError, ValueError):
        return False


def is_rate_limited(request, scope: str, limit: int, window_seconds: int) -> bool:
    key = f"rate:{scope}:{client_ip(request)}"
    return rate_limit_key_hit(key, limit, window_seconds)


def _normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def email_content_fingerprint(*parts: str) -> str:
    normalized = "|".join(" ".join((part or "").split()).lower() for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _email_dedupe_key(scope: str, fingerprint: str) -> str:
    return f"email_dedupe:{scope}:{fingerprint}"


def is_duplicate_email(scope: str, fingerprint: str) -> bool:
    return cache.get(_email_dedupe_key(scope, fingerprint)) is not None


def mark_email_dedupe(scope: str, fingerprint: str, ttl_seconds: int) -> None:
    cache.set(_email_dedupe_key(scope, fingerprint), 1, timeout=ttl_seconds)


def global_email_cap_reached() -> bool:
    return rate_limit_key_exceeded(
        "rate:email_outbound:global",
        getattr(settings, "EMAIL_OUTBOUND_LIMIT", 40),
    )


def record_global_email_sent() -> None:
    rate_limit_key_hit(
        "rate:email_outbound:global",
        getattr(settings, "EMAIL_OUTBOUND_LIMIT", 40),
        getattr(settings, "EMAIL_OUTBOUND_WINDOW_SECONDS", 3600),
    )


def contact_email_fingerprint(cleaned: dict) -> str:
    return email_content_fingerprint(
        _normalize_email(cleaned.get("email", "")),
        cleaned.get("subject", ""),
        cleaned.get("message", ""),
    )


def contact_email_blocked_reason(cleaned: dict) -> str | None:
    dedupe_seconds = getattr(settings, "CONTACT_EMAIL_DEDUPE_SECONDS", 1800)
    if dedupe_seconds and is_duplicate_email("contact", contact_email_fingerprint(cleaned)):
        return "duplicate_content"
    submitter = _normalize_email(cleaned.get("email", ""))
    submitter_limit = getattr(settings, "CONTACT_SUBMITTER_EMAIL_LIMIT", 3)
    if submitter and rate_limit_key_exceeded(
        f"rate:contact_submitter:{submitter}",
        submitter_limit,
    ):
        return "submitter_rate"
    if global_email_cap_reached():
        return "global_cap"
    return None


def record_contact_email_sent(cleaned: dict) -> None:
    dedupe_seconds = getattr(settings, "CONTACT_EMAIL_DEDUPE_SECONDS", 1800)
    if dedupe_seconds:
        mark_email_dedupe("contact", contact_email_fingerprint(cleaned), dedupe_seconds)
    submitter = _normalize_email(cleaned.get("email", ""))
    if submitter:
        rate_limit_key_hit(
            f"rate:contact_submitter:{submitter}",
            getattr(settings, "CONTACT_SUBMITTER_EMAIL_LIMIT", 3),
            getattr(settings, "CONTACT_SUBMITTER_EMAIL_WINDOW_SECONDS", 3600),
        )
    record_global_email_sent()


def order_notification_fingerprint(order) -> str:
    items = "|".join(
        f"{item.product_id}x{item.quantity}"
        for item in order.items.all().order_by("product_id")
    )
    return email_content_fingerprint(
        _normalize_email(order.email),
        str(order.total_cents),
        items,
    )


def order_notification_blocked_reason(order) -> str | None:
    dedupe_seconds = getattr(settings, "ORDER_NOTIFY_DEDUPE_SECONDS", 600)
    if dedupe_seconds and is_duplicate_email("order", order_notification_fingerprint(order)):
        return "duplicate_order"
    submitter = _normalize_email(order.email)
    if submitter and rate_limit_key_exceeded(
        f"rate:order_notify:{submitter}",
        getattr(settings, "ORDER_NOTIFY_EMAIL_LIMIT", 5),
    ):
        return "submitter_rate"
    if global_email_cap_reached():
        return "global_cap"
    return None


def record_order_notification_sent(order) -> None:
    dedupe_seconds = getattr(settings, "ORDER_NOTIFY_DEDUPE_SECONDS", 600)
    if dedupe_seconds:
        mark_email_dedupe("order", order_notification_fingerprint(order), dedupe_seconds)
    submitter = _normalize_email(order.email)
    if submitter:
        rate_limit_key_hit(
            f"rate:order_notify:{submitter}",
            getattr(settings, "ORDER_NOTIFY_EMAIL_LIMIT", 5),
            getattr(settings, "ORDER_NOTIFY_EMAIL_WINDOW_SECONDS", 3600),
        )
    record_global_email_sent()


def password_reset_email_blocked_reason(email: str) -> str | None:
    normalized = _normalize_email(email)
    if not normalized:
        return None
    if rate_limit_key_exceeded(
        f"rate:password_reset:{normalized}",
        getattr(settings, "PASSWORD_RESET_EMAIL_LIMIT", 3),
    ):
        return "submitter_rate"
    if global_email_cap_reached():
        return "global_cap"
    return None


def record_password_reset_email_sent(email: str) -> None:
    normalized = _normalize_email(email)
    if not normalized:
        return
    rate_limit_key_hit(
        f"rate:password_reset:{normalized}",
        getattr(settings, "PASSWORD_RESET_EMAIL_LIMIT", 3),
        getattr(settings, "PASSWORD_RESET_EMAIL_WINDOW_SECONDS", 3600),
    )
    record_global_email_sent()


def checkout_idempotency_key(request) -> str:
    key = (request.session.get(CHECKOUT_IDEMPOTENCY_SESSION_KEY) or "").strip()
    if not key:
        key = get_random_string(32)
        request.session[CHECKOUT_IDEMPOTENCY_SESSION_KEY] = key
    return key


def safe_contact_subject(raw: str, max_len: int = 200) -> str:
    cleaned = " ".join((raw or "").splitlines()).strip()
    if not cleaned:
        return "(no subject)"
    return cleaned[:max_len]


def send_contact_email(cleaned: dict) -> None:
    site = settings.SEO_SITE_NAME
    subj = safe_contact_subject(cleaned["subject"])
    body = (
        f"Name: {cleaned['name']}\n"
        f"From (form): {cleaned['email']}\n\n"
        f"{cleaned['message']}"
    )
    msg = EmailMessage(
        subject=f"[{site} contact] {subj}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=list(settings.CONTACT_FORM_RECIPIENTS),
        reply_to=[cleaned["email"]],
    )
    msg.send(fail_silently=False)


def deliver_contact_email(cleaned: dict) -> bool:
    """Send a contact notification unless anti-spam rules block it."""
    reason = contact_email_blocked_reason(cleaned)
    if reason:
        logger.warning("Contact notification suppressed (%s)", reason)
        return False
    send_contact_email(cleaned)
    record_contact_email_sent(cleaned)
    return True


def deliver_order_notification(order, data: dict) -> bool:
    """Send an order notification unless anti-spam rules block it."""
    from .checkout_service import send_order_notification

    reason = order_notification_blocked_reason(order)
    if reason:
        logger.warning(
            "Order notification suppressed (order id=%s, reason=%s)",
            order.pk,
            reason,
        )
        return False
    send_order_notification(order, data)
    record_order_notification_sent(order)
    return True
