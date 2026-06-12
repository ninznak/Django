"""Создание заказа из корзины и checkout-формы."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.mail import EmailMessage

from . import cart_utils
from .models import Order, OrderItem
from .pricing import format_minor_as_rub
from .shop_types import CartLine

if TYPE_CHECKING:
    from django.http import HttpRequest


def create_order(
    *,
    cleaned_data: dict[str, Any],
    lines: list[CartLine],
    total_cents: int,
    ip_address: str | None,
) -> Order:
    """Создать ``Order`` + ``OrderItem`` из валидной формы и строк корзины."""
    order = Order.objects.create(
        name=cleaned_data["name"],
        email=cleaned_data["email"],
        phone=cleaned_data.get("phone", ""),
        country=cleaned_data["country"],
        city=cleaned_data["city"],
        address=cleaned_data.get("address", ""),
        postal_code=cleaned_data.get("postal_code", ""),
        total_cents=total_cents,
        notes=cleaned_data.get("notes", ""),
        pd_consent=cleaned_data["pd_consent"],
        ip_address=ip_address,
    )
    for line in lines:
        product = line["product"]
        OrderItem.objects.create(
            order=order,
            product_id=product["id"],
            product_name=product["title"],
            product_price_cents=product["price_cents"],
            quantity=line["qty"],
        )
    return order


def finalize_checkout_session(request: "HttpRequest") -> None:
    """Очистить корзину после успешного заказа."""
    cart_utils.clear_cart(request.session)


def send_order_notification(order: Order, data: dict[str, Any]) -> None:
    """Уведомление администратору о новом заказе."""
    site = settings.SEO_SITE_NAME
    items_list = "\n".join(
        f"  • {item.product_name} × {item.quantity} — {format_minor_as_rub(item.total_cents)}"
        for item in order.items.all()
    )
    body = (
        f"Новый заказ №{order.id} на сайте {site}\n\n"
        f"=== Данные заказчика ===\n"
        f"Имя: {order.name}\n"
        f"Email: {order.email}\n"
        f"Телефон: {order.phone or 'не указан'}\n\n"
        f"=== Адрес доставки ===\n"
        f"Страна: {order.country}\n"
        f"Город: {order.city}\n"
        f"Адрес: {order.address}\n"
        f"Индекс: {order.postal_code or 'не указан'}\n\n"
        f"=== Товары ===\n{items_list}\n\n"
        f"=== Итого ===\nСумма: {format_minor_as_rub(order.total_cents)}\n\n"
        f"=== Комментарий ===\n{order.notes or 'нет'}\n\n"
        f"Согласие на обработку ПДн: {'да' if order.pd_consent else 'нет'}\n"
        f"Дата согласия: {order.pd_consent_date:%Y-%m-%d %H:%M:%S}\n"
        f"IP-адрес: {order.ip_address or 'не определён'}\n"
    )
    msg = EmailMessage(
        subject=f"[{site} заказ] Новый заказ №{order.id} от {order.name}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=list(settings.CONTACT_FORM_RECIPIENTS),
        reply_to=[order.email],
    )
    msg.send(fail_silently=False)
