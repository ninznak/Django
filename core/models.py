from django.db import models


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
