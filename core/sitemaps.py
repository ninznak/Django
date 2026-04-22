from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import NewsArticle


class _BaseSitemap(Sitemap):
    def get_protocol(self, protocol=None):
        if protocol:
            return protocol
        return "https" if not settings.DEBUG else "http"


class CoreViewSitemap(_BaseSitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # Named URL patterns to expose to crawlers (no admin, no API).
        # Single home URL (/); /homepage/ is an alias and omitted to avoid duplicates.
        # Forum: add "core:forum" back when forum routes are re-enabled in core/urls.py.
        return [
            "core:homepage",
            "core:about",
            "core:portfolio",
            ("core:portfolio_gallery", {"slug": "3d"}),
            ("core:portfolio_gallery", {"slug": "products"}),
            ("core:portfolio_gallery", {"slug": "ai"}),
            "core:shop",
            "core:free_models",
            "core:news",
            # "core:forum",
            "core:copyright",
        ]

    def location(self, item):
        if isinstance(item, tuple):
            name, kwargs = item
            return reverse(name, kwargs=kwargs)
        return reverse(item)


class NewsArticleSitemap(_BaseSitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return NewsArticle.objects.filter(status=NewsArticle.Status.PUBLISHED)

    def location(self, article):
        return reverse("core:news_article", kwargs={"slug": article.slug})

    def lastmod(self, article):
        return article.updated_at
