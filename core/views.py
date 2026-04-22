import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.templatetags.static import static
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from . import cart_utils
from .portfolio_gallery_data import gallery_context
from .forms import (
    CheckoutForm,
    ContactForm,
    NewsArticleCreateForm,
    ProductCreateForm,
    RegisterForm,
)
from .models import ContactSubmission, NewsArticle, Order, OrderItem, Product
from .permissions import (
    can_manage_content,
    can_publish_content,
    require_content_manager,
    role_key,
    role_label_ru,
)
from .pricing import format_minor_as_rub
from .seo import get_seo, news_article_seo_overrides
from .shop_data import get_product, get_shop_products

User = get_user_model()
logger = logging.getLogger(__name__)


def _safe_contact_subject(raw: str, max_len: int = 200) -> str:
    cleaned = " ".join((raw or "").splitlines()).strip()
    if not cleaned:
        return "(no subject)"
    return cleaned[:max_len]


def _send_contact_email(cleaned: dict) -> None:
    site = settings.SEO_SITE_NAME
    subj = _safe_contact_subject(cleaned["subject"])
    body = (
        f"Name: {cleaned['name']}\n"
        f"From (form): {cleaned['email']}\n\n"
        f"{cleaned['message']}"
    )
    msg = EmailMessage(
        subject=f"[{site} contact] {subj}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_FORM_RECIPIENT],
        reply_to=[cleaned["email"]],
    )
    msg.send(fail_silently=False)


@require_http_methods(["GET", "POST"])
def homepage(request):
    """Главная страница — портфолио KurilenkoArt"""
    if request.method == "POST" and request.POST.get("contact_form"):
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            submission = ContactSubmission.objects.create(
                name=data["name"],
                email=data["email"],
                subject=data["subject"],
                message=data["message"],
                email_sent=False,
            )
            if getattr(settings, "CONTACT_FORM_TRY_EMAIL", True):
                try:
                    _send_contact_email(data)
                except Exception:
                    logger.exception(
                        "Contact form email failed (submission id=%s)", submission.pk
                    )
                else:
                    ContactSubmission.objects.filter(pk=submission.pk).update(
                        email_sent=True
                    )
            messages.success(request, "Thank you — your message was received.")
            return redirect("core:homepage")
        return render(request, "core/homepage.html", {"contact_form": form})
    return render(request, "core/homepage.html", {"contact_form": ContactForm()})


def about(request):
    """Страница About - Обо мне"""
    return render(request, 'core/about.html')


def news(request):
    """Страница новостей"""
    articles = NewsArticle.objects.filter(status=NewsArticle.Status.PUBLISHED)
    featured_article = articles.first()
    other_articles = articles[1:]
    return render(
        request,
        "core/news.html",
        {
            "featured_article": featured_article,
            "other_articles": other_articles,
        },
    )


def news_article(request, slug):
    """Страница статьи новостей"""
    queryset = NewsArticle.objects.all() if request.user.is_staff else NewsArticle.objects.filter(
        status=NewsArticle.Status.PUBLISHED
    )
    article = get_object_or_404(queryset, slug=slug)
    label = article.title
    ctx = {
        "article": article,
        "seo": get_seo(request, **news_article_seo_overrides(request, article.slug, label)),
    }
    return render(request, "core/news_article.html", ctx)


def portfolio(request):
    """Страница портфолио (навигация по секциям — якоря #portfolio-intro / #portfolio-3d / #portfolio-ai)."""
    cat = (request.GET.get("category") or "").strip().lower()
    base = reverse("core:portfolio")
    if cat == "3d":
        return redirect(f"{base}#portfolio-3d")
    if cat == "ai":
        return redirect(f"{base}#portfolio-ai")
    if cat == "all":
        return redirect(base)
    return render(request, "core/portfolio.html")


def portfolio_gallery(request, slug):
    """Отдельная страница-галерея для раздела 3D или AI (slug: 3d | ai)."""
    ctx = gallery_context(slug)
    if not ctx:
        raise Http404()
    meta = ctx["gallery"]
    seo = ctx["gallery_seo"]
    og_url = request.build_absolute_uri(static(meta["items"][0]["image"]))
    return render(
        request,
        "core/portfolio_gallery.html",
        {
            **ctx,
            "seo": get_seo(
                request,
                title=seo["title"],
                description=seo["description"],
                canonical_path=request.path,
                og_image_url=og_url,
            ),
        },
    )


