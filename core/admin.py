from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import ContactSubmission, NewsArticle, Order, OrderItem
from .pricing import format_minor_as_rub


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
        return request.user.is_superuser or request.user.groups.filter(name="Editors").exists()

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

