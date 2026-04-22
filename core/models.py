from django.conf import settings
from django.db import models

from .pricing import format_minor_as_rub


class Order(models.Model):
    """Заказ в интернет-магазине (без регистрации пользователя)."""

    STATUS_CHOICES = [
        ("new", "Новый"),
        ("processing", "В обработке"),
        ("paid", "Оплачен"),
        ("shipped", "Отправлен"),
        ("completed", "Завершён"),
        ("cancelled", "Отменён"),
    ]

    # Контактные данные заказчика
    name = models.CharField("Имя", max_length=120)
    email = models.EmailField("Email")
    phone = models.CharField("Телефон", max_length=30, blank=True, default="")

    # Адрес доставки
    country = models.CharField("Страна", max_length=100, default="Россия")
    city = models.CharField("Город", max_length=100)
    address = models.TextField("Адрес доставки", max_length=500, blank=True, default="")
    postal_code = models.CharField("Индекс", max_length=20, blank=True, default="")

    # Статус и данные заказа
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="new")
    total_cents = models.PositiveIntegerField("Сумма заказа (копейки/центы)")
    notes = models.TextField("Комментарий к заказу", blank=True, default="", max_length=1000)

    # Согласие на обработку ПДн
    pd_consent = models.BooleanField("Согласие на обработку ПДн", default=False)
    pd_consent_date = models.DateTimeField("Дата согласия", auto_now_add=True)

    # Метаданные
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    ip_address = models.GenericIPAddressField("IP-адрес", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "заказ"
        verbose_name_plural = "заказы"

    def __str__(self) -> str:
        return f"Заказ №{self.id} от {self.name} ({self.email})"


class OrderItem(models.Model):
    """Позиция заказа (товар)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ")
    product_id = models.PositiveIntegerField("ID товара")
    product_name = models.CharField("Название товара", max_length=200)
    product_price_cents = models.PositiveIntegerField("Цена за единицу (копейки/центы)")
    quantity = models.PositiveIntegerField("Количество", default=1)

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказа"

    def __str__(self) -> str:
        return f"{self.product_name} × {self.quantity}"

    @property
    def total_cents(self) -> int:
        """Общая стоимость позиции."""
        return self.product_price_cents * self.quantity


class ContactSubmission(models.Model):
    """Contact form messages; listed in Django admin."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    email_sent = models.BooleanField(
        default=False,
        help_text="Whether the notification email was delivered (if enabled).",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "contact message"
        verbose_name_plural = "contact messages"

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} — {self.subject[:60]}"


