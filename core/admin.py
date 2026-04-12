from django.contrib import admin

from .models import ContactSubmission


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "subject", "name", "email", "email_sent")
    list_filter = ("email_sent", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_at", "email_sent")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