# Размер страницы магазина = кратному ``_SHOP_ROW_LCM``, чтобы все страницы
# кроме последней получали полностью заполненные ряды карточек на любом
# брейкпоинте (``sm:grid-cols-2``, ``lg:grid-cols-3``). При per_page=12
# первая страница — 12 карточек = 4 ряда по 3 на lg и 6 рядов по 2 на sm,
# «дырок в ряду» не бывает, пока есть следующая страница.
_SHOP_ROW_LCM = 6  # НОК(2, 3) — полный ряд и на sm, и на lg
SHOP_PAGE_SIZE = 2 * _SHOP_ROW_LCM  # = 12


def shop(request):
    """Страница магазина — карточки из БД с row-aligned пагинацией.

    ``SHOP_PAGE_SIZE`` кратен НОК ширин сетки, поэтому все страницы, кроме
    последней, показывают полные ряды карточек. У последней страницы взять
    карточки негде — ей позволен неполный ряд (это совпадает с пользовательским
    ожиданием: ряд добивается только если есть «откуда добивать»).
    """
    paginator = Paginator(get_shop_products(), SHOP_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/shop.html",
        {
            "shop_products": page_obj.object_list,
            "shop_page_obj": page_obj,
        },
    )


def free_models(request):
    """Бесплатные 3D-модели, сгруппированные по табам ``free_category``.

    Мы читаем сразу инстансы ``Product`` (не ``as_cart_dict()``), чтобы
    шаблон мог пройтись по ``extra_images`` для switcher'а ракурсов.
    Группировка делается в Python — товаров несколько десятков, запрос
    и так один.
    """
    products = list(
        Product.objects.filter(kind=Product.Kind.FREE, is_published=True)
        .order_by("display_order", "id")
        .prefetch_related("extra_images")
    )

    # Все табы существуют всегда (даже если пока пустые) — это сохраняет
    # привычный UI с тремя заголовками и плейсхолдерами.
    tabs = [
        {"key": key, "label": label, "products": []}
        for key, label in Product.FreeCategory.choices
    ]
    by_key = {tab["key"]: tab for tab in tabs}
    for product in products:
        bucket = by_key.get(product.free_category)
        if bucket is not None:
            bucket["products"].append(product)

    return render(request, "core/free_models.html", {"free_tabs": tabs})


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
    """Страница форума (маршруты отключены в core/urls.py — см. комментарий FORUM)."""
    return render(request, 'core/forum.html')


def forum_topic(request, topic_id):
    """Страница темы форума (маршруты отключены в core/urls.py — см. комментарий FORUM)."""
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
    show_reg = getattr(settings, "AUTH_SHOW_REGISTRATION", False)
    ctx = {
        "auth_tab": "login",
        "next": next_param,
        "login_error": None,
        "register_form": None,
        "show_registration": show_reg,
    }

    if request.method != "POST":
        if not show_reg:
            ctx["auth_tab"] = "login"
        return render(request, "core/sign-up-login.html", ctx)

    action = (request.POST.get("auth_action") or "").strip().lower()
    next_url = _safe_next_url(request, settings.LOGIN_REDIRECT_URL)

    if action == "register" and not show_reg:
        messages.info(request, "Registration is currently unavailable.")
        return redirect("core:sign_up_login")

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


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


def copyright(request):
    """Страница авторского права"""
    return render(request, 'core/copyright.html')


