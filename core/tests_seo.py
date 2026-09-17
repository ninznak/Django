"""Search crawl contracts, independent of client-side translations."""
import json
import re
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import NewsArticle


@override_settings(PUBLIC_SITE_URL="https://kurilenkoart.ru")
class SearchIntegrationTests(TestCase):
    def test_scales_metadata_and_application(self):
        response = self.client.get(reverse("core:scales_generator"))
        self.assertContains(response, "Бесплатный генератор текстур чешуи")
        self.assertContains(response, "Как создать и скачать бесплатную текстуру")
        self.assertContains(response, 'href="https://kurilenkoart.ru/scales/"')
        self.assertNotContains(response, 'hreflang="en"')
        self.assertNotContains(response, "WebAssembly")
        graph = json.loads(str(response.context["seo"]["json_ld"]))["@graph"]
        app = next(n for n in graph if n["@type"] == "WebApplication")
        self.assertEqual(app["offers"]["price"], "0")
        self.assertEqual(app["applicationCategory"], "DesignApplication")
        self.assertTrue(app["isAccessibleForFree"])
        self.assertTrue(any(n["@type"] == "WebPage" for n in graph))
        self.assertTrue(any(n["@type"] == "BreadcrumbList" for n in graph))

    def test_aliases_redirect_permanently(self):
        for name, target in [("homepage_path", "homepage"), ("scales_generator_tools", "scales_generator")]:
            self.assertRedirects(self.client.get(reverse("core:" + name)), reverse("core:" + target), status_code=301)

    def test_sitemap_uses_public_origin_and_unique_canonical_paths(self):
        response = self.client.get("/sitemap.xml")
        urls = [el.text for el in ElementTree.fromstring(response.content).iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertTrue(all(u.startswith("https://kurilenkoart.ru/") for u in urls))
        self.assertEqual(urls.count("https://kurilenkoart.ru/scales/"), 1)
        self.assertNotIn("https://kurilenkoart.ru/tools/scales/", urls)
        self.assertNotIn("https://kurilenkoart.ru/homepage/", urls)

    def test_shop_pagination_and_filters(self):
        from unittest.mock import patch
        products = [{"id": i, "title": f"Model {i}"} for i in range(30)]
        with patch("core.views.shop.get_shop_products", return_value=products):
            response = self.client.get(reverse("core:shop"), {"page": 2, "utm_source": "test"})
            self.assertEqual(response.context["seo"]["canonical_url"], "https://kurilenkoart.ru/shop/?page=2")
            self.assertIn("страница 2", response.context["seo"]["title"])
            self.assertContains(response, 'href="?page=3"', count=2)
            filtered = self.client.get(reverse("core:shop"), {"q": "Model", "page": 2})
            self.assertEqual(filtered.context["seo"]["robots"], "noindex, follow")

    def test_draft_preview_noindex_and_article_excerpt(self):
        article = NewsArticle.objects.create(title="Heightmaps", slug="heightmaps-test", excerpt="Уникальное описание карты высот", content="Text", status="draft")
        user = get_user_model().objects.create_user(username="seo-editor", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse("core:news_article", args=[article.slug]))
        self.assertEqual(response.context["seo"]["robots"], "noindex, nofollow")
        self.assertEqual(response.context["seo"]["description"], article.excerpt)

    def test_public_html_crawl_contract(self):
        titles = set()
        for name in ["homepage", "about", "portfolio", "shop", "free_models", "news", "copyright", "scales_generator"]:
            response = self.client.get(reverse("core:" + name))
            self.assertEqual(response.status_code, 200, name)
            html = response.content.decode()
            self.assertEqual(len(re.findall(r"<h1\b", html)), 1, name)
            self.assertEqual(html.count('rel="canonical"'), 1, name)
            title = re.search(r"<title>(.*?)</title>", html).group(1)
            self.assertNotIn(title, titles)
            titles.add(title)
            self.assertNotIn("noindex", response.context["seo"]["robots"])
            self.assertContains(response, 'href="/scales/"')
