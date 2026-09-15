from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django_otp.admin import OTPAdminSite, OTPAdminAuthenticationForm


class SecureAdminSite(OTPAdminSite):
    """Switch enforcement only after provisioning an authenticator/recovery code."""
    def __init__(self, name='admin'):
        super().__init__(name)

    @property
    def login_form(self):
        return OTPAdminAuthenticationForm if settings.ADMIN_OTP_REQUIRED else AdminAuthenticationForm

    @property
    def login_template(self):
        return OTPAdminSite.login_template if settings.ADMIN_OTP_REQUIRED else 'admin/login.html'

    def has_permission(self, request):
        if settings.ADMIN_OTP_REQUIRED:
            return super().has_permission(request)
        return AdminSite.has_permission(self, request)
