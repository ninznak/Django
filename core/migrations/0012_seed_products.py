"""Посев товаров магазина (id=1..14) и бесплатных моделей в БД.

Идемпотентная и безопасная для продакшена миграция:

* Использует ``get_or_create`` по ``pk`` — если админ уже создал товар
  с таким id, миграция не перезаписывает его поля.
* Для каждого товара дополнительные ракурсы (``ProductImage``) добавляются
  только если у товара ещё нет ни одного доп. ракурса, чтобы не клонировать
  их при повторных прогонах.
* ``id`` товаров магазина совпадают со старыми ``SHOP_PRODUCTS[*]['id']``,
  чтобы старые ``OrderItem.product_id`` и ключи сессий корзины продолжали
  ссылаться на существующие товары.
* В конце выставляем значение Postgres-последовательности так, чтобы
  следующий admin-товар получил ``id > max(id)``.
"""

from django.db import migrations


# ── Данные товаров магазина ──────────────────────────────────────────────
# Порядок в списке = display_order (0,1,2,…), это же определяет порядок
# карточек на странице /shop/.
SHOP_SEED = [
    dict(id=8,  title="Медаль Толстова «Переход за Рейн»",                 price_rub=3800, image="images/shop/tolst.png",       alt="3D-модель: Медаль Толстова «Переход за Рейн»",        description="Трёхмерный файл отсканированной медали."),
    dict(id=12, title="Отсканированный бюст Давид Микеланджело",           price_rub=1600, image="images/news/david.jpg",       alt="3D-модель: отсканированный бюст Давид Микеланджело",  description="Трёхмерный файл отсканированного бюста."),
    dict(id=13, title="Чумной доктор",                                     price_rub=1300, image="images/news/plague.jpg",      alt="3D-модель: Чумной доктор",                             description="3D-модель для печати."),
    dict(id=14, title="Давид Донателло",                                   price_rub=1300, image="images/news/DavidDonatello.jpg", alt="3D-модель: Давид Донателло",                        description="Трёхмерная модель для печати."),
    dict(id=9,  title="Скан стороны медали «Игры новых развивающихся сил»", price_rub=1800, image="images/shop/emerging.png",   alt="3D-модель: скан стороны медали «Игры новых развивающихся сил»", description="Трёхмерный файл отсканированной медали."),
    dict(id=10, title="Модель академика Ю. Орлова (сканирование)",          price_rub=2300, image="images/shop/Orlov.png",       alt="3D-модель: портрет академика Ю. Орлова (сканирование)", description="Трёхмерный файл отсканированной модели."),
    dict(id=4,  title="Урал — автомобиль геологоразведки",                  price_rub=4500, image="images/shop/ural.JPEG",       alt="3D-модель автомобиля Урал геологоразведки",            description="Состоит из разделяющихся частей."),
    dict(id=11, title="Барельеф — герб Адыгеи",                             price_rub=1000, image="images/shop/adygeya.png",     alt="3D-модель: барельеф герба Республики Адыгея",          description="Трёхмерный барельеф, готовый к печати."),
    # ── Не для продажи (is_sold_out=True) ───────────────────────────────
    dict(id=5,  title="Леди Диметреску",                                    price_rub=5000, image="images/shop/Dimetresku.png",  alt="3D-модель: Леди Диметреску из Resident Evil Village",  description="Модель по мотивам игры Resident Evil Village.", is_sold_out=True),
    dict(id=6,  title="Червяк Джимм",                                       price_rub=4000, image="images/shop/EarthWormJim.png", alt="3D-модель: Червяк Джимм",                              description="Модель для печати, возможно разделение по частям.", is_sold_out=True),
    dict(id=2,  title="Малыш Марио в горшочке",                             price_rub=2300, image="images/shop/mario.JPEG",      alt="3D-модель: фигурка ребёнок Марио в горшочке",         description="Трёхмерная модель для печати."),
    dict(id=3,  title="Фигурка из игры Neverhood",                          price_rub=3600, image="images/shop/shop1.png",       alt="3D-модель: фигурка из игры Neverhood",                description="Фигурка для печати."),
    dict(id=1,  title="Боевая Жаба",                                        price_rub=3300, image="images/shop/battletoad.png",  alt="3D-модель Боевая Жаба",                                description="Трёхмерная модель, готовая для печати."),
    dict(id=7,  title="Робот-сгибальщик Бендер",                            price_rub=4500, image="images/shop/Bender.png",      alt="3D-модель: Робот-сгибальщик Бендер",                   description="Коллекционная 3D-модель.", is_sold_out=True),
]


