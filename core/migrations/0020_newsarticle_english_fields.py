from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0019_fix_coin_minting_news_duplicate_cover"),
    ]

    operations = [
        migrations.AddField(
            model_name="newsarticle",
            name="title_en",
            field=models.CharField(
                blank=True, default="", max_length=220, verbose_name="Title (EN)"
            ),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="excerpt_en",
            field=models.TextField(
                blank=True, default="", max_length=600, verbose_name="Excerpt (EN)"
            ),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="content_en",
            field=models.TextField(blank=True, default="", verbose_name="Body (EN)"),
        ),
        migrations.AddField(
            model_name="newsarticle",
            name="tag_en",
            field=models.CharField(
                blank=True, default="", max_length=80, verbose_name="Category (EN)"
            ),
        ),
    ]
