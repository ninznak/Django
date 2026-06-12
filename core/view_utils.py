"""Общие хелперы для HTTP-views (rate limit, сессия заказов, email)."""

from __future__ import annotations

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


def is_rate_limited(request, scope: str, limit: int, window_seconds: int) -> bool:
    key = f"rate:{scope}:{client_ip(request)}"
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        hits = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        hits = 1
    return hits > limit


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
