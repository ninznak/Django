"""Обновить иллюстрации в обзорной статье о чеканке (16052026news*)."""

import importlib

from django.db import migrations


def update_images(apps, schema_editor):
    seed = importlib.import_module(
        "core.migrations.0017_seed_coin_minting_news_2025_2026"
    )
    NewsArticle = apps.get_model("core", "NewsArticle")
    NewsArticle.objects.filter(slug=seed.SLUG).update(
        content=seed.CONTENT,
        cover_image="images/news/16052026news0.png",
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_seed_coin_minting_news_2025_2026"),
    ]

    operations = [
        migrations.RunPython(update_images, noop),
    ]
