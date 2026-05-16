"""Одна обзорная статья: новинки технологий чеканки 2025–2026 (idempotent seed)."""

from datetime import timedelta

from django.db import migrations
from django.utils import timezone
SLUG = "novinki-tekhnologii-chekanke-monet-2025-2026"

CONTENT = """За 2025 и начало 2026 года крупнейшие монетные дворы мира показали, что современная чеканка — это уже не только пресс и штемпель, а связка лазерной гравировки, микрорельефа, новых сплавов и цифровой аутентификации. Ниже — сводка главных направлений, которые стоит учитывать художнику медали и 3D-скульптору.

![Чеканка — иллюстрация 2](images/news/16052026news.png)

## Лазерная гравировка штемпелей

**Монетный двор США** в 2025 году выпустил первую серебряную «Американскую орловую» с лазерным privy mark — стилизованным «солнечным лучом» на аверсе. Ранее лазеры применялись для серийных номеров на оправках штемпелей и матирования proof-поверхностей; теперь **мастер-штемпель целиком создаётся лазерной гравировкой**, что даёт более чёткую передачу мелких элементов: перьев, складок ткани, букв.

Для художника это означает: макет должен содержать **реально воспроизводимую микрогеометрию** — лазер не «спасёт» размытый рельеф, но награждает чистые формы.

## Микротекст и «визуальная безопасность»

**Королевский монетный двор Великобритании** продолжает развивать серию Britannia как эталон защиты инвестиционной монеты. В обновлённых версиях используются:

- **микротекст** DECUS ET TUTAMEN по контуру рельефа;
- **пикосекундные лазеры** — следы шириной до долей микрона (сотни раз тоньше человеческого волоса);
- **латентное изображение** (замок / трезубец при наклоне);
- **surface animation** — иллюзия «живой» поверхности при повороте монеты.

Те же приёмы перенесены на **золотые слитки** Britannia: аутентичность проверяется визуально, без специальных приборов.

![Чеканка — иллюстрация 3](images/news/16052026news2.png)

## Smartminting® 4.0: рельеф до 9 мм

Компания **CIT / B.H. Mayer's** представила **Smartminting® 4.0** (2024–2025): ультравысокий рельеф порядка **9 mm** при сохранении proof-качества полей — на ~50% выше предыдущего поколения технологии. Пример — серебряная монета **Iron Knight** (Острова Кука): рыцарь с объёмной бронёй, элементы «выходят» к гурту.

Для барельефа и медалей это важный ориентир: **контраст высот** и читаемость силуэта снова в моде; плоские «пластинки» на премиальном рынке уступают скульптурным решениям.

## Ниобий, анодирование и цифровой двойник

**Австрийский монетный двор** развивает серию **серебро + ниобий** (с 2003 года). Ниобиевое ядро окрашивается **анодным окислением** — цвет держится в объёме металла, а не в краске.

- **2024 — «Edaphon»**: почва как экосистема, организмы в серебряном кольце и цветном ниобии.
- **2025 — «Digitalisation»**: аналоговые и цифровые пары объектов, мотив микросхемы и AI; впервые в лимитированном наборе — **цифровой двойник монеты** (блокчейн / crypto stamp).

Ниобий остаётся редким материалом в чеканке: низкая плотность, яркие интерференционные цвета, отдельный технологический цикл после серебряного кольца.

## Высокий рельеф и реверс-proof

**National Park Foundation** (США) и партнёры выпускают серебряные медали **Saint-Gaudens Winged Liberty** в высоком рельефе с **reverse proof** — зеркальные элементы и матовые поля меняются местами относительно классики. **Royal Canadian Mint** в серии Aztec Empire сочетает ultra-high relief с **селективным золочением**.

Тренд: **двусторонний объём** и комбинированные финиши (proof + high relief + plating) в одном тираже.

![Чеканка — иллюстрация 4](images/news/16052026news3.png)

## Что это даёт практике медальера

1. **Проектирование под инструмент** — лазер и микрорельеф требуют чистых CAD/CAM-данных без артефактов сетки.
2. **Безопасность как часть дизайна** — микротекст, гурт с вариацией, latent-элементы закладываются на этапе макета.
3. **Материал ≠ декор** — ниобий, биметалл, селективное покрытие диктуют отдельные операции; художник согласует композицию с технологом.
4. **Высота рельефа** — Smartminting и высокорельефные прессы снова расширяют допустимый Z-дiapason; стоит тестировать глубину на восковой/цифровой модели до стали.

## Источники и материалы для углубления

- [US Mint — laser-engraved Silver Eagle 2025](https://www.usmint.gov/2025-laser-engraved-american-eagle-one-ounce-silver-proof-coin-25EALE.html)
- [Coin World — laser engraving on American Eagle](https://www.coinworld.com/news/us-coins/new-technology-brings-laser-engraving-on-american-eagle)
- [Royal Mint — visually secure Britannia](https://www.royalmint.com/aboutus/press-centre/the-royal-mint-unveil-the-worlds-most-visually-secure-bullion-coin/)
- [CoinsWeekly — Smartminting® 4.0 Iron Knight](https://new.coinsweekly.com/people-and-markets/cits-new-smartminting-4-0-iron-knight/)
- [Austrian Mint — niobium Digitalisation 2025](https://www.muenzeoesterreich.at/eng/collect/good-to-know/silver-niobium-coins)
- [Coin World — Austria niobium «soil» 2024](https://www.coinworld.com/news/world-coins/austria-s-annual-niobium-issue-celebrates-soil)

*Обзор подготовлен по открытым публикациям монетных дворов и отраслевых изданий.*
"""


def seed_article(apps, schema_editor):
    NewsArticle = apps.get_model("core", "NewsArticle")
    now = timezone.now()
    NewsArticle.objects.update_or_create(
        slug=SLUG,
        defaults={
            "title": "Новинки технологий чеканки монет: обзор 2025–2026",
            "excerpt": (
                "Лазерные штемпели, микротекст Britannia, Smartminting® 4.0, "
                "ниобий Австрии и цифровые двойники — сводка мировых трендов "
                "для художников медали и 3D-скульпторов."
            ),
            "content": CONTENT,
            "tag": "Монеты",
            "reading_time_minutes": 12,
            "cover_image": "images/news/16052026news0.png",
            "status": "published",
            "published_at": now - timedelta(days=2),
        },
    )


def unseed_article(apps, schema_editor):
    NewsArticle = apps.get_model("core", "NewsArticle")
    NewsArticle.objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_sitesetting_product_file_size"),
    ]

    operations = [
        migrations.RunPython(seed_article, unseed_article),
    ]
