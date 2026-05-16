"""Убрать дубль news0 в теле статьи (обложка уже показывает news0)."""

import importlib

from django.db import migrations


def fix_duplicate(apps, schema_editor):
    seed = importlib.import_module(
        "core.migrations.0017_seed_coin_minting_news_2025_2026"
    )
    NewsArticle = apps.get_model("core", "NewsArticle")
    NewsArticle.objects.filter(slug=seed.SLUG).update(content=seed.CONTENT)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0018_update_coin_minting_news_images"),
    ]

    operations = [
        migrations.RunPython(fix_duplicate, noop),
    ]