# ── Данные бесплатных моделей (таб «Хоббийные модели») ───────────────────
# ``id`` начинаются со 101, чтобы заведомо не пересечься с будущими товарами
# магазина и с существующими ``OrderItem.product_id`` из продакшена.
FREE_SEED = [
    dict(
        id=101,
        slug="jalapeno-free-3d",
        title="Халапеньо (Jalapeno)",
        image="images/shop/free/peper1.png",
        alt="Бесплатная 3D-модель халапеньо, первый ракурс",
        description="Формат STL. Бесплатная модель для 3D-печати и тестовых распечаток.",
        download_url="https://disk.yandex.ru/d/FeBhoKfzXHrlxQ",
        extras=[
            ("images/shop/free/peper2.png", "Бесплатная 3D-модель халапеньо, второй ракурс"),
        ],
    ),
    dict(
        id=102,
        slug="kabbage-free-3d",
        title="Злой кабачок",
        image="images/shop/free/kabbage2.png",
        alt="Бесплатная 3D-модель, основной ракурс",
        description="Формат OBJ. Бесплатная загрузка для личных тестов и ознакомления.",
        download_url="https://disk.yandex.ru/d/BNZ0tmLTBh0kyA",
        extras=[
            ("images/shop/free/kabbage1.png", "Бесплатная 3D-модель, альтернативный ракурс"),
        ],
    ),
    dict(
        id=103,
        slug="peashooter-ice-free-3d",
        title="Горохострел Ледяной",
        image="images/shop/free/goroh1.png",
        alt="Бесплатная 3D-модель горохострела, первый ракурс",
        description="Модель состоит из 2 отдельных частей, поддержек при печати FDM не требует.",
        download_url="https://disk.yandex.ru/d/24zTNbjkJiWb_g",
        extras=[
            ("images/shop/free/goroh2.png", "Бесплатная 3D-модель горохострела, второй ракурс"),
        ],
    ),
]


def _slug_for_shop(entry: dict) -> str:
    """Стабильный slug для товаров магазина (id уже уникален)."""
    return f"shop-item-{entry['id']}"


def seed_products(apps, schema_editor):
    Product = apps.get_model("core", "Product")
    ProductImage = apps.get_model("core", "ProductImage")

    # Магазин
    for order_idx, entry in enumerate(SHOP_SEED):
        defaults = {
            "kind": "shop",
            "file_type": "3d",
            "free_category": "",
            "slug": _slug_for_shop(entry),
            "title": entry["title"],
            "description": entry.get("description", ""),
            "badge": "",
            "image": entry["image"],
            "alt": entry.get("alt", ""),
            "price_rub": entry["price_rub"],
            "download_url": "",
            "is_published": True,
            "is_sold_out": bool(entry.get("is_sold_out", False)),
            "display_order": order_idx,
        }
        Product.objects.get_or_create(pk=entry["id"], defaults=defaults)

    # Бесплатные модели — таб «Хоббийные»
    for order_idx, entry in enumerate(FREE_SEED):
        defaults = {
            "kind": "free",
            "file_type": "3d",
            "free_category": "hobby",
            "slug": entry["slug"],
            "title": entry["title"],
            "description": entry.get("description", ""),
            "badge": "",
            "image": entry["image"],
            "alt": entry.get("alt", ""),
            "price_rub": 0,
            "download_url": entry.get("download_url", ""),
            "is_published": True,
            "is_sold_out": False,
            "display_order": order_idx,
        }
        product, _ = Product.objects.get_or_create(pk=entry["id"], defaults=defaults)

        # Доп. ракурсы добавляем только если у товара их ещё нет — чтобы при
        # повторном прогоне миграции не дублировать их поверх админских правок.
        if not ProductImage.objects.filter(product=product).exists():
            for extra_idx, (path, alt) in enumerate(entry.get("extras", [])):
                ProductImage.objects.create(
                    product=product,
                    image=path,
                    alt=alt,
                    display_order=extra_idx,
                )

    # Обновляем Postgres-последовательность, чтобы следующий ``id`` из admin
    # не пересекался с посеянными. Для SQLite AUTOINCREMENT выставится сам
    # при первом INSERT без явного pk.
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval("
                "pg_get_serial_sequence('core_product', 'id'), "
                "COALESCE((SELECT MAX(id) FROM core_product), 1), "
                "true)"
            )


def unseed_products(apps, schema_editor):
    """Откат удаляет только посеянные id — чужие записи не трогаем."""
    Product = apps.get_model("core", "Product")
    seeded_ids = [e["id"] for e in SHOP_SEED] + [e["id"] for e in FREE_SEED]
    Product.objects.filter(pk__in=seeded_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_product_and_product_image"),
    ]

    operations = [
        migrations.RunPython(seed_products, reverse_code=unseed_products),
    ]
