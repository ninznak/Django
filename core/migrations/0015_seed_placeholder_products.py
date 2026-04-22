"""Посев 2 placeholder-карточек в каждый таб бесплатных моделей.

Идея — визуально проверить, как смотрится `Product.is_placeholder` в
роли бывших хардкодных «Скоро новая модель». Миграция полностью
совместима с логикой `0012_seed_products`:

* id-коридор для placeholder'ов — 201..299 (магазинные id 1..14,
  бесплатные модели 101+, остаётся запас). Админские продукты получат
  id > 299 благодаря setval в 0012.
* `get_or_create(pk=…)` → повторный прогон не перезапишет правки
  редактора; если он удалил карточку в админке и запустил мигратор,
  она снова появится (это ожидаемое поведение seed-миграций).
* Картинка — `images/shop/empty.JPEG`, уже лежит в репозитории. Нужна
  только для того, чтобы placeholder-карточка имела валидный alt/image
  даже если редактор потом снимет `is_placeholder` — не придётся
  дозаполнять вручную.
* Обратная миграция — удаляет только посеянные id, не трогает чужие.
"""

from django.db import migrations


PLACEHOLDER_IMAGE = "images/shop/empty.JPEG"


# По два placeholder'а в таб. id фиксированные, чтобы повторный
# прогон не клонировал записи. Порядок: art, hobby, tech — совпадает
# с `Product.FreeCategory.choices` после 0014_reorder_free_categories.
PLACEHOLDER_SEED = [
    # Художественные модели
    dict(id=201, free_category="art",   slug="ph-art-1",   title="Скоро новая модель",        description="Место для будущего фото"),
    dict(id=202, free_category="art",   slug="ph-art-2",   title="Скоро новая модель",        description="Место для будущего фото"),
    # Хоббийные модели
    dict(id=203, free_category="hobby", slug="ph-hobby-1", title="Скоро новая модель",        description="Место для будущего фото"),
    dict(id=204, free_category="hobby", slug="ph-hobby-2", title="Скоро новая модель",        description="Место для будущего фото"),
    # Технические модели
    dict(id=205, free_category="tech",  slug="ph-tech-1",  title="Скоро новая модель",        description="Место для будущего фото"),
    dict(id=206, free_category="tech",  slug="ph-tech-2",  title="Скоро новая модель",        description="Место для будущего фото"),
]


def seed_placeholders(apps, schema_editor):
    Product = apps.get_model("core", "Product")

    for order_idx, entry in enumerate(PLACEHOLDER_SEED):
        defaults = {
            "kind": "free",
            "file_type": "3d",
            "free_category": entry["free_category"],
            "slug": entry["slug"],
            "title": entry["title"],
            "description": entry["description"],
            "badge": "",
            "image": PLACEHOLDER_IMAGE,
            "alt": "Пустая карточка-заглушка",
            "price_rub": 0,
            "download_url": "",
            "is_published": True,
            "is_sold_out": False,
            "is_placeholder": True,
            # display_order побольше, чтобы placeholder'ы шли ПОСЛЕ реальных
            # товаров в каждом табе (реальные имеют display_order 0..2).
            "display_order": 100 + order_idx,
        }
        Product.objects.get_or_create(pk=entry["id"], defaults=defaults)

    # Двигаем sequence, чтобы следующие admin-продукты получили id > 299.
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setval("
                "pg_get_serial_sequence('core_product', 'id'), "
                "COALESCE((SELECT MAX(id) FROM core_product), 1), "
                "true)"
            )


def unseed_placeholders(apps, schema_editor):
    Product = apps.get_model("core", "Product")
    Product.objects.filter(pk__in=[e["id"] for e in PLACEHOLDER_SEED]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_reorder_free_categories"),
    ]

    operations = [
        migrations.RunPython(seed_placeholders, reverse_code=unseed_placeholders),
    ]
