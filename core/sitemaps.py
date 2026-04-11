from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class CoreViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def get_protocol(self, protocol=None):
        if protocol:
            return protocol
        return "https" if not settings.DEBUG else "http"

    def items(self):
        # Named URL patterns to expose to crawlers (no admin, no API).
        # Single home URL (/); /homepage/ is an alias and omitted to avoid duplicates.
        return [
            "core:homepage",
            "core:about",
            "core:portfolio",
            "core:shop",
            "core:news",
            "core:forum",
            "core:copyright",
        ]

    def location(self, item):
        return reverse(item)