@require_http_methods(["GET", "POST"])
def checkout(request):
    """Страница оформления заказа (без регистрации)."""
    summary = cart_utils.get_cart_summary(request)
    lines = summary["cart_lines"]

    # Если корзина пуста — перенаправляем в магазин
    if not lines:
        messages.warning(request, "Ваша корзина пуста. Добавьте товары для оформления заказа.")
        return redirect("core:shop")

    total_cents = summary["cart_subtotal_cents"]

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # Создаём заказ
            order = Order.objects.create(
                name=data["name"],
                email=data["email"],
                phone=data.get("phone", ""),
                country=data["country"],
                city=data["city"],
                address=data["address"],
                postal_code=data.get("postal_code", ""),
                total_cents=total_cents,
                notes=data.get("notes", ""),
                pd_consent=data["pd_consent"],
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            # Добавляем позиции заказа
            for line in lines:
                product = line["product"]
                OrderItem.objects.create(
                    order=order,
                    product_id=product["id"],
                    product_name=product["title"],
                    product_price_cents=product["price_cents"],
                    quantity=line["qty"],
                )

            # Очищаем корзину
            cart_utils.clear_cart(request.session)

            # Отправляем уведомление администратору
            if getattr(settings, "CONTACT_FORM_TRY_EMAIL", True):
                try:
                    _send_order_email(order, data)
                except Exception:
                    logger.exception("Order notification email failed (order id=%s)", order.pk)

            messages.success(request, f"Заказ №{order.id} успешно оформлен! Мы свяжемся с вами в ближайшее время.")
            return redirect("core:order_confirmation", order_id=order.id)

        # Если форма невалидна — показываем ошибки
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    else:
        form = CheckoutForm()

    ctx = {
        "form": form,
        "cart_lines": lines,
        "total_cents": total_cents,
        "total_formatted": format_minor_as_rub(total_cents),
        "seo": get_seo(
            request,
            title="Оформление заказа — KurilenkoArt",
            description="Оформите заказ на 3D-модели и цифровое искусство.",
            canonical_path=request.path,
        ),
    }
    return render(request, "core/checkout.html", ctx)


def _send_order_email(order: Order, data: dict) -> None:
    """Отправка уведомления о заказе администратору."""
    site = settings.SEO_SITE_NAME

    # Формируем список товаров
    items_list = "\n".join(
        f"  • {item.product_name} × {item.quantity} — {item.total_cents / 100:.2f} руб."
        for item in order.items.all()
    )

    body = (
        f"Новый заказ №{order.id} на сайте {site}\n\n"
        f"=== Данные заказчика ===\n"
        f"Имя: {order.name}\n"
        f"Email: {order.email}\n"
        f"Телефон: {order.phone or 'не указан'}\n\n"
        f"=== Адрес доставки ===\n"
        f"Страна: {order.country}\n"
        f"Город: {order.city}\n"
        f"Адрес: {order.address}\n"
        f"Индекс: {order.postal_code or 'не указан'}\n\n"
        f"=== Товары ===\n{items_list}\n\n"
        f"=== Итого ===\nСумма: {order.total_cents / 100:.2f} руб.\n\n"
        f"=== Комментарий ===\n{order.notes or 'нет'}\n\n"
        f"Согласие на обработку ПДн: {'да' if order.pd_consent else 'нет'}\n"
        f"Дата согласия: {order.pd_consent_date:%Y-%m-%d %H:%M:%S}\n"
        f"IP-адрес: {order.ip_address or 'не определён'}\n"
    )

    msg = EmailMessage(
        subject=f"[{site} заказ] Новый заказ №{order.id} от {order.name}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_FORM_RECIPIENT],
        reply_to=[order.email],
    )
    msg.send(fail_silently=False)


def order_confirmation(request, order_id):
    """Страница подтверждения заказа."""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, "Заказ не найден.")
        return redirect("core:shop")

    ctx = {
        "order": order,
        "seo": get_seo(
            request,
            title=f"Заказ №{order.id} подтверждён — KurilenkoArt",
            description=f"Ваш заказ №{order.id} успешно оформлен.",
            canonical_path=request.path,
        ),
    }
    return render(request, "core/order_confirmation.html", ctx)


# ---------------------------------------------------------------------------
# Профиль пользователя + UI-дружелюбные формы добавления контента.
#
# Это "зеркало админки" для авторизованных пользователей: на /profile/ они
# видят свои данные (логин, email, роль), а staff / Editors дополнительно
# получают кнопки «Добавить товар» и «Добавить статью», открывающие
# упрощённые формы ``ProductCreateForm`` / ``NewsArticleCreateForm``.
#
# Права на публикацию живут в одном месте — ``core/permissions.py``:
#   * ``can_manage_content(user)`` — пускать в формы (staff/Editors/superuser);
#   * ``can_publish_content(user)`` — разрешить ``is_published=True`` /
#     ``status=published`` (только superuser + группа Editors).
# ---------------------------------------------------------------------------