class NewsArticle(models.Model):
    """News/blog article managed from Django admin."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"

    title = models.CharField("Заголовок", max_length=220)
    slug = models.SlugField("Slug", unique=True, max_length=220)
    excerpt = models.TextField("Краткое описание", max_length=600, blank=True, default="")
    content = models.TextField("Текст статьи")
    tag = models.CharField("Категория", max_length=80, blank=True, default="Статья")
    reading_time_minutes = models.PositiveSmallIntegerField("Время чтения (мин)", default=8)
    cover_image = models.CharField(
        "Обложка (путь в static/)",
        max_length=255,
        blank=True,
        default="",
        help_text="Например: images/news/model11.JPEG",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_articles",
        verbose_name="Автор",
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField("Дата публикации", blank=True, null=True, db_index=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "статья"
        verbose_name_plural = "статьи"

    def __str__(self) -> str:
        return self.title


class Product(models.Model):
    """Карточка товара: платные позиции магазина и бесплатные 3D/2D-модели.

    Одна таблица с дискриминатором ``kind``, чтобы `/shop/` и `/free_models/`
    обслуживались из одного места и админка была единообразной.

    Цена хранится целым числом в рублях (``price_rub``); минорные единицы
    (копейки) вычисляются лениво через ``price_cents`` — это сохраняет
    совместимость с существующей схемой ``Order.total_cents``.

    ``id`` существующих товаров магазина стабильны — их помнят ``OrderItem``
    и пользовательские сессии (корзина). Новым товарам админка выдаёт
    следующий свободный ``id``.
    """

    class Kind(models.TextChoices):
        SHOP = "shop", "Магазин (платный)"
        FREE = "free", "Бесплатная модель"

    class FileType(models.TextChoices):
        MODEL_3D = "3d", "3D модель"
        FILE_2D = "2d", "2D файл"
        OTHER = "other", "Другое"

    class FreeCategory(models.TextChoices):
        # Порядок здесь определяет порядок табов на /free_models/
        # (core.views.free_models строит tabs = [… for key, label in choices]).
        ART = "art", "Художественные модели"
        HOBBY = "hobby", "Хоббийные модели"
        TECH = "tech", "Технические модели"

    kind = models.CharField(
        "Тип карточки",
        max_length=10,
        choices=Kind.choices,
        default=Kind.SHOP,
        db_index=True,
    )
    file_type = models.CharField(
        "Тип файла",
        max_length=10,
        choices=FileType.choices,
        default=FileType.MODEL_3D,
    )
    free_category = models.CharField(
        "Таб (только для бесплатных)",
        max_length=10,
        choices=FreeCategory.choices,
        blank=True,
        default="",
        help_text="Определяет, в каком табе страницы /free_models/ показывать карточку.",
    )

    slug = models.SlugField("Slug", max_length=80, unique=True)
    title = models.CharField("Название", max_length=200)
    description = models.TextField(
        "Описание",
        blank=True,
        default="",
        help_text="Простой текст; переводы строки в шаблоне превращаются в <br>.",
    )
    badge = models.CharField(
        "Бейдж",
        max_length=80,
        blank=True,
        default="",
        help_text="Короткая метка на карточке (например, «NEW»). Пусто — без бейджа.",
    )

    image = models.CharField(
        "Главная картинка (путь в static/)",
        max_length=500,
        blank=True,
        default="",
        help_text="Например: images/shop/battletoad.png. Для placeholder-карточки можно оставить пустым.",
    )
    alt = models.CharField("Alt для главной картинки", max_length=200, blank=True, default="")

    price_rub = models.PositiveIntegerField(
        "Цена, ₽",
        default=0,
        help_text="Целое число в рублях. Для бесплатных — 0.",
    )
    download_url = models.CharField(
        "Ссылка на скачивание",
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Для бесплатных моделей: полный URL (https://…) или относительный "
            "путь в static/ (files/free/xxx.zip)."
        ),
    )

    is_published = models.BooleanField("Опубликовано", default=True, db_index=True)
    is_sold_out = models.BooleanField(
        "Распродано",
        default=False,
        help_text="Показывать метку «Нет в продаже» и блокировать кнопку купить/скачать.",
    )
    is_placeholder = models.BooleanField(
        "Placeholder «Скоро»",
        default=False,
        help_text=(
            "Рендерить пустую карточку «Скоро новая модель» вместо обычной. "
            "Можно не заполнять image / description / download_url. Карточка не "
            "попадает в корзину и превью на главной."
        ),
    )
    display_order = models.PositiveIntegerField(
        "Порядок",
        default=0,
        db_index=True,
        help_text="Меньшее число — карточка выше на странице.",
    )

    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "товар / бесплатная модель"
        verbose_name_plural = "товары и бесплатные модели"

    def __str__(self) -> str:
        return self.title

    @property
    def price_cents(self) -> int:
        """Цена в минорных единицах (копейках) для совместимости с Order/OrderItem."""
        return int(self.price_rub) * 100

    @property
    def price_display(self) -> str:
        """Готовая к выводу строка цены («3 800 ₽»)."""
        return format_minor_as_rub(self.price_cents)

    @property
    def is_purchasable(self) -> bool:
        """Можно ли сейчас положить товар в корзину / скачать бесплатно."""
        return self.is_published and not self.is_sold_out and not self.is_placeholder

    def all_image_paths(self) -> list[tuple[str, str]]:
        """Все картинки карточки в порядке показа: [(path, alt), …].

        Всегда возвращает минимум одну запись (главную картинку). Дополнительные
        берутся из ``extra_images`` и участвуют в switcher'е ракурсов.
        """
        out: list[tuple[str, str]] = [(self.image, self.alt or self.title)]
        for extra in self.extra_images.all():
            out.append((extra.image, extra.alt or self.title))
        return out

    def as_cart_dict(self) -> dict:
        """Словарная форма товара для корзины, JSON API и шаблонов.

        ``not_for_sale`` объединяет все причины, по которым товар нельзя
        положить в корзину: и «Распродано», и placeholder-карточка «Скоро».
        Так ``cart_utils.add_item`` автоматически отфильтровывает оба
        состояния через один старый флаг — не нужно править call-sites.
        """
        return {
            "id": self.pk,
            "title": self.title,
            "description": self.description,
            "img": self.image,
            "alt": self.alt or self.title,
            "badge": self.badge or None,
            "type_label": self.get_file_type_display(),
            "price": self.price_display,
            "price_cents": self.price_cents,
            "price_rub": int(self.price_rub),
            "not_for_sale": self.is_sold_out or self.is_placeholder,
            "is_sold_out": self.is_sold_out,
            "is_placeholder": self.is_placeholder,
            "is_free": self.kind == self.Kind.FREE,
            "download_url": self.download_url,
            "slug": self.slug,
        }


class ProductImage(models.Model):
    """Дополнительные ракурсы карточки для switcher'а (точки под картинкой).

    Главная картинка остаётся на ``Product.image`` — эта таблица хранит только
    доп. ракурсы. Если ``extra_images`` пустая, карточка показывается как
    обычная одиночная картинка.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="extra_images",
        verbose_name="Товар",
    )
    image = models.CharField(
        "Путь к картинке (в static/)",
        max_length=500,
        help_text="Например: images/shop/free/peper2.png",
    )
    alt = models.CharField("Alt-текст", max_length=200, blank=True, default="")
    display_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "доп. ракурс"
        verbose_name_plural = "доп. ракурсы"

    def __str__(self) -> str:
        return f"{self.product.title} — {self.image}"
