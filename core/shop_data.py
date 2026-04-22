"""Адаптер над моделью :class:`core.models.Product` для остального кода.

Исторически каталог магазина жил как питоновский список словарей
``SHOP_PRODUCTS``. Сейчас источник данных — таблица ``core_product``,
которую можно редактировать через админку. Этот модуль оставлен как
тонкая обёртка, чтобы:

* шаблоны/тесты продолжали работать со словарной формой товара
  (``{"id", "title", "price", "price_cents", "img", "alt", ...}``),
* корзина и ``OrderItem`` продолжали видеть минорные единицы (копейки),
* новые места могли обращаться напрямую к queryset'у
  ``Product.objects.filter(kind="shop", is_published=True)``.

``SHOP_PRODUCTS`` и ``SHOP_PREVIEW_PRODUCTS`` больше **не** модульные
константы — это функции, потому что:

1. импорт модуля не должен делать запросы в БД (иначе падает
   ``manage.py migrate`` на чистой БД);
2. свежесть данных важна — после редактирования в админке страница
   /shop/ должна сразу видеть новое состояние.
"""

from __future__ import annotations

from typing import Any

from .models import Product


def _shop_queryset():
    return Product.objects.filter(
        kind=Product.Kind.SHOP,
        is_published=True,
    ).order_by("display_order", "id")


def _free_queryset():
    return Product.objects.filter(
        kind=Product.Kind.FREE,
        is_published=True,
    ).order_by("display_order", "id")


def get_shop_products() -> list[dict[str, Any]]:
    """Опубликованные товары магазина в словарной форме."""
    return [p.as_cart_dict() for p in _shop_queryset()]


def get_shop_preview_products(limit: int = 4) -> list[dict[str, Any]]:
    """Первые ``limit`` *доступных к покупке* товаров для превью на главной.

    Превью на ``homepage.html`` должно показывать только покупабельное —
    распроданные позиции и placeholder-карточки («Скоро новый товар»)
    скрыты независимо от их ``display_order``: визуально «скелет» в
    компактном превью только путает.
    """
    qs = _shop_queryset().filter(is_sold_out=False, is_placeholder=False)[:limit]
    return [p.as_cart_dict() for p in qs]


def get_free_products() -> list[dict[str, Any]]:
    """Опубликованные бесплатные модели в словарной форме."""
    return [p.as_cart_dict() for p in _free_queryset()]


def get_product(product_id) -> dict[str, Any] | None:
    """Товар по ``id`` (любого ``kind``), либо ``None``.

    Оставлена та же сигнатура, что у прежней реализации — чтобы не
    переписывать ``cart_utils``, ``views.cart_api`` и тесты корзины.
    Возвращает словарь ``Product.as_cart_dict()``; для непубликованных
    или отсутствующих товаров — ``None``.
    """
    try:
        pid = int(product_id)
    except (TypeError, ValueError):
        return None
    product = Product.objects.filter(pk=pid, is_published=True).first()
    return product.as_cart_dict() if product else None


def get_product_instance(product_id) -> Product | None:
    """Как ``get_product``, но отдаёт модельный инстанс (для шаблонов)."""
    try:
        pid = int(product_id)
    except (TypeError, ValueError):
        return None
    return Product.objects.filter(pk=pid, is_published=True).first()
