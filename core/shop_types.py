"""Типизированный контракт словаря товара (``Product.as_cart_dict``)."""

from __future__ import annotations

from typing import TypedDict


class CartProduct(TypedDict):
    id: int
    title: str
    description: str
    img: str
    alt: str
    badge: str | None
    type_label: str
    price: str
    price_cents: int
    price_rub: int
    not_for_sale: bool
    is_sold_out: bool
    is_placeholder: bool
    is_free: bool
    download_url: str
    file_size: str
    slug: str


class CartLine(TypedDict):
    product: CartProduct
    qty: int
