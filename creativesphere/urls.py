"""creativesphere URL Configuration"""
from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core import views as core_views
from core.sitemaps import CoreViewSitemap

# Получаем базовую директорию проекта
BASE_DIR = Path(__file__).resolve().parent.parent

sitemaps = {"pages": CoreViewSitemap}

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("core.urls")),
]

handler404 = "core.views.handler404"
handler500 = "core.views.handler500"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Must be last: unknown paths render templates/core/404.html with status 404.
# With DEBUG=True, Django would otherwise show the yellow technical 404 (handler404 is not used then).
urlpatterns.append(
    path("<path:catchall>", core_views.page_not_found_catchall, name="page_not_found_catchall"),
)
