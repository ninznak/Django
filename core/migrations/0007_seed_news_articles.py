from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def seed_news_articles(apps, schema_editor):
    NewsArticle = apps.get_model("core", "NewsArticle")
    now = timezone.now()
    rows = [
        {
            "title": "3D-моделирование: путь от базовых форм к коммерческому уровню",
            "slug": "bas-relief-depth-achieving-sub-millimeter-precision-in-zbrush",
            "excerpt": "О последовательной работе с формой, деталями и технической подготовкой модели под реальный продакшн.",
            "content": (
                "Сильная 3D-модель начинается с формы и пропорций, а не с микродеталей.\n\n"
                "Рабочий порядок остается неизменным: крупные массы, затем средние формы, и только после этого финальная детализация.\n\n"
                "Коммерческий результат дает дисциплина пайплайна: проверка топологии, UV, масштаба и чистоты сцены перед сдачей."
            ),
            "tag": "Практика",
            "reading_time_minutes": 10,
            "cover_image": "images/news/model11.JPEG",
            "published_at": now - timedelta(days=8),
        },
        {
            "title": "Ключевые тренды 3D-графики в 2026 году",
            "slug": "midjourney-v7-for-numismatic-concept-art",
            "excerpt": "Что важно в 2026: PBR-реализм, модульные сцены и гибридный workflow с AI.",
            "content": (
                "Рынок 3D стал прикладным: ценятся не только красивые кадры, но и быстрое производство вариаций.\n\n"
                "На первый план выходят библиотеки ассетов, стандартизированный свет и предсказуемый pipeline от брифа до публикации.\n\n"
                "AI ускоряет поиск направления, но финальное качество по-прежнему определяет чистая 3D-база."
            ),
            "tag": "Тренды",
            "reading_time_minutes": 9,
            "cover_image": "images/news/midjourney-1920x1200.png",
            "published_at": now - timedelta(days=10),
        },
        {
            "title": "Технологии генеративного дизайна изделий",
            "slug": "generative-design-technologies",
            "excerpt": "Как генеративные алгоритмы меняют проектирование, оптимизацию и производство изделий.",
            "content": (
                "Генеративный дизайн позволяет задавать требования и получать множество вариантов формы под ограничения производства.\n\n"
                "Связка параметрического моделирования, оптимизации и аддитивных технологий дает выигрыш в скорости и экономике.\n\n"
                "Человек сохраняет ключевую роль: постановка задачи, оценка результата и финальный художественный контроль."
            ),
            "tag": "Технологии",
            "reading_time_minutes": 14,
            "cover_image": "images/news/gener1.jpg",
            "published_at": now - timedelta(days=12),
        },
        {
            "title": "ZBrush-скульптинг: как добиться выразительной формы и чистой детализации",
            "slug": "sora-and-kling-ai-video-for-3d-presentations",
            "excerpt": "Практика скульптинга: от крупной пластики к финальной детализации без визуального шума.",
            "content": (
                "Качество скульпта определяет порядок работы: силуэт и крупные массы, затем средние формы и только потом микродеталь.\n\n"
                "Такой подход ускоряет согласования и снижает стоимость правок на поздних этапах.\n\n"
                "Перед экспортом нужно закрепить техническую часть: ретопология, проверка сетки и подготовка к целевому пайплайну."
            ),
            "tag": "Скульптинг",
            "reading_time_minutes": 11,
            "cover_image": "images/news/ai-video-1920x1200.png",
            "published_at": now - timedelta(days=14),
        },
        {
            "title": "ArtCAM: возможности программы, ключевые задачи и практический workflow",
            "slug": "artcam-vozmozhnosti-zadachi-i-praktika",
            "excerpt": "Зачем ArtCAM в художественном CAD/CAM и как выстроить путь от эскиза до G-кода.",
            "content": (
                "ArtCAM помогает быстро переводить художественный рельеф в технологичный маршрут для ЧПУ.\n\n"
                "Сильная сторона подхода - единый workflow от векторной подготовки до траекторий обработки.\n\n"
                "Для стабильного результата важно учитывать материал, инструмент, шаг по Z и финишные стратегии."
            ),
            "tag": "CAD/CAM",
            "reading_time_minutes": 12,
            "cover_image": "images/news/artcam1.png",
            "published_at": now - timedelta(days=7),
        },
    ]

    for row in rows:
        NewsArticle.objects.update_or_create(
            slug=row["slug"],
            defaults={
                **row,
                "status": "published",
            },
        )


def unseed_news_articles(apps, schema_editor):
    NewsArticle = apps.get_model("core", "NewsArticle")
    NewsArticle.objects.filter(
        slug__in=[
            "bas-relief-depth-achieving-sub-millimeter-precision-in-zbrush",
            "midjourney-v7-for-numismatic-concept-art",
            "generative-design-technologies",
            "sora-and-kling-ai-video-for-3d-presentations",
            "artcam-vozmozhnosti-zadachi-i-praktika",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_newsarticle"),
    ]

    operations = [
        migrations.RunPython(seed_news_articles, unseed_news_articles),
    ]
