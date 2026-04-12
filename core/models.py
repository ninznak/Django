from django.db import models


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
