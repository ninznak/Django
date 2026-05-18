from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

from ..seo import get_seo


def forum(request):
    return render(request, "core/forum.html")


def forum_topic(request, topic_id):
    return render(
        request,
        "core/forum_topic.html",
        {
            "topic_id": topic_id,
            "seo": get_seo(
                request,
                title=f"Тема форума #{topic_id} — KurilenkoArt",
                description=f"Обсуждение на форуме KurilenkoArt (тема №{topic_id}).",
                canonical_path=request.path,
            ),
        },
    )


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /profile/",
        "Disallow: /sign-up-login/",
        "Disallow: /checkout/",
        "Disallow: /order/",
    ]
    base = getattr(settings, "PUBLIC_SITE_URL", "") or ""
    if base:
        host = base.replace("https://", "").replace("http://", "").rstrip("/")
        if host.startswith("www."):
            host = host[4:]
        lines.append(f"Host: {host}")
        lines.append(f"Sitemap: {base}/sitemap.xml")
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def page_not_found_response(request):
    return render(
        request,
        "core/404.html",
        {
            "seo": get_seo(
                request,
                title="Страница не найдена — KurilenkoArt",
                description="Запрошенная страница не существует.",
                canonical_path=request.path,
                robots="noindex, follow",
                no_json_ld=True,
            ),
        },
        status=404,
    )


def handler404(request, exception):
    return page_not_found_response(request)


def page_not_found_catchall(request, catchall):
    return page_not_found_response(request)


def handler500(request):
    return render(
        request,
        "core/500.html",
        {
            "seo": get_seo(
                request,
                title="Ошибка сервера — KurilenkoArt",
                description="Временная ошибка сервера. Попробуйте позже.",
                canonical_path="/",
                robots="noindex, nofollow",
                no_json_ld=True,
            ),
        },
        status=500,
    )
