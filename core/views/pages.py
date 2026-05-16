import logging

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from ..forms import ContactForm
from ..models import ContactSubmission, NewsArticle
from ..portfolio_gallery_data import gallery_context
from ..seo import get_seo, news_article_seo_overrides
from ..view_utils import (
    CONTACT_FORM_POST_LIMIT,
    CONTACT_FORM_WINDOW_SECONDS,
    is_rate_limited,
    send_contact_email,
)

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
def homepage(request):
    if request.method == "POST" and request.POST.get("contact_form"):
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
                {"contact_form": ContactForm(request.POST)},
                status=429,
            )
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
                    send_contact_email(data)
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


@require_http_methods(["GET", "POST"])
def about(request):
    if request.method == "POST" and request.POST.get("contact_form"):
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
            submission = ContactSubmission.objects.create(
                name=data["name"],
                email=data["email"],
                subject=data["subject"],
                message=data["message"],
                email_sent=False,
            )
            if getattr(settings, "CONTACT_FORM_TRY_EMAIL", True):
                try:
                    send_contact_email(data)
                except Exception:
                    logger.exception(
                        "Contact form email failed (submission id=%s)", submission.pk
                    )
                else:
                    ContactSubmission.objects.filter(pk=submission.pk).update(
                        email_sent=True
                    )
            messages.success(request, "Thank you — your message was received.")
            return redirect("core:about")
        return render(request, "core/about.html", {"contact_form": form})
    return render(request, "core/about.html", {"contact_form": ContactForm()})


def news(request):
    articles = list(
        NewsArticle.objects.filter(status=NewsArticle.Status.PUBLISHED).defer("content")
    )
    return render(
        request,
        "core/news.html",
        {
            "featured_article": articles[0] if articles else None,
            "other_articles": articles[1:],
            "breadcrumbs": [
                {"label": "Главная", "url_name": "core:homepage"},
                {"label": "Новости", "current": True},
            ],
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
                request, **news_article_seo_overrides(request, article.slug, article.title)
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
            "breadcrumbs": [
                {"label": "Главная", "url_name": "core:homepage"},
                {"label": "Портфолио", "url_name": "core:portfolio"},
                {"label": seo["title"], "current": True},
            ],
        },
    )


def copyright(request):
    return render(request, "core/copyright.html")
