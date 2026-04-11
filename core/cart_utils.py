"""Session cart — quantities per product ID."""

from __future__ import annotations

from typing import Any

from .shop_data import get_product

CART_SESSION_KEY = "creativesphere_cart_v1"


def _quantities(session) -> dict[str, int]:
    raw = session.get(CART_SESSION_KEY)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            q = int(v)
        except (TypeError, ValueError):
            continue
        if q > 0:
            out[str(k)] = q
    return out


def _save(session, q: dict[str, int]) -> None:
    session[CART_SESSION_KEY] = q
    session.modified = True


def add_item(session, product_id: int, qty: int = 1) -> None:
    if not get_product(product_id):
        return
    q = _quantities(session)
    key = str(int(product_id))
    current = int(q.get(key, 0))
    new_qty = max(0, current + int(qty))
    if new_qty == 0:
        q.pop(key, None)
    else:
        q[key] = new_qty
    _save(session, q)


def set_qty(session, product_id: int, qty: int) -> None:
    if not get_product(product_id):
        return
    q = _quantities(session)
    key = str(int(product_id))
    if qty < 1:
        q.pop(key, None)
    else:
        q[key] = int(qty)
    _save(session, q)


def remove_item(session, product_id: int) -> None:
    q = _quantities(session)
    key = str(int(product_id))
    q.pop(key, None)
    _save(session, q)


def clear_cart(session) -> None:
    session[CART_SESSION_KEY] = {}
    session.modified = True


def build_lines(session) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for pid_str, qty in _quantities(session).items():
        pid = int(pid_str)
        product = get_product(pid)
        if product and qty > 0:
            lines.append({"product": product, "qty": qty})
    lines.sort(key=lambda x: x["product"]["id"])
    return lines


def get_cart_summary(request) -> dict[str, Any]:
    lines = build_lines(request.session)
    total_items = sum(line["qty"] for line in lines)
    subtotal = sum(line["product"]["price_cents"] * line["qty"] for line in lines)
    return {
        "cart_lines": lines,
        "cart_total_items": total_items,
        "cart_subtotal_cents": subtotal,
    }


def catalog_for_api() -> list[dict[str, Any]]:
    """Minimal product list for clients (IDs and titles)."""
    from .shop_data import SHOP_PRODUCTS
    return [{"id": p["id"], "title": p["title"]} for p in SHOP_PRODUCTS]
