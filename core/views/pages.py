import logging

from django.conf import settings
from django.db import transaction
from django.db.models import DateTimeField
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from ..forms import ContactForm
from ..abuse import reserve
from ..models import ContactSubmission, NewsArticle
from ..portfolio_gallery_data import gallery_context
from ..seo import get_seo, news_article_seo_overrides
from ..site_settings import contact_form_enabled
from ..view_utils import (
    contact_email_fingerprint,
    CONTACT_FORM_POST_LIMIT,
    CONTACT_FORM_WINDOW_SECONDS,
    deliver_contact_email,
    is_rate_limited,
)

logger = logging.getLogger(__name__)

HOMEPAGE_NEWS_LIMIT = 4


@transaction.atomic
def _store_contact_submission(data):
    # The dedupe claim rolls back if saving the message fails.
    if data.get("website") or not reserve(
        "contact_submission:" + contact_email_fingerprint(data), 1,
        settings.CONTACT_SUBMISSION_DEDUPE_SECONDS,
    ):
        return None
    return ContactSubmission.objects.create(
        name=data["name"], email=data["email"], subject=data["subject"],
        message=data["message"], email_sent=False,
    )


def _published_news_queryset():
    return (
        NewsArticle.objects.filter(status=NewsArticle.Status.PUBLISHED)
        .defer("content", "content_en")
        .order_by(
            Coalesce("published_at", "created_at", output_field=DateTimeField()).desc(),
            "-pk",
        )
    )


def _homepage_news_context() -> dict:
    articles = list(_published_news_queryset()[:HOMEPAGE_NEWS_LIMIT])
    return {
        "home_news_featured": articles[0] if articles else None,
        "home_news_side": articles[1:HOMEPAGE_NEWS_LIMIT],
    }


def _homepage_context(contact_form) -> dict:
    return {"contact_form": contact_form, **_homepage_news_context()}


@require_http_methods(["GET", "POST"])
def homepage(request):
    if request.resolver_match.url_name == "homepage_path" and request.method == "GET":
        return redirect("core:homepage", permanent=True)
    if request.method == "POST" and request.POST.get("contact_form"):
        if not contact_form_enabled():
            messages.error(request, "Отправка сообщений с сайта временно отключена.")
            return redirect("core:homepage")
        if is_rate_limited(
            request, "contact_form", CONTACT_FORM_POST_LIMIT, CONTACT_FORM_WINDOW_SECONDS
        ):
            messages.error(
                request,
                "Too many contact form submissions. Please wait a bit and try again.",
            )
            return render(
                request,
                "core/homepage.html",
                _homepage_context(ContactForm(request.POST)),
                status=429,
            )
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            submission = _store_contact_submission(data)
            if submission is None:
                messages.success(request, "Thank you — your message was received.")
                return redirect("core:homepage")
            if getattr(settings, "CONTACT_FORM_TRY_EMAIL", True):
                try:
                    if deliver_contact_email(data):
                        ContactSubmission.objects.filter(pk=submission.pk).update(
                            email_sent=True
                        )
                except Exception:
                    logger.exception(
                        "Contact form email failed (submission id=%s)", submission.pk
                    )
            messages.success(request, "Thank you — your message was received.")
            return redirect("core:homepage")
        return render(request, "core/homepage.html", _homepage_context(form))
    return render(request, "core/homepage.html", _homepage_context(ContactForm()))


@require_http_methods(["GET", "POST"])
def about(request):
    if request.method == "POST" and request.POST.get("contact_form"):
        if not contact_form_enabled():
            messages.error(request, "Отправка сообщений с сайта временно отключена.")
            return redirect("core:about")
        if is_rate_limited(
            request, "contact_form", CONTACT_FORM_POST_LIMIT, CONTACT_FORM_WINDOW_SECONDS
        ):
            messages.error(request, "Too many contact form submissions. Please wait a bit and try again.")
            return render(
                request,
                "core/about.html",
                {"contact_form": ContactForm(request.POST)},
                status=429,
            )
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            submission = _store_contact_submission(data)
            if submission is None:
                messages.success(request, "Thank you — your message was received.")
                return redirect("core:about")
            if getattr(settings, "CONTACT_FORM_TRY_EMAIL", True):
                try:
                    if deliver_contact_email(data):
                        ContactSubmission.objects.filter(pk=submission.pk).update(
                            email_sent=True
                        )
                except Exception:
                    logger.exception(
                        "Contact form email failed (submission id=%s)", submission.pk
                    )
            messages.success(request, "Thank you — your message was received.")
            return redirect("core:about")
        return render(request, "core/about.html", {"contact_form": form})
    return render(
        request,
        "core/about.html",
        {
            "contact_form": ContactForm(),
            "seo": get_seo(request, webpage_type="ProfilePage"),
        },
    )


