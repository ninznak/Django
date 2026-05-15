from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.http import require_http_methods

from ..forms import NewsArticleCreateForm, ProductCreateForm, SiteSettingForm
from ..models import NewsArticle, Product
from ..permissions import (
    can_manage_content,
    can_publish_content,
    require_content_manager,
    role_key,
    role_label_ru,
)
from ..site_settings import invalidate_site_settings_cache
from .auth import _profile_seo


@require_http_methods(["GET"])
def profile(request):
    if not request.user.is_authenticated:
        login_url = reverse("core:sign_up_login")
        return redirect(f"{login_url}?{urlencode({'next': request.path})}")

    user = request.user
    can_manage = can_manage_content(user)
    return render(
        request,
        "core/profile.html",
        {
            "profile_user": user,
            "profile_role": role_label_ru(user),
            "profile_role_key": role_key(user),
            "can_manage_content": can_manage,
            "can_edit_site_settings": can_publish_content(user),
            "recent_products": (
                Product.objects.order_by("-updated_at")[:5] if can_manage else []
            ),
            "recent_articles": (
                NewsArticle.objects.only("id", "title", "status", "updated_at").order_by(
                    "-updated_at"
                )[:5]
                if can_manage
                else []
            ),
            "seo": _profile_seo(
                request,
                "Мой профиль — KurilenkoArt",
                "Личный кабинет пользователя KurilenkoArt.",
            ),
        },
    )


@require_http_methods(["GET", "POST"])
@require_content_manager
def profile_add_product(request):
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

    return render(
        request,
        "core/profile_product_form.html",
        {
            "form": form,
            "can_publish": can_publish_content(request.user),
            "seo": _profile_seo(
                request,
                "Добавить товар — KurilenkoArt",
                "Форма добавления товара или бесплатной модели.",
            ),
        },
    )


@require_http_methods(["GET", "POST"])
@require_content_manager
def profile_add_article(request):
    if request.method == "POST":
        form = NewsArticleCreateForm(request.POST, user=request.user)
        if form.is_valid():
            article = form.save(commit=False)
            if article.author_id is None:
                article.author = request.user
            if (
                article.status == NewsArticle.Status.PUBLISHED
                and article.published_at is None
            ):
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

    return render(
        request,
        "core/profile_article_form.html",
        {
            "form": form,
            "can_publish": can_publish_content(request.user),
            "seo": _profile_seo(
                request,
                "Добавить статью — KurilenkoArt",
                "Форма добавления новостной статьи.",
            ),
        },
    )


@require_http_methods(["GET", "POST"])
def profile_site_settings(request):
    if not request.user.is_authenticated:
        login_url = reverse("core:sign_up_login")
        return redirect(f"{login_url}?{urlencode({'next': request.path})}")
    if not can_publish_content(request.user):
        messages.error(request, "Редактировать настройки сайта могут только Editors и администратор.")
        return redirect("core:profile")

    from ..models import SiteSetting

    instance = SiteSetting.load()
    if request.method == "POST":
        form = SiteSettingForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            invalidate_site_settings_cache()
            messages.success(request, "Настройки сайта сохранены.")
            return redirect("core:profile")
    else:
        form = SiteSettingForm(instance=instance)

    return render(
        request,
        "core/profile_site_settings.html",
        {
            "form": form,
            "seo": _profile_seo(
                request,
                "Настройки сайта — KurilenkoArt",
                "Загруженность автора и счётчики на главной.",
            ),
        },
    )