def _profile_seo(request, title: str, description: str) -> dict:
    """SEO для всех /profile/ страниц: noindex, nofollow, без JSON-LD.

    Выделено в helper, чтобы не повторять один и тот же блок в трёх вью.
    """
    return get_seo(
        request,
        title=title,
        description=description,
        canonical_path=request.path,
        robots="noindex, nofollow",
        no_json_ld=True,
    )


@require_http_methods(["GET"])
def profile(request):
    """Страница профиля: логин, email, ссылки на управление контентом."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('core:sign_up_login')}?next={request.path}")

    user = request.user
    can_manage = can_manage_content(user)
    ctx = {
        "profile_user": user,
        "profile_role": role_label_ru(user),
        "profile_role_key": role_key(user),
        "can_manage_content": can_manage,
        "recent_products": (
            Product.objects.order_by("-updated_at")[:5] if can_manage else []
        ),
        "recent_articles": (
            NewsArticle.objects.only(
                "id", "title", "status", "updated_at"
            ).order_by("-updated_at")[:5]
            if can_manage
            else []
        ),
        "seo": _profile_seo(
            request,
            "Мой профиль — KurilenkoArt",
            "Личный кабинет пользователя KurilenkoArt.",
        ),
    }
    return render(request, "core/profile.html", ctx)


@require_http_methods(["GET", "POST"])
@require_content_manager
def profile_add_product(request):
    """UI-дружелюбный дубль ``ProductAdmin`` для staff/Editors."""
    if request.method == "POST":
        form = ProductCreateForm(request.POST, user=request.user)
        if form.is_valid():
            product = form.save()
            messages.success(
                request,
                f"Товар «{product.title}» сохранён "
                f"({'опубликован' if product.is_published else 'черновик'}).",
            )
            return redirect("core:profile")
    else:
        form = ProductCreateForm(user=request.user)

    ctx = {
        "form": form,
        "can_publish": can_publish_content(request.user),
        "seo": _profile_seo(
            request,
            "Добавить товар — KurilenkoArt",
            "Форма добавления товара или бесплатной модели.",
        ),
    }
    return render(request, "core/profile_product_form.html", ctx)


@require_http_methods(["GET", "POST"])
@require_content_manager
def profile_add_article(request):
    """UI-дружелюбный дубль ``NewsArticleAdmin`` для staff/Editors."""
    if request.method == "POST":
        form = NewsArticleCreateForm(request.POST, user=request.user)
        if form.is_valid():
            article = form.save(commit=False)
            if article.author_id is None:
                article.author = request.user
            # Держим ``published_at`` в синхронизации со ``status`` — та же
            # логика, что и в ``NewsArticleAdmin.save_model`` (см. admin.py).
            if (
                article.status == NewsArticle.Status.PUBLISHED
                and article.published_at is None
            ):
                from django.utils import timezone

                article.published_at = timezone.now()
            elif article.status == NewsArticle.Status.DRAFT:
                article.published_at = None
            article.save()
            messages.success(
                request,
                f"Статья «{article.title}» сохранена "
                f"({'опубликована' if article.status == NewsArticle.Status.PUBLISHED else 'черновик'}).",
            )
            return redirect("core:profile")
    else:
        form = NewsArticleCreateForm(user=request.user)

    ctx = {
        "form": form,
        "can_publish": can_publish_content(request.user),
        "seo": _profile_seo(
            request,
            "Добавить статью — KurilenkoArt",
            "Форма добавления новостной статьи.",
        ),
    }
    return render(request, "core/profile_article_form.html", ctx)


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


def page_not_found_response(request):
    """HTML 404 page (shared by handler404 and URL catch-all)."""
    ctx = {
        "seo": get_seo(
            request,
            title="Страница не найдена — KurilenkoArt",
            description="Запрошенная страница не существует.",
            canonical_path=request.path,
            robots="noindex, follow",
            no_json_ld=True,
        ),
    }
    return render(request, "core/404.html", ctx, status=404)


def handler404(request, exception):
    """Вызывается для Http404 из view при DEBUG=False; см. также page_not_found_catchall."""
    return page_not_found_response(request)


def page_not_found_catchall(request, catchall):
    """
    Любой путь, не попавший в urlpatterns, попадает сюда (см. creativesphere/urls.py).
    При DEBUG=True иначе Django показал бы жёлтую отладочную 404 без этого маршрута.
    """
    return page_not_found_response(request)


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
