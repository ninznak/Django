"""Shop catalog.

Порядок элементов ``SHOP_PRODUCTS`` определяет порядок карточек на странице
``/shop/``. Превью на главной (``SHOP_PREVIEW_PRODUCTS``) формируется явной
фильтрацией по ``not_for_sale`` — это гарантирует, что превью всегда показывает
только доступные к покупке товары, даже если в каталоге ``not_for_sale``-позиции
перемешаны с продаваемыми.

``price_cents`` держим положительным даже для "Нет в продаже", чтобы не ломать
``test_every_product_has_required_fields`` — доступность покупки решает флаг
``not_for_sale`` в UI (``shop.html`` / ``homepage.html``) и в ``cart_utils``.

Идентификаторы (``id``) у существующих товаров стабильны — их используют
корзина, заказы в БД и тесты. Новым товарам выдаются следующие свободные ``id``.
"""

from __future__ import annotations

from .pricing import rub_whole_to_kopecks


def _product(rub_price: int, **kwargs) -> dict:
    price, price_cents = rub_whole_to_kopecks(rub_price)
    return {"price": price, "price_cents": price_cents, **kwargs}


SHOP_PRODUCTS: list[dict] = [
    _product(
        3800,
        id=8,
        title="Медаль Толстова «Переход за Рейн»",
        type_i18="shop_3d_model",
        img="images/shop/tolst.png",
        alt="3D-модель: Медаль Толстова «Переход за Рейн»",
        badge=None,
        description="Трёхмерный файл отсканированной медали.",
    ),
    _product(
        1600,
        id=12,
        title="Отсканированный бюст Давид Микеланджело",
        type_i18="shop_3d_model",
        img="images/news/david.jpg",
        alt="3D-модель: отсканированный бюст Давид Микеланджело",
        badge=None,
        description="Трёхмерный файл отсканированного бюста.",
    ),
    _product(
        1300,
        id=13,
        title="Чумной доктор",
        type_i18="shop_3d_model",
        img="images/news/plague.jpg",
        alt="3D-модель: Чумной доктор",
        badge=None,
        description="3D-модель для печати.",
    ),
    _product(
        1300,
        id=14,
        title="Давид Донателло",
        type_i18="shop_3d_model",
        img="images/news/DavidDonatello.jpg",
        alt="3D-модель: Давид Донателло",
        badge=None,
        description="Трёхмерная модель для печати.",
    ),
    _product(
        1800,
        id=9,
        title="Скан стороны медали «Игры новых развивающихся сил»",
        type_i18="shop_3d_model",
        img="images/shop/emerging.png",
        alt="3D-модель: скан стороны медали «Игры новых развивающихся сил»",
        badge=None,
        description="Трёхмерный файл отсканированной медали.",
    ),
    _product(
        2300,
        id=10,
        title="Модель академика Ю. Орлова (сканирование)",
        type_i18="shop_3d_model",
        img="images/shop/Orlov.png",
        alt="3D-модель: портрет академика Ю. Орлова (сканирование)",
        badge=None,
        description="Трёхмерный файл отсканированной модели.",
    ),
    _product(
        4500,
        id=4,
        title="Урал — автомобиль геологоразведки",
        type_i18="shop_3d_model",
        img="images/shop/ural.JPEG",
        alt="3D-модель автомобиля Урал геологоразведки",
        badge=None,
        description="Состоит из разделяющихся частей.",
    ),
    _product(
        1000,
        id=11,
        title="Барельеф — герб Адыгеи",
        type_i18="shop_3d_model",
        img="images/shop/adygeya.png",
        alt="3D-модель: барельеф герба Республики Адыгея",
        badge=None,
        description="Трёхмерный барельеф, готовый к печати.",
    ),
    # ── Not for sale ──────────────────────────────────────────────────────
    # price_cents is preserved only so data-integrity tests pass; the UI and
    # cart gate purchase via the ``not_for_sale`` flag, never via price.
    _product(
        5000,
        id=5,
        title="Леди Диметреску",
        type_i18="shop_3d_model",
        img="images/shop/Dimetresku.png",
        alt="3D-модель: Леди Диметреску из Resident Evil Village",
        badge=None,
        description="Модель по мотивам игры Resident Evil Village.",
        not_for_sale=True,
    ),
    _product(
        4000,
        id=6,
        title="Червяк Джимм",
        type_i18="shop_3d_model",
        img="images/shop/EarthWormJim.png",
        alt="3D-модель: Червяк Джимм",
        badge=None,
        description="Модель для печати, возможно разделение по частям.",
        not_for_sale=True,
    ),
    _product(
        2300,
        id=2,
        title="Малыш Марио в горшочке",
        type_i18="shop_3d_model",
        img="images/shop/mario.JPEG",
        alt="3D-модель: фигурка ребёнок Марио в горшочке",
        badge=None,
        description="Трёхмерная модель для печати.",
    ),
    _product(
        3600,
        id=3,
        title="Фигурка из игры Neverhood",
        type_i18="shop_3d_model",
        img="images/shop/shop1.png",
        alt="3D-модель: фигурка из игры Neverhood",
        badge=None,
        description="Фигурка для печати.",
    ),
    _product(
        3300,
        id=1,
        title="Боевая Жаба",
        type_i18="shop_3d_model",
        img="images/shop/battletoad.png",
        alt="3D-модель Боевая Жаба",
        badge=None,
        description="Трёхмерная модель, готовая для печати.",
    ),
    _product(
        4500,
        id=7,
        title="Робот-сгибальщик Бендер",
        type_i18="shop_3d_model",
        img="images/shop/Bender.png",
        alt="3D-модель: Робот-сгибальщик Бендер",
        badge=None,
        description="Коллекционная 3D-модель.",
        not_for_sale=True,
    ),
]

# Превью на главной — только товары, доступные к покупке; первые 4 в порядке
# каталога. Явная фильтрация делает превью устойчивым к перестановкам.
SHOP_PREVIEW_PRODUCTS = [p for p in SHOP_PRODUCTS if not p.get("not_for_sale")][:4]

_BY_ID = {p["id"]: p for p in SHOP_PRODUCTS}


def get_product(product_id: int) -> dict | None:
    return _BY_ID.get(int(product_id))
