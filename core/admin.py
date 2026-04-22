from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import ContactSubmission, NewsArticle, Order, OrderItem, Product, ProductImage
from .pricing import format_minor_as_rub


def _user_can_publish(request) -> bool:
    """Публиковать товары/статьи разрешено только superuser и группе Editors.

    Общая точка для ``NewsArticleAdmin`` и ``ProductAdmin`` — если появятся
    новые модели, подключайте их сюда же, чтобы правила публикации были
    в одном месте и легко менялись (см. AGENTS.md §11).
    """
    user = request.user
    return user.is_superuser or user.groups.filter(name="Editors").exists()


class OrderItemInline(admin.TabularInline):
    """Позиции заказа в админке."""
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "product_price_display", "quantity", "line_total_display")
    fields = ("product_name", "product_price_display", "quantity", "line_total_display")

    @admin.display(description="Цена за ед.")
    def product_price_display(self, obj):
        return format_minor_as_rub(obj.product_price_cents)

    @admin.display(description="Сумма")
    def line_total_display(self, obj):
        return format_minor_as_rub(obj.total_cents)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "name", "email", "phone", "city", "total_cents_display", "status", "pd_consent")
    list_filter = ("status", "pd_consent", "country", "created_at")
    search_fields = ("name", "email", "phone", "city", "address", "notes")
    readonly_fields = (
        "id", "created_at", "updated_at", "ip_address", "pd_consent_date",
        "name", "email", "phone", "country", "city", "address", "postal_code",
        "total_cents", "status", "notes"
    )
    ordering = ("-created_at",)
    inlines = (OrderItemInline,)
    date_hierarchy = "created_at"

    def total_cents_display(self, obj):
        return format_minor_as_rub(obj.total_cents)
    total_cents_display.short_description = "Сумма заказа"

    def has_add_permission(self, request):
        return False


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "subject", "name", "email", "email_sent")
    list_filter = ("email_sent", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_at", "email_sent")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "author", "tag", "published_at", "updated_at")
    list_filter = ("status", "tag", "published_at", "author")
    search_fields = ("title", "slug", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at", "-created_at")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Основное", {"fields": ("title", "slug", "status", "tag", "author")}),
        ("Содержимое", {"fields": ("excerpt", "content", "cover_image", "reading_time_minutes")}),
        ("Публикация", {"fields": ("published_at",)}),
        ("Тех. поля", {"fields": ("created_at", "updated_at")}),
    )

    @staticmethod
    def _can_publish(request):
        return _user_can_publish(request)

    def save_model(self, request, obj, form, change):
        wants_publish = obj.status == NewsArticle.Status.PUBLISHED
        if wants_publish and not self._can_publish(request):
            raise PermissionDenied("Публиковать статьи может только группа Editors или superuser.")

        if not obj.author_id and request.user.is_authenticated:
            obj.author = request.user

        if wants_publish and obj.published_at is None:
            obj.published_at = timezone.now()
        if obj.status == NewsArticle.Status.DRAFT:
            obj.published_at = None

        super().save_model(request, obj, form, change)


class ProductImageInline(admin.TabularInline):
    """Дополнительные ракурсы товара (switcher под главной картинкой).

    Если ни одного ракурса не добавлено — карточка показывает только
    ``Product.image``. Для магазинных товаров обычно хватает одного
    ракурса, для бесплатных моделей удобно добавлять 2-4.
    """

    model = ProductImage
    extra = 0
    fields = ("image", "alt", "display_order")
    ordering = ("display_order", "id")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Админка товаров магазина и бесплатных моделей.

    Права на *публикацию* (``is_published=True``) ограничены superuser и
    группой ``Editors`` — как у ``NewsArticleAdmin``. Обычный staff может
    создавать и редактировать черновики (``is_published=False``), но
    сделать их видимыми на сайте не может.

    ``fieldsets`` статические: и для «shop», и для «free» доступны все
    поля (``free_category``/``download_url`` игнорируются на стороне
    рендеринга, когда ``kind`` другой), — так админке проще переключать
    ``kind`` туда-сюда без перезагрузки формы.
    """

    list_display = (
        "title",
        "kind",
        "free_category",
        "price_display_admin",
        "is_published",
        "is_sold_out",
        "is_placeholder",
        "display_order",
        "updated_at",
    )
    list_filter = (
        "kind",
        "free_category",
        "file_type",
        "is_published",
        "is_sold_out",
        "is_placeholder",
    )
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ProductImageInline,)

    fieldsets = (
        ("Основное", {"fields": ("kind", "file_type", "free_category", "title", "slug", "badge")}),
        ("Содержимое", {"fields": ("description", "image", "alt")}),
        ("Цена / скачивание", {"fields": ("price_rub", "download_url")}),
        ("Публикация", {"fields": ("is_published", "is_sold_out", "is_placeholder", "display_order")}),
        ("Тех. поля", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Цена")
    def price_display_admin(self, obj):
        if obj.kind == Product.Kind.FREE:
            return "Бесплатно"
        return format_minor_as_rub(obj.price_cents)

    def save_model(self, request, obj, form, change):
        wants_publish = bool(obj.is_published)
        if wants_publish and not _user_can_publish(request):
            raise PermissionDenied(
                "Публиковать товары может только группа Editors или superuser. "
                "Снимите галочку «Опубликовано», чтобы сохранить как черновик."
            )
        super().save_model(request, obj, form, change)

