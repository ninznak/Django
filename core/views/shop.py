import json

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_http_methods

from .. import cart_utils
from ..models import Product
from ..seo import get_seo
from ..shop_data import get_product, get_shop_products
from ..view_utils import (
    CART_API_POST_LIMIT,
    CART_API_WINDOW_SECONDS,
    is_rate_limited,
)

_SHOP_ROW_LCM = 6
SHOP_PAGE_SIZE = 2 * _SHOP_ROW_LCM


def shop(request):
    products = get_shop_products()
    hide_sold = request.GET.get("hide_sold") in ("1", "true", "yes")
    q = (request.GET.get("q") or "").strip().lower()
    if hide_sold:
        products = [p for p in products if not p.get("is_sold_out")]
    if q:
        products = [
            p
            for p in products
            if q in (p.get("title") or "").lower()
            or q in (p.get("description") or "").lower()
            or q in (p.get("type_label") or "").lower()
        ]
    paginator = Paginator(products, SHOP_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    breadcrumbs = [
        {"label": "Главная", "url_name": "core:homepage"},
        {"label": "Магазин", "current": True},
    ]
    return render(
        request,
        "core/shop.html",
        {
            "shop_products": page_obj.object_list,
            "shop_page_obj": page_obj,
            "shop_hide_sold": hide_sold,
            "shop_query": q,
            "breadcrumbs": breadcrumbs,
            "seo": get_seo(
                request,
                breadcrumbs=breadcrumbs,
                webpage_type="CollectionPage",
            ),
        },
    )


def free_models(request):
    products = list(
        Product.objects.filter(kind=Product.Kind.FREE, is_published=True)
        .order_by("display_order", "id")
        .prefetch_related("extra_images")
    )
    tabs = [
        {"key": key, "label": label, "products": []}
        for key, label in Product.FreeCategory.choices
    ]
    by_key = {tab["key"]: tab for tab in tabs}
    for product in products:
        bucket = by_key.get(product.free_category)
        if bucket is not None:
            bucket["products"].append(product)
    breadcrumbs = [
        {"label": "Главная", "url_name": "core:homepage"},
        {"label": "Бесплатные модели", "current": True},
    ]
    return render(
        request,
        "core/free_models.html",
        {
            "free_tabs": tabs,
            "breadcrumbs": breadcrumbs,
            "seo": get_seo(
                request,
                breadcrumbs=breadcrumbs,
                webpage_type="CollectionPage",
            ),
        },
    )


def _serialize_cart_line(line):
    p = line["product"]
    return {
        "product": {
            "id": p["id"],
            "title": p["title"],
            "price": p["price"],
            "priceCents": p["price_cents"],
            "img": static(p["img"]),
            "alt": p["alt"],
        },
        "qty": line["qty"],
    }


def _cart_json(request):
    summary = cart_utils.get_cart_summary(request)
    return {
        "ok": True,
        "lines": [_serialize_cart_line(line) for line in summary["cart_lines"]],
        "totalItems": summary["cart_total_items"],
        "subtotalCents": summary["cart_subtotal_cents"],
    }


@require_http_methods(["GET", "POST"])
def cart_api(request):
    if request.method == "GET":
        return JsonResponse(_cart_json(request))

    if is_rate_limited(
        request, "cart_api_post", CART_API_POST_LIMIT, CART_API_WINDOW_SECONDS
    ):
        return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)

    try:
        data = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    action = data.get("action")
    raw_pid = data.get("product_id")
    raw_qty = data.get("qty", 1)

    if action == "add":
        try:
            pid = int(raw_pid)
            qty = int(raw_qty) if raw_qty is not None else 1
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_id"}, status=400)
        if not get_product(pid):
            return JsonResponse({"ok": False, "error": "unknown_product"}, status=400)
        cart_utils.add_item(request.session, pid, max(1, qty))
    elif action == "set":
        try:
            pid = int(raw_pid)
            qty = int(raw_qty)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_params"}, status=400)
        cart_utils.set_qty(request.session, pid, qty)
    elif action == "remove":
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_id"}, status=400)
        cart_utils.remove_item(request.session, pid)
    elif action == "clear":
        cart_utils.clear_cart(request.session)
    else:
        return JsonResponse({"ok": False, "error": "unknown_action"}, status=400)

    return JsonResponse(_cart_json(request))