def news(request):
    articles = list(_published_news_queryset())
    breadcrumbs = [
        {"label": "Главная", "url_name": "core:homepage"},
        {"label": "Новости", "current": True},
    ]
    return render(
        request,
        "core/news.html",
        {
            "featured_article": articles[0] if articles else None,
            "other_articles": articles[1:],
            "breadcrumbs": breadcrumbs,
            "seo": get_seo(
                request,
                breadcrumbs=breadcrumbs,
                webpage_type="CollectionPage",
            ),
        },
    )


def news_article(request, slug):
    from core.article_i18n import (
        article_has_english,
        build_article_i18_payload,
        build_article_seo_i18_payload,
    )

    queryset = (
        NewsArticle.objects.all()
        if request.user.is_staff
        else NewsArticle.objects.filter(status=NewsArticle.Status.PUBLISHED)
    )
    article = get_object_or_404(queryset, slug=slug)
    has_en = article_has_english(article)
    return render(
        request,
        "core/news_article.html",
        {
            "article": article,
            "article_has_english": has_en,
            "article_i18": build_article_i18_payload(article) if has_en else None,
            "article_seo_i18": (
                build_article_seo_i18_payload(request, article.slug, article) if has_en else None
            ),
            "seo": get_seo(
                request,
                robots="noindex, nofollow" if article.status != NewsArticle.Status.PUBLISHED else "index, follow, max-image-preview:large",
                **news_article_seo_overrides(
                    request, article.slug, article.title, article=article
                ),
            ),
            "breadcrumbs": [
                {"label": "Главная", "url_name": "core:homepage"},
                {"label": "Новости", "url_name": "core:news"},
                {"label": article.title, "current": True},
            ],
        },
    )


def portfolio(request):
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
    ctx = gallery_context(slug)
    if not ctx:
        raise Http404()
    meta = ctx["gallery"]
    seo = ctx["gallery_seo"]
    og_url = request.build_absolute_uri(static(meta["items"][0]["image"]))
    breadcrumbs = [
        {"label": "Главная", "url_name": "core:homepage"},
        {"label": "Портфолио", "url_name": "core:portfolio"},
        {"label": seo["title"], "current": True},
    ]
    return render(
        request,
        "core/portfolio_gallery.html",
        {
            **ctx,
            "seo": get_seo(
                request,
                title=seo["title"],
                description=seo["description"],
                keywords=seo.get("keywords", ""),
                canonical_path=request.path,
                og_image_url=og_url,
                breadcrumbs=breadcrumbs,
                webpage_type="CollectionPage",
            ),
            "breadcrumbs": breadcrumbs,
        },
    )


def copyright(request):
    return render(request, "core/copyright.html")


def scales_generator(request):
    if request.resolver_match.url_name == "scales_generator_tools":
        return redirect("core:scales_generator", permanent=True)
    breadcrumbs = [
        {"label": "Главная", "url_name": "core:homepage"},
        {"label": "Генератор чешуи", "current": True},
    ]
    return render(
        request,
        "core/scales_generator.html",
        {
            "breadcrumbs": breadcrumbs,
            "seo": get_seo(
                request,
                canonical_path=reverse("core:scales_generator"),
                breadcrumbs=breadcrumbs,
                application_ld={
                    "applicationCategory": "DesignApplication",
                    "operatingSystem": "Any",
                    "browserRequirements": "Requires JavaScript and HTML5 Canvas",
                    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "RUB"},
                    "featureList": ["Бесшовные текстуры чешуи", "PNG 8/16 бит", "TIFF 32-bit Float", "Редактор кривой высоты"],
                },
            ),
        },
    )
