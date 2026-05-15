from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_seed_placeholder_products"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="file_size",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Подпись на карточке, например «12.4 MB» или «45 МБ».",
                max_length=40,
                verbose_name="Размер файла",
            ),
        ),
        migrations.CreateModel(
            name="SiteSetting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sculptor_busy",
                    models.PositiveSmallIntegerField(
                        default=50,
                        help_text="0–24 свободен, 25–49 открыт, 50–74 частично занят, 75–100 занят.",
                        verbose_name="Загруженность автора, %",
                    ),
                ),
                (
                    "stat_3d_value",
                    models.CharField(
                        default="200+",
                        max_length=32,
                        verbose_name="Счётчик: 3D модели",
                    ),
                ),
                (
                    "stat_projects_value",
                    models.CharField(
                        default="50+",
                        max_length=32,
                        verbose_name="Счётчик: проекты",
                    ),
                ),
                (
                    "stat_years_value",
                    models.CharField(
                        default="12",
                        max_length=32,
                        verbose_name="Счётчик: лет опыта",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "настройки сайта",
                "verbose_name_plural": "настройки сайта",
            },
        ),
    ]
