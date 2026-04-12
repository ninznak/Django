from django.contrib import admin

from .models import ContactSubmission, Order, OrderItem
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
