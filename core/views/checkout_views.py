import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .. import cart_utils
from ..checkout_service import (
    create_order,
    finalize_checkout_session,
    send_order_notification,
)
from ..forms import CheckoutForm
from ..models import Order
from ..pricing import format_minor_as_rub
from ..seo import get_seo
from ..view_utils import (
    CHECKOUT_IDEMPOTENCY_SESSION_KEY,
    CHECKOUT_IDEMPOTENCY_TTL_SECONDS,
    CHECKOUT_POST_LIMIT,
    CHECKOUT_WINDOW_SECONDS,
    checkout_idempotency_key,
    client_ip,
    is_rate_limited,
    remember_confirmed_order,
    session_owns_order,
)

logger = logging.getLogger(__name__)


def _checkout_ctx(request, form, lines, total_cents, idempotency_key):
    return {
        "form": form,
        "cart_lines": lines,
        "total_cents": total_cents,
        "total_formatted": format_minor_as_rub(total_cents),
        "checkout_idempotency_key": idempotency_key,
        "seo": get_seo(
            request,
            title="Оформление заказа — KurilenkoArt",
            description="Оформите заказ на 3D-модели и цифровое искусство.",
            canonical_path=request.path,
        ),
        "breadcrumbs": [
            {"label": "Главная", "url_name": "core:homepage"},
            {"label": "Магазин", "url_name": "core:shop"},
            {"label": "Оформление заказа", "current": True},
        ],
    }


@require_http_methods(["GET", "POST"])
def checkout(request):
    summary = cart_utils.get_cart_summary(request)
    lines = summary["cart_lines"]
    submitted_idempotency_key = (
        request.POST.get("idempotency_key")
        or request.headers.get("X-Idempotency-Key")
        or ""
    ).strip()
    ip_addr = client_ip(request)

    if request.method == "POST" and submitted_idempotency_key:
        idem_cache_key = f"idem:checkout:{ip_addr}:{submitted_idempotency_key}"
        existing_order_id = cache.get(idem_cache_key)
        if existing_order_id:
            remember_confirmed_order(request, existing_order_id)
            messages.info(request, f"Заказ №{existing_order_id} уже был оформлен ранее.")
            return redirect("core:order_confirmation", order_id=existing_order_id)

    if not lines:
        messages.warning(request, "Ваша корзина пуста. Добавьте товары для оформления заказа.")
        return redirect("core:shop")

    total_cents = summary["cart_subtotal_cents"]
    idempotency_key = checkout_idempotency_key(request)
    effective_idempotency_key = submitted_idempotency_key or idempotency_key

    if request.method == "POST":
        if is_rate_limited(
            request, "checkout_post", CHECKOUT_POST_LIMIT, CHECKOUT_WINDOW_SECONDS
        ):
            form = CheckoutForm(request.POST)
            return render(
                request,
                "core/checkout.html",
                _checkout_ctx(request, form, lines, total_cents, idempotency_key),
                status=429,
            )

        form = CheckoutForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            order = create_order(
                cleaned_data=data,
                lines=lines,
                total_cents=total_cents,
                ip_address=ip_addr,
            )
            finalize_checkout_session(request)
            if getattr(settings, "CONTACT_FORM_TRY_EMAIL", True):
                try:
                    send_order_notification(order, data)
                except Exception:
                    logger.exception("Order notification email failed (order id=%s)", order.pk)

            idem_cache_key = f"idem:checkout:{ip_addr}:{effective_idempotency_key}"
            cache.set(idem_cache_key, order.id, timeout=CHECKOUT_IDEMPOTENCY_TTL_SECONDS)
            request.session.pop(CHECKOUT_IDEMPOTENCY_SESSION_KEY, None)
            remember_confirmed_order(request, order.id)
            messages.success(
                request,
                f"Заказ №{order.id} успешно оформлен! Мы свяжемся с вами в ближайшее время.",
            )
            return redirect("core:order_confirmation", order_id=order.id)

        for _field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    else:
        form = CheckoutForm()

    return render(
        request,
        "core/checkout.html",
        _checkout_ctx(request, form, lines, total_cents, idempotency_key),
    )


def order_confirmation(request, order_id):
    if not session_owns_order(request, order_id):
        messages.error(request, "Заказ не найден.")
        return redirect("core:shop")

    order = get_object_or_404(Order.objects.prefetch_related("items"), id=order_id)
    return render(
        request,
        "core/order_confirmation.html",
        {
            "order": order,
            "seo": get_seo(
                request,
                title=f"Заказ №{order.id} подтверждён — KurilenkoArt",
                description=f"Ваш заказ №{order.id} успешно оформлен.",
                canonical_path=request.path,
            ),
        },
    )
