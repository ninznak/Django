from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from ..forms import RegisterForm
from ..seo import get_seo
from ..view_utils import AUTH_POST_LIMIT, AUTH_WINDOW_SECONDS, is_rate_limited

User = get_user_model()


def safe_next_url(request, default="/"):
    cand = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if cand and url_has_allowed_host_and_scheme(
        cand,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return cand
    return default


def username_for_login(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    u = User.objects.filter(username__iexact=raw).first()
    if u:
        return u.get_username()
    if "@" in raw:
        u = User.objects.filter(email__iexact=raw).first()
        if u:
            return u.get_username()
    return None


@sensitive_post_parameters("password", "password1", "password2", "password_confirm")
@require_http_methods(["GET", "POST"])
def sign_up_login(request):
    if request.user.is_authenticated:
        return redirect(safe_next_url(request, settings.LOGIN_REDIRECT_URL))

    next_param = (request.POST.get("next") or request.GET.get("next") or "").strip()
    show_reg = getattr(settings, "AUTH_SHOW_REGISTRATION", False)
    ctx = {
        "auth_tab": "login",
        "next": next_param,
        "login_error": None,
        "register_form": None,
        "show_registration": show_reg,
    }

    if request.method != "POST":
        return render(request, "core/sign-up-login.html", ctx)

    if is_rate_limited(request, "auth_post", AUTH_POST_LIMIT, AUTH_WINDOW_SECONDS):
        ctx["login_error"] = "Too many attempts. Please wait a few minutes and try again."
        return render(request, "core/sign-up-login.html", ctx, status=429)

    action = (request.POST.get("auth_action") or "").strip().lower()
    next_url = safe_next_url(request, settings.LOGIN_REDIRECT_URL)

    if action == "register" and not show_reg:
        messages.info(request, "Registration is currently unavailable.")
        return redirect("core:sign_up_login")

    if action == "login":
        identifier = request.POST.get("username", "")
        password = request.POST.get("password", "")
        uname = username_for_login(identifier)
        user = authenticate(request, username=uname, password=password) if uname else None
        if user is not None:
            login(request, user)
            messages.success(request, "Signed in successfully.")
            return redirect(next_url)
        ctx["login_error"] = "Invalid email, username, or password."
        return render(request, "core/sign-up-login.html", ctx)

    if action == "register" and show_reg:
        ctx["auth_tab"] = "register"
        data = request.POST.copy()
        data["password1"] = request.POST.get("password", "")
        data["password2"] = request.POST.get("password_confirm", "")
        form = RegisterForm(data)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. You are now signed in.")
            return redirect(next_url)
        ctx["register_form"] = form
        return render(request, "core/sign-up-login.html", ctx)

    return render(request, "core/sign-up-login.html", ctx)


@require_http_methods(["POST"])
def logout_view(request):
    # POST-only (like Django's own LogoutView): a GET logout could be
    # triggered cross-site via <img>/link to forcibly sign users out.
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


def _profile_seo(request, title: str, description: str) -> dict:
    return get_seo(
        request,
        title=title,
        description=description,
        canonical_path=request.path,
        robots="noindex, nofollow",
        no_json_ld=True,
    )


@sensitive_post_parameters("old_password", "new_password1", "new_password2")
@require_http_methods(["GET", "POST"])
def profile_password_change(request):
    if not request.user.is_authenticated:
        login_url = reverse("core:sign_up_login")
        return redirect(f"{login_url}?{urlencode({'next': request.path})}")

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Пароль успешно изменён.")
            return redirect("core:profile")
    else:
        form = PasswordChangeForm(request.user)

    return render(
        request,
        "core/profile_password.html",
        {
            "form": form,
            "seo": _profile_seo(
                request,
                "Смена пароля — KurilenkoArt",
                "Изменение пароля учётной записи.",
            ),
        },
    )


class CorePasswordResetView(PasswordResetView):
    template_name = "core/password_reset.html"
    email_template_name = "core/password_reset_email.txt"
    subject_template_name = "core/password_reset_subject.txt"
    success_url = reverse_lazy("core:password_reset_done")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["seo"] = get_seo(
            self.request,
            title="Сброс пароля — KurilenkoArt",
            description="Запрос ссылки для сброса пароля.",
            canonical_path=self.request.path,
            robots="noindex, nofollow",
            no_json_ld=True,
        )
        return ctx


class CorePasswordResetDoneView(PasswordResetDoneView):
    template_name = "core/password_reset_done.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["seo"] = get_seo(
            self.request,
            title="Письмо отправлено — KurilenkoArt",
            description="Инструкции по сбросу пароля отправлены на email.",
            canonical_path=self.request.path,
            robots="noindex, nofollow",
            no_json_ld=True,
        )
        return ctx


class CorePasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "core/password_reset_confirm.html"
    success_url = reverse_lazy("core:password_reset_complete")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["seo"] = get_seo(
            self.request,
            title="Новый пароль — KurilenkoArt",
            description="Установка нового пароля.",
            canonical_path=self.request.path,
            robots="noindex, nofollow",
            no_json_ld=True,
        )
        return ctx


class CorePasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "core/password_reset_complete.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["seo"] = get_seo(
            self.request,
            title="Пароль обновлён — KurilenkoArt",
            description="Пароль успешно изменён.",
            canonical_path=self.request.path,
            robots="noindex, nofollow",
            no_json_ld=True,
        )
        return ctx
