import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from . import cart_utils
from .forms import RegisterForm
from .seo import get_seo
from .shop_data import get_product

User = get_user_model()


def homepage(request):
    """Главная страница — портфолио KurilenkoArt"""
    return render(request, 'core/homepage.html')


def about(request):
    """Страница About - Обо мне"""
    return render(request, 'core/about.html')


def news(request):
    """Страница новостей"""
    return render(request, 'core/news.html')


def news_article(request, slug):
    """Страница статьи новостей"""
    label = slug.replace("-", " ").strip() or slug
    label = label[:1].upper() + label[1:] if label else slug
    ctx = {
        "slug": slug,
        "seo": get_seo(
            request,
            title=f"{label} — KurilenkoArt | Новости",
            description=f"Статья «{label}» в разделе новостей KurilenkoArt: 3D-моделирование и AI.",
            canonical_path=request.path,
        ),
    }
    return render(request, "core/news_article.html", ctx)


def portfolio(request):
    """Страница портфолио"""
    category = request.GET.get('category', 'all')
    return render(request, 'core/portfolio.html', {'category': category})


def shop(request):
    """Страница магазина"""
    return render(request, 'core/shop.html')


def _serialize_cart_line(line):
    p = line["product"]
    return {
        "product": {
            "id": p["id"],
            "title": p["title"],
            "price": p["price"],
            "priceCents": p["price_cents"],
            "img": static(p["img"]),
            "alt": p["alt"],
        },
        "qty": line["qty"],
    }


def _cart_json(request):
    summary = cart_utils.get_cart_summary(request)
    return {
        "ok": True,
        "lines": [_serialize_cart_line(l) for l in summary["cart_lines"]],
        "totalItems": summary["cart_total_items"],
        "subtotalCents": summary["cart_subtotal_cents"],
    }


@require_http_methods(["GET", "POST"])
def cart_api(request):
    """JSON API for session cart (requires CSRF token on POST)."""
    if request.method == "GET":
        return JsonResponse(_cart_json(request))

    try:
        data = json.loads(request.body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    action = data.get("action")
    raw_pid = data.get("product_id")
    raw_qty = data.get("qty", 1)

    if action == "add":
        try:
            pid = int(raw_pid)
            qty = int(raw_qty) if raw_qty is not None else 1
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_id"}, status=400)
        if not get_product(pid):
            return JsonResponse({"ok": False, "error": "unknown_product"}, status=400)
        cart_utils.add_item(request.session, pid, max(1, qty))
    elif action == "set":
        try:
            pid = int(raw_pid)
            qty = int(raw_qty)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_params"}, status=400)
        cart_utils.set_qty(request.session, pid, qty)
    elif action == "remove":
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_id"}, status=400)
        cart_utils.remove_item(request.session, pid)
    elif action == "clear":
        cart_utils.clear_cart(request.session)
    else:
        return JsonResponse({"ok": False, "error": "unknown_action"}, status=400)

    return JsonResponse(_cart_json(request))


def forum(request):
    """Страница форума"""
    return render(request, 'core/forum.html')


def forum_topic(request, topic_id):
    """Страница темы форума"""
    ctx = {
        "topic_id": topic_id,
        "seo": get_seo(
            request,
            title=f"Тема форума #{topic_id} — KurilenkoArt",
            description=f"Обсуждение на форуме KurilenkoArt (тема №{topic_id}).",
            canonical_path=request.path,
        ),
    }
    return render(request, "core/forum_topic.html", ctx)


def _safe_next_url(request, default="/"):
    cand = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if cand and url_has_allowed_host_and_scheme(
        cand,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return cand
    return default


def _username_for_login(raw: str) -> str | None:
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
    """Страница регистрации и входа"""
    if request.user.is_authenticated:
        return redirect(_safe_next_url(request, settings.LOGIN_REDIRECT_URL))

    next_param = (request.POST.get("next") or request.GET.get("next") or "").strip()
    ctx = {
        "auth_tab": "login",
        "next": next_param,
        "login_error": None,
        "register_form": None,
    }

    if request.method != "POST":
        return render(request, "core/sign-up-login.html", ctx)

    action = (request.POST.get("auth_action") or "").strip().lower()
    next_url = _safe_next_url(request, settings.LOGIN_REDIRECT_URL)

    if action == "login":
        identifier = request.POST.get("username", "")
        password = request.POST.get("password", "")
        uname = _username_for_login(identifier)
        user = authenticate(request, username=uname, password=password) if uname else None
        if user is not None:
            login(request, user)
            messages.success(request, "Signed in successfully.")
            return redirect(next_url)
        ctx["login_error"] = "Invalid email, username, or password."
        return render(request, "core/sign-up-login.html", ctx)

    if action == "register":
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


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


def copyright(request):
    """Страница авторского права"""
    return render(request, 'core/copyright.html')


def robots_txt(request):
    """robots.txt with sitemap hint when PUBLIC_SITE_URL is set."""
    from django.conf import settings
    from django.http import HttpResponse

    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
    ]
    base = getattr(settings, "PUBLIC_SITE_URL", "") or ""
    if base:
        lines.append(f"Sitemap: {base}/sitemap.xml")
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def handler404(request, exception):
    """Обработчик 404 ошибки"""
    ctx = {
        "seo": get_seo(
            request,
            title="Страница не найдена — KurilenkoArt",
            description="Запрошенная страница не существует.",
            canonical_path="/",
            robots="noindex, follow",
            no_json_ld=True,
        ),
    }
    return render(request, "core/404.html", ctx, status=404)


def handler500(request):
    """Обработчик 500 ошибки"""
    ctx = {
        "seo": get_seo(
            request,
            title="Ошибка сервера — KurilenkoArt",
            description="Временная ошибка сервера. Попробуйте позже.",
            canonical_path="/",
            robots="noindex, nofollow",
            no_json_ld=True,
        ),
    }
    return render(request, "core/500.html", ctx, status=500)
