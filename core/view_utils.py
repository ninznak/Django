"""Общие хелперы для HTTP-views (rate limit, сессия заказов, email)."""

from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.crypto import get_random_string

from .abuse import reserve, exceeded

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
    return not reserve(key, limit, window_seconds)


def rate_limit_key_exceeded(key: str, limit: int) -> bool:
    return exceeded(key, limit)


def is_rate_limited(request, scope: str, limit: int, window_seconds: int) -> bool:
    return rate_limit_key_hit(f"rate:{scope}:{client_ip(request)}", limit, window_seconds)


def email_content_fingerprint(*parts: str) -> str:
    import json
    normalized = [" ".join((part or "").split()).lower() for part in parts]
    return hashlib.sha256(json.dumps(normalized).encode("utf-8")).hexdigest()


def contact_email_fingerprint(cleaned: dict) -> str:
    return email_content_fingerprint(cleaned.get("email", ""), cleaned.get("subject", ""), cleaned.get("message", ""))


def reserve_email(scope, sender, *, fingerprint=None, dedupe_seconds=0, count=1):
    """Reserve all slots before SMTP. Conservative: failures still consume quota.

    count accounts for multiple password-reset recipients sharing one address.
    No SQL transaction remains open while talking to an external mail server.
    """
    if fingerprint and dedupe_seconds and not reserve(f"email_dedupe:{scope}:{fingerprint}", 1, dedupe_seconds):
        return False
    prefix = {"contact": "CONTACT_SUBMITTER", "order": "ORDER_NOTIFY", "password_reset": "PASSWORD_RESET"}[scope]
    sender_limit = getattr(settings, prefix + "_EMAIL_LIMIT", 3)
    window = getattr(settings, prefix + "_EMAIL_WINDOW_SECONDS", 3600)
    for _ in range(count):
        if not reserve(f"email_sender:{scope}:{sender.strip().lower()}", sender_limit, window):
            return False
        if not reserve("email_outbound:global", settings.EMAIL_OUTBOUND_LIMIT, settings.EMAIL_OUTBOUND_WINDOW_SECONDS):
            return False
    return True


def order_notification_fingerprint(order) -> str:
    items = "|".join(f"{item.product_id}x{item.quantity}" for item in order.items.all().order_by("product_id"))
    return email_content_fingerprint(order.email, str(order.total_cents), items)


def checkout_idempotency_key(request) -> str:
    if not request.session.session_key:
        request.session.create()
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
    if not reserve_email("contact", cleaned["email"], fingerprint=contact_email_fingerprint(cleaned), dedupe_seconds=settings.CONTACT_EMAIL_DEDUPE_SECONDS):
        logger.warning("Contact notification suppressed by quota or deduplication")
        return False
    send_contact_email(cleaned)
    return True


def deliver_order_notification(order, data: dict) -> bool:
    """Send an order notification unless anti-spam rules block it."""
    from .checkout_service import send_order_notification

    if not reserve_email("order", order.email, fingerprint=order_notification_fingerprint(order), dedupe_seconds=settings.ORDER_NOTIFY_DEDUPE_SECONDS):
        logger.warning("Order notification suppressed (order id=%s)", order.pk)
        return False
    send_order_notification(order, data)
    return True
