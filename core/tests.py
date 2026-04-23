"""Test suite for the ``core`` Django app.

Covers pure helpers (pricing, shop catalog, gallery data), session cart
logic, forms, models, views (HTML pages, JSON cart API, checkout, auth,
contact form, robots/sitemap, 404 handlers) and the pricing_extras
template filter.

Run with:

    python manage.py test core
"""
from __future__ import annotations

import json
from unittest import mock

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.template import Context, Template
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from core import cart_utils
from core.admin import NewsArticleAdmin, ProductAdmin
from core.forms import CheckoutForm, ContactForm, RegisterForm
from core.models import ContactSubmission, NewsArticle, Order, OrderItem, Product, ProductImage
from core.portfolio_gallery_data import gallery_context
from core.pricing import (
    USD_TO_RUB_RATE,
    format_minor_as_rub,
    usd_whole_to_rub_kopecks,
)
from core.seo import get_seo
from core.shop_data import (
    get_free_products,
    get_product,
    get_product_instance,
    get_shop_preview_products,
    get_shop_products,
)

User = get_user_model()


def _purchasable_shop_pair():
    """Две доступные к покупке позиции магазина (нужно для тестов корзины).

    Возвращает кортеж ``(Product, Product)``; оба товара гарантированно
    ``is_published=True`` и ``is_sold_out=False``. Набор берётся из
    data-миграции ``0012_seed_products`` — если её кто-то заменит,
    достаточно поправить только эту функцию.
    """
    qs = (
        Product.objects
        .filter(kind=Product.Kind.SHOP, is_published=True, is_sold_out=False)
        .order_by("display_order", "id")
    )
    return qs[0], qs[1]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class PricingTests(TestCase):
    def test_format_whole_rubles_uses_space_thousand_separator(self):
        self.assertEqual(format_minor_as_rub(100_000), "1 000 ₽")
        self.assertEqual(format_minor_as_rub(0), "0 ₽")
        self.assertEqual(format_minor_as_rub(50_00), "50 ₽")

    def test_format_fractional_kopecks_shows_two_decimals(self):
        self.assertEqual(format_minor_as_rub(12_345), "123.45 ₽")
        self.assertEqual(format_minor_as_rub(1), "0.01 ₽")

    def test_usd_whole_to_rub_kopecks_matches_rate(self):
        display, kopecks = usd_whole_to_rub_kopecks(29)
        self.assertEqual(kopecks, 29 * USD_TO_RUB_RATE * 100)
        self.assertEqual(display, format_minor_as_rub(kopecks))

    def test_usd_whole_to_rub_kopecks_zero(self):
        display, kopecks = usd_whole_to_rub_kopecks(0)
        self.assertEqual(kopecks, 0)
        self.assertEqual(display, "0 ₽")


class ShopDataTests(TestCase):
    def test_every_product_has_required_fields(self):
        required = {"id", "title", "price", "price_cents", "img", "alt"}
        shop = get_shop_products()
        self.assertTrue(shop, "Seed migration must populate at least one shop product")
        for p in shop:
            with self.subTest(product=p["id"]):
                self.assertTrue(required.issubset(p.keys()))
                self.assertIsInstance(p["id"], int)
                self.assertIsInstance(p["price_cents"], int)
                self.assertGreater(p["price_cents"], 0)

    def test_product_ids_are_unique(self):
        ids = [p["id"] for p in get_shop_products()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_get_product_found_and_missing(self):
        first = Product.objects.filter(kind=Product.Kind.SHOP).order_by("display_order", "id").first()
        self.assertEqual(get_product(first.pk)["title"], first.title)
        self.assertIsNone(get_product(9999))

    def test_get_product_accepts_numeric_strings(self):
        first = Product.objects.filter(kind=Product.Kind.SHOP).order_by("display_order", "id").first()
        self.assertEqual(get_product(str(first.pk)), first.as_cart_dict())

    def test_get_product_hides_unpublished(self):
        draft = Product.objects.create(
            kind=Product.Kind.SHOP,
            slug="draft-shop",
            title="Черновик",
            image="images/shop/battletoad.png",
            price_rub=100,
            is_published=False,
        )
        self.assertIsNone(get_product(draft.pk))

    def test_preview_hides_sold_out(self):
        preview = get_shop_preview_products()
        self.assertTrue(preview)
        self.assertTrue(all(not p["not_for_sale"] for p in preview))
        self.assertLessEqual(len(preview), 4)

    def test_free_products_seeded(self):
        free = get_free_products()
        self.assertGreaterEqual(len(free), 1)
        for p in free:
            with self.subTest(product=p["id"]):
                self.assertTrue(p["is_free"])
                self.assertEqual(p["price_cents"], 0)


class ProductModelTests(TestCase):
    def test_price_cents_and_display_match_rub(self):
        p = Product.objects.create(
            slug="price-check",
            title="Pricecheck",
            image="images/x.png",
            price_rub=3800,
        )
        self.assertEqual(p.price_cents, 380_000)
        self.assertEqual(p.price_display, "3 800 ₽")

    def test_is_purchasable_respects_flags(self):
        p = Product.objects.create(
            slug="purch", title="t", image="x.png", price_rub=100
        )
        self.assertTrue(p.is_purchasable)
        p.is_sold_out = True
        self.assertFalse(p.is_purchasable)
        p.is_sold_out = False
        p.is_published = False
        self.assertFalse(p.is_purchasable)
        p.is_published = True
        p.is_placeholder = True
        self.assertFalse(p.is_purchasable)

    def test_placeholder_product_not_for_sale_and_image_optional(self):
        # Placeholder можно создать без image/description — это ключевой
        # смысл фичи (редактор заводит "рамку на потом" одним кликом).
        p = Product.objects.create(
            slug="ph", title="Скоро", is_placeholder=True
        )
        self.assertEqual(p.image, "")
        d = p.as_cart_dict()
        self.assertTrue(d["is_placeholder"])
        self.assertTrue(d["not_for_sale"])  # корзина его отсечёт

    def test_all_image_paths_includes_extras_in_order(self):
        p = Product.objects.create(
            slug="multi", title="t", image="images/main.png", alt="main",
        )
        ProductImage.objects.create(product=p, image="images/b.png", alt="b", display_order=1)
        ProductImage.objects.create(product=p, image="images/a.png", alt="a", display_order=0)
        paths = p.all_image_paths()
        self.assertEqual(paths[0], ("images/main.png", "main"))
        self.assertEqual(paths[1][0], "images/a.png")
        self.assertEqual(paths[2][0], "images/b.png")

    def test_as_cart_dict_carries_sold_out_flag(self):
        p = Product.objects.create(
            slug="so", title="t", image="x.png", price_rub=500, is_sold_out=True
        )
        d = p.as_cart_dict()
        self.assertTrue(d["not_for_sale"])
        self.assertTrue(d["is_sold_out"])


class PortfolioGalleryDataTests(TestCase):
    def test_known_slugs_return_context(self):
        for slug in ("3d", "ai"):
            with self.subTest(slug=slug):
                ctx = gallery_context(slug)
                self.assertIsNotNone(ctx)
                self.assertEqual(ctx["gallery_slug"], slug)
                self.assertIn("title", ctx["gallery_seo"])
                self.assertTrue(ctx["gallery"]["items"])

    def test_unknown_slug_returns_none(self):
        self.assertIsNone(gallery_context("unknown"))

    def test_slug_is_case_insensitive_and_trimmed(self):
        self.assertIsNotNone(gallery_context("  3D  "))


# ---------------------------------------------------------------------------
# Cart utilities (pure functions over the session dict)
# ---------------------------------------------------------------------------


class _SessionStub(dict):
    """Dict that also tolerates ``session.modified = True`` assignments."""
    modified = False


class CartUtilsTests(TestCase):
    def setUp(self):
        self.session = _SessionStub()
        first, second = _purchasable_shop_pair()
        self.valid_id = first.pk
        self.other_id = second.pk
        self.sold_out = Product.objects.filter(
            kind=Product.Kind.SHOP, is_sold_out=True
        ).first()

    def test_add_item_increments_qty(self):
        cart_utils.add_item(self.session, self.valid_id, 2)
        cart_utils.add_item(self.session, self.valid_id, 3)
        stored = self.session[cart_utils.CART_SESSION_KEY]
        self.assertEqual(stored[str(self.valid_id)], 5)

    def test_add_item_ignores_unknown_product(self):
        cart_utils.add_item(self.session, 9999, 1)
        self.assertEqual(self.session, {})

    def test_add_item_ignores_sold_out_product(self):
        self.assertIsNotNone(self.sold_out, "Seed must include at least one sold-out product")
        cart_utils.add_item(self.session, self.sold_out.pk, 1)
        self.assertEqual(self.session, {})

    def test_set_qty_overwrites_and_removes_when_zero(self):
        cart_utils.add_item(self.session, self.valid_id, 2)
        cart_utils.set_qty(self.session, self.valid_id, 7)
        self.assertEqual(
            self.session[cart_utils.CART_SESSION_KEY][str(self.valid_id)], 7
        )
        cart_utils.set_qty(self.session, self.valid_id, 0)
        self.assertNotIn(
            str(self.valid_id), self.session[cart_utils.CART_SESSION_KEY]
        )

    def test_remove_item_removes_entry(self):
        cart_utils.add_item(self.session, self.valid_id, 1)
        cart_utils.remove_item(self.session, self.valid_id)
        self.assertEqual(self.session[cart_utils.CART_SESSION_KEY], {})

    def test_clear_cart_empties_session_entry(self):
        cart_utils.add_item(self.session, self.valid_id, 1)
        cart_utils.clear_cart(self.session)
        self.assertEqual(self.session[cart_utils.CART_SESSION_KEY], {})

    def test_build_lines_sorted_by_id_and_expanded(self):
        cart_utils.add_item(self.session, self.other_id, 1)
        cart_utils.add_item(self.session, self.valid_id, 2)
        lines = cart_utils.build_lines(self.session)
        self.assertEqual(
            [l["product"]["id"] for l in lines],
            sorted([self.valid_id, self.other_id]),
        )
        self.assertEqual(lines[0]["qty"], 2)

    def test_malformed_session_values_are_ignored(self):
        self.session[cart_utils.CART_SESSION_KEY] = {
            str(self.valid_id): "bad",
            str(self.other_id): 3,
            "9999": 2,
        }
        lines = cart_utils.build_lines(self.session)
        ids = {l["product"]["id"] for l in lines}
        self.assertEqual(ids, {self.other_id})

    def test_non_dict_session_entry_is_treated_as_empty(self):
        self.session[cart_utils.CART_SESSION_KEY] = "not a dict"
        self.assertEqual(cart_utils.build_lines(self.session), [])

    def test_get_cart_summary_totals(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.session = _SessionStub()
        cart_utils.add_item(request.session, self.valid_id, 2)
        cart_utils.add_item(request.session, self.other_id, 1)
        summary = cart_utils.get_cart_summary(request)
        expected_subtotal = (
            get_product(self.valid_id)["price_cents"] * 2
            + get_product(self.other_id)["price_cents"] * 1
        )
        self.assertEqual(summary["cart_total_items"], 3)
        self.assertEqual(summary["cart_subtotal_cents"], expected_subtotal)
        self.assertEqual(len(summary["cart_lines"]), 2)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ModelTests(TestCase):
    def test_order_str_includes_id_name_email(self):
        order = Order.objects.create(
            name="Иван",
            email="ivan@example.com",
            city="Москва",
            total_cents=1000,
            pd_consent=True,
        )
        rendered = str(order)
        self.assertIn(str(order.id), rendered)
        self.assertIn("Иван", rendered)
        self.assertIn("ivan@example.com", rendered)

    def test_order_item_total_cents_property(self):
        order = Order.objects.create(
            name="A", email="a@a.com", city="X", total_cents=0, pd_consent=True
        )
        item = OrderItem.objects.create(
            order=order,
            product_id=1,
            product_name="Foo",
            product_price_cents=500,
            quantity=3,
        )
        self.assertEqual(item.total_cents, 1500)
        self.assertIn("Foo", str(item))
        self.assertIn("3", str(item))

    def test_contact_submission_str_is_timestamp_and_subject(self):
        sub = ContactSubmission.objects.create(
            name="X", email="x@example.com", subject="Hello world", message="hi"
        )
        self.assertIn("Hello world", str(sub))

    def test_news_article_str_returns_title(self):
        article = NewsArticle.objects.create(
            title="Заголовок",
            slug="zagolovok",
            excerpt="Коротко",
            content="Контент",
        )
        self.assertEqual(str(article), "Заголовок")


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------


class FormTests(TestCase):
    def _valid_checkout_data(self, **overrides):
        data = {
            "name": "Иван Иванов",
            "email": "ivan@example.com",
            "phone": "+7 999 000 00 00",
            "country": "Россия",
            "city": "Москва",
            "address": "ул. Ленина, 1",
            "postal_code": "101000",
            "notes": "",
            "pd_consent": True,
            "license_ack": True,
        }
        data.update(overrides)
        return data

    def test_contact_form_valid(self):
        form = ContactForm(data={
            "name": "Jane",
            "email": "jane@example.com",
            "subject": "Hi",
            "message": "Hello",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_contact_form_requires_all_fields(self):
        form = ContactForm(data={})
        self.assertFalse(form.is_valid())
        for field in ("name", "email", "subject", "message"):
            self.assertIn(field, form.errors)

    def test_checkout_form_requires_pd_consent(self):
        form = CheckoutForm(data=self._valid_checkout_data(pd_consent=False))
        self.assertFalse(form.is_valid())
        self.assertIn("pd_consent", form.errors)

    def test_checkout_form_requires_license_ack(self):
        form = CheckoutForm(data=self._valid_checkout_data(license_ack=False))
        self.assertFalse(form.is_valid())
        self.assertIn("license_ack", form.errors)

    def test_checkout_form_valid_minimal(self):
        form = CheckoutForm(data=self._valid_checkout_data(phone="", address="", postal_code="", notes=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_checkout_form_requires_city_and_name(self):
        form = CheckoutForm(data=self._valid_checkout_data(name="", city=""))
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("city", form.errors)

    def test_register_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="existing", email="dup@example.com", password="pass12345!"
        )
        form = RegisterForm(data={
            "username": "newuser",
            "email": "DUP@example.com",
            "password1": "Abcdef1234!",
            "password2": "Abcdef1234!",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_register_form_normalizes_email_lowercase(self):
        form = RegisterForm(data={
            "username": "fresh",
            "email": "Fresh@Example.Com",
            "password1": "Abcdef1234!",
            "password2": "Abcdef1234!",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["email"], "fresh@example.com")


# ---------------------------------------------------------------------------
# Template filter
# ---------------------------------------------------------------------------


class PricingExtrasTemplateTagTests(TestCase):
    def _render(self, value):
        tpl = Template("{% load pricing_extras %}{{ value|rub_minor }}")
        return tpl.render(Context({"value": value}))

    def test_filter_formats_numeric_values(self):
        self.assertEqual(self._render(100_000), "1 000 ₽")

    def test_filter_returns_original_on_invalid(self):
        self.assertEqual(self._render("not a number"), "not a number")


class ArticleExtrasTemplateTagTests(TestCase):
    def _render(self, value):
        tpl = Template("{% load article_extras %}{{ value|render_article_body }}")
        return tpl.render(Context({"value": value}))

    def test_renders_heading_list_and_image(self):
        source = (
            "## Заголовок\n\n"
            "Абзац текста.\n\n"
            "- Первый пункт\n"
            "- Второй пункт\n\n"
            "![Подпись](images/news/model11.JPEG)\n"
        )
        html = self._render(source)
        self.assertIn("<h3", html)
        self.assertIn("Заголовок", html)
        self.assertIn("<ul", html)
        self.assertIn("Первый пункт", html)
        self.assertIn('src="/static/images/news/model11.JPEG"', html)

    def test_escapes_script_content(self):
        html = self._render("## <script>alert(1)</script>")
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_bold_and_italic_inline_markup(self):
        html = self._render("Это **важно** и *курсив* внутри абзаца.")
        self.assertIn("<strong>важно</strong>", html)
        self.assertIn("<em>курсив</em>", html)

    def test_inline_bold_inside_heading_and_list(self):
        source = (
            "## Заголовок с **акцентом**\n\n"
            "- пункт с *курсивом*\n"
            "- обычный пункт\n"
        )
        html = self._render(source)
        self.assertIn("<h3", html)
        self.assertIn("<strong>акцентом</strong>", html)
        self.assertIn("<em>курсивом</em>", html)
        self.assertIn("<ul", html)

    def test_ordered_list_renders_ol(self):
        source = "1. первый\n2. второй\n3. третий\n"
        html = self._render(source)
        self.assertIn("<ol", html)
        self.assertIn("list-decimal", html)
        self.assertIn("<li>первый</li>", html)
        self.assertIn("<li>третий</li>", html)

    def test_ordered_and_unordered_lists_do_not_mix(self):
        source = "- bullet A\n- bullet B\n\n1. number A\n2. number B\n"
        html = self._render(source)
        self.assertEqual(html.count("<ul"), 1)
        self.assertEqual(html.count("<ol"), 1)
        self.assertLess(html.index("<ul"), html.index("<ol"))

    def test_link_renders_anchor_for_safe_url(self):
        html = self._render("Смотри [сайт](https://example.com/page) здесь.")
        self.assertIn(
            '<a href="https://example.com/page"', html
        )
        self.assertIn("rel=\"noopener noreferrer\"", html)
        self.assertIn(">сайт</a>", html)

    def test_link_rejects_javascript_scheme(self):
        html = self._render("[click](javascript:alert(1))")
        self.assertNotIn("<a ", html)
        self.assertIn("[click]", html)

    def test_inline_image_still_renders_and_does_not_become_link(self):
        html = self._render("![alt](images/news/model11.JPEG)")
        self.assertIn('src="/static/images/news/model11.JPEG"', html)
        self.assertNotIn("<a ", html)


# ---------------------------------------------------------------------------
# SEO helper
# ---------------------------------------------------------------------------


class SeoTests(TestCase):
    def setUp(self):
        # Cached JSON-LD nodes would leak deterministic settings across tests
        # that override PUBLIC_SITE_URL / SEO_SITE_NAME — clear between tests.
        from core import seo as seo_module

        seo_module._static_graph_nodes.cache_clear()

    def test_get_seo_default_contains_canonical_and_json_ld(self):
        request = RequestFactory().get("/")
        data = get_seo(request)
        self.assertIn("canonical_url", data)
        self.assertTrue(data["canonical_url"].endswith("/"))
        self.assertTrue(data["json_ld"])

    def test_get_seo_respects_no_json_ld_override(self):
        request = RequestFactory().get("/")
        data = get_seo(request, no_json_ld=True)
        self.assertEqual(data["json_ld"], "")

    def test_get_seo_applies_overrides(self):
        request = RequestFactory().get("/")
        data = get_seo(request, title="X", description="Y", canonical_path="/z/")
        self.assertEqual(data["title"], "X")
        self.assertEqual(data["description"], "Y")
        self.assertTrue(data["canonical_url"].endswith("/z/"))

    def test_json_ld_contains_organization_and_website(self):
        request = RequestFactory().get("/")
        data = get_seo(request)
        payload = json.loads(str(data["json_ld"]))
        self.assertEqual(payload["@context"], "https://schema.org")
        types = {node["@type"] for node in payload["@graph"]}
        self.assertEqual(types, {"Organization", "WebSite"})

    def test_article_ld_is_appended_with_defaults(self):
        request = RequestFactory().get("/news/foo/")
        data = get_seo(
            request,
            canonical_path="/news/foo/",
            article_ld={"headline": "Hello", "description": "World"},
        )
        payload = json.loads(str(data["json_ld"]))
        articles = [n for n in payload["@graph"] if n["@type"] == "Article"]
        self.assertEqual(len(articles), 1)
        art = articles[0]
        self.assertEqual(art["headline"], "Hello")
        self.assertEqual(art["inLanguage"], "ru-RU")
        self.assertTrue(art["mainEntityOfPage"].endswith("/news/foo/"))
        self.assertIn("image", art)
        self.assertIn("publisher", art)

    def test_json_ld_escapes_html_closers(self):
        request = RequestFactory().get("/news/x/")
        data = get_seo(
            request,
            canonical_path="/news/x/",
            article_ld={"headline": "</script><b>pwn</b>"},
        )
        rendered = str(data["json_ld"])
        self.assertNotIn("</script>", rendered)
        self.assertIn("<\\/script>", rendered)

    def test_static_graph_nodes_are_cached(self):
        from core import seo as seo_module

        seo_module._static_graph_nodes.cache_clear()
        request = RequestFactory().get("/")
        get_seo(request)
        get_seo(request, title="Other")  # same site origin/image/name
        info = seo_module._static_graph_nodes.cache_info()
        self.assertEqual(info.misses, 1)
        self.assertGreaterEqual(info.hits, 1)

    @override_settings(PUBLIC_SITE_URL="https://example.com")
    def test_public_site_url_used_for_absolute_links(self):
        request = RequestFactory().get("/about/")
        data = get_seo(request, canonical_path="/about/")
        self.assertEqual(data["canonical_url"], "https://example.com/about/")

    def test_context_processor_is_lazy_and_does_not_force_build(self):
        """The context processor must not compute SEO unless the template reads it."""
        from core import context_processors as cp

        request = RequestFactory().get("/")
        with mock.patch.object(cp, "get_seo", wraps=cp.get_seo) as spy:
            ctx = cp.site_seo(request)
            # Still untouched — lazy wrapper hasn't been resolved.
            spy.assert_not_called()
            # Accessing a field resolves the lazy object and triggers one call.
            _ = ctx["seo"]["title"]
            spy.assert_called_once()


# ---------------------------------------------------------------------------
# Simple page views
# ---------------------------------------------------------------------------


class StaticPagesViewTests(TestCase):
    def setUp(self):
        self.article = NewsArticle.objects.create(
            title="Публичная статья",
            slug="public-article",
            excerpt="Кратко",
            content="Текст публичной статьи",
            status=NewsArticle.Status.PUBLISHED,
        )
        self.draft_article = NewsArticle.objects.create(
            title="Черновик",
            slug="draft-article",
            excerpt="Черновик",
            content="Текст черновика",
            status=NewsArticle.Status.DRAFT,
        )

    def test_pages_render_successfully(self):
        c = Client()
        for name in (
            "core:homepage",
            "core:homepage_path",
            "core:about",
            "core:news",
            "core:portfolio",
            "core:shop",
            "core:free_models",
            "core:copyright",
            "core:sign_up_login",
        ):
            with self.subTest(url=name):
                response = c.get(reverse(name))
                self.assertEqual(response.status_code, 200, name)

    def test_news_article_renders(self):
        c = Client()
        response = c.get(reverse("core:news_article", args=[self.article.slug]))
        self.assertEqual(response.status_code, 200)

    def test_news_article_404_for_unknown_slug(self):
        c = Client()
        response = c.get(reverse("core:news_article", args=["missing"]))
        self.assertEqual(response.status_code, 404)

    def test_news_article_hides_drafts_for_anonymous(self):
        c = Client()
        response = c.get(reverse("core:news_article", args=[self.draft_article.slug]))
        self.assertEqual(response.status_code, 404)

    def test_news_article_allows_staff_preview_for_drafts(self):
        staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="Secret1234!",
            is_staff=True,
        )
        c = Client()
        c.force_login(staff)
        response = c.get(reverse("core:news_article", args=[self.draft_article.slug]))
        self.assertEqual(response.status_code, 200)

    def test_shop_pagination_query_renders(self):
        c = Client()
        response = c.get(reverse("core:shop") + "?page=2")
        self.assertEqual(response.status_code, 200)

    def test_portfolio_gallery_valid_and_invalid(self):
        c = Client()
        ok = c.get(reverse("core:portfolio_gallery", args=["3d"]))
        self.assertEqual(ok.status_code, 200)
        missing = c.get(reverse("core:portfolio_gallery", args=["nope"]))
        self.assertEqual(missing.status_code, 404)

    def test_portfolio_category_redirects(self):
        c = Client()
        base = reverse("core:portfolio")
        r = c.get(base + "?category=3d")
        self.assertEqual(r.status_code, 302)
        self.assertIn("#portfolio-3d", r["Location"])
        r = c.get(base + "?category=ai")
        self.assertEqual(r.status_code, 302)
        self.assertIn("#portfolio-ai", r["Location"])
        r = c.get(base + "?category=all")
        self.assertRedirects(r, base, fetch_redirect_response=False)

    def test_robots_txt_basic(self):
        response = Client().get(reverse("core:robots_txt"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("User-agent: *", body)
        self.assertIn("Disallow: /admin/", body)

    @override_settings(PUBLIC_SITE_URL="https://example.com")
    def test_robots_txt_includes_sitemap_when_public_url_set(self):
        response = Client().get(reverse("core:robots_txt"))
        self.assertIn("Sitemap: https://example.com/sitemap.xml", response.content.decode())

    def test_sitemap_xml_responds(self):
        response = Client().get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("urlset", response.content.decode())
        self.assertIn(self.article.slug, response.content.decode())
        self.assertNotIn(self.draft_article.slug, response.content.decode())

    def test_catchall_returns_404(self):
        response = Client().get("/definitely-does-not-exist/")
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Cart JSON API
# ---------------------------------------------------------------------------


class CartApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.url = reverse("core:cart_api")
        first, _ = _purchasable_shop_pair()
        self.product_id = first.pk

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_get_empty_cart(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["lines"], [])
        self.assertEqual(data["totalItems"], 0)
        self.assertEqual(data["subtotalCents"], 0)

    def test_add_then_set_then_remove(self):
        r = self._post({"action": "add", "product_id": self.product_id, "qty": 2})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["totalItems"], 2)

        r = self._post({"action": "set", "product_id": self.product_id, "qty": 5})
        self.assertEqual(r.json()["totalItems"], 5)

        r = self._post({"action": "remove", "product_id": self.product_id})
        self.assertEqual(r.json()["totalItems"], 0)

    def test_clear_action(self):
        self._post({"action": "add", "product_id": self.product_id, "qty": 1})
        r = self._post({"action": "clear"})
        self.assertEqual(r.json()["totalItems"], 0)

    def test_add_rejects_unknown_product(self):
        r = self._post({"action": "add", "product_id": 9999, "qty": 1})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "unknown_product")

    def test_add_rejects_bad_id(self):
        r = self._post({"action": "add", "product_id": "not-int", "qty": 1})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "bad_id")

    def test_unknown_action_returns_400(self):
        r = self._post({"action": "frobnicate"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "unknown_action")

    def test_invalid_json_body(self):
        r = self.client.post(self.url, data=b"not-json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "invalid_json")

    def test_post_rate_limited_returns_429(self):
        with mock.patch("core.views.CART_API_POST_LIMIT", 1), mock.patch(
            "core.views.CART_API_WINDOW_SECONDS", 60
        ):
            first = self._post({"action": "add", "product_id": self.product_id, "qty": 1})
            self.assertEqual(first.status_code, 200)
            second = self._post({"action": "add", "product_id": self.product_id, "qty": 1})
            self.assertEqual(second.status_code, 429)
            self.assertEqual(second.json()["error"], "rate_limited")


# ---------------------------------------------------------------------------
# Contact form (home page POST)
# ---------------------------------------------------------------------------


class ContactFormSubmissionTests(TestCase):
    def test_valid_submission_creates_record_and_sends_email(self):
        c = Client()
        r = c.post(reverse("core:homepage"), {
            "contact_form": "1",
            "name": "Jane",
            "email": "jane@example.com",
            "subject": "Hi there",
            "message": "Hello",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.name, "Jane")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Hi there", mail.outbox[0].subject)
        submission.refresh_from_db()
        self.assertTrue(submission.email_sent)

    def test_invalid_submission_rerenders_form_without_record(self):
        c = Client()
        r = c.post(reverse("core:homepage"), {
            "contact_form": "1",
            "name": "",
            "email": "not-an-email",
            "subject": "",
            "message": "",
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    @override_settings(CONTACT_FORM_TRY_EMAIL=True)
    def test_email_failure_still_saves_submission(self):
        with mock.patch("core.views._send_contact_email", side_effect=RuntimeError("smtp boom")):
            r = Client().post(reverse("core:homepage"), {
                "contact_form": "1",
                "name": "Jane",
                "email": "jane@example.com",
                "subject": "Hi",
                "message": "Hello",
            })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        self.assertFalse(ContactSubmission.objects.get().email_sent)


# ---------------------------------------------------------------------------
# Checkout flow
# ---------------------------------------------------------------------------


class CheckoutFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        first, _ = _purchasable_shop_pair()
        # Keeping dict shape так, чтобы индексирование ``self.product["id"]``
        # и ``self.product["price_cents"]`` ниже в тестах работало без правок.
        self.product = first.as_cart_dict()

    def _add_to_cart(self, qty=2):
        self.client.post(
            reverse("core:cart_api"),
            data=json.dumps({"action": "add", "product_id": self.product["id"], "qty": qty}),
            content_type="application/json",
        )

    def test_empty_cart_redirects_to_shop(self):
        r = self.client.get(reverse("core:checkout"))
        self.assertRedirects(r, reverse("core:shop"))

    def test_checkout_get_renders_when_cart_has_items(self):
        self._add_to_cart()
        r = self.client.get(reverse("core:checkout"))
        self.assertEqual(r.status_code, 200)

    def test_valid_checkout_creates_order_and_clears_cart(self):
        self._add_to_cart(qty=2)
        expected_total = self.product["price_cents"] * 2
        data = {
            "name": "Иван",
            "email": "ivan@example.com",
            "phone": "",
            "country": "Россия",
            "city": "Москва",
            "address": "",
            "postal_code": "",
            "notes": "",
            "pd_consent": "on",
            "license_ack": "on",
        }
        r = self.client.post(reverse("core:checkout"), data)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.total_cents, expected_total)
        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.product_id, self.product["id"])
        self.assertEqual(item.quantity, 2)
        self.assertRedirects(
            r, reverse("core:order_confirmation", args=[order.id])
        )

        # Cart should be cleared after successful checkout.
        cart = self.client.get(reverse("core:cart_api")).json()
        self.assertEqual(cart["totalItems"], 0)

        # Admin notification email should have been sent.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"№{order.id}", mail.outbox[0].subject)

    def test_invalid_checkout_without_consent_does_not_create_order(self):
        self._add_to_cart()
        data = {
            "name": "Иван",
            "email": "ivan@example.com",
            "country": "Россия",
            "city": "Москва",
        }
        r = self.client.post(reverse("core:checkout"), data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_confirmation_page_found_and_missing(self):
        order = Order.objects.create(
            name="Анна",
            email="anna@example.com",
            city="Казань",
            total_cents=1000,
            pd_consent=True,
        )
        r = self.client.get(reverse("core:order_confirmation", args=[order.id]))
        self.assertEqual(r.status_code, 200)

        r = self.client.get(reverse("core:order_confirmation", args=[999_999]))
        self.assertRedirects(r, reverse("core:shop"))

    def test_checkout_idempotency_key_prevents_duplicate_order(self):
        self._add_to_cart(qty=1)
        checkout_url = reverse("core:checkout")
        checkout_page = self.client.get(checkout_url)
        self.assertEqual(checkout_page.status_code, 200)
        idem = checkout_page.context["checkout_idempotency_key"]
        payload = {
            "name": "Иван",
            "email": "ivan@example.com",
            "phone": "",
            "country": "Россия",
            "city": "Москва",
            "address": "",
            "postal_code": "",
            "notes": "",
            "pd_consent": "on",
            "license_ack": "on",
            "idempotency_key": idem,
        }
        first = self.client.post(checkout_url, payload)
        self.assertEqual(Order.objects.count(), 1)
        order_id = Order.objects.get().id
        self.assertRedirects(first, reverse("core:order_confirmation", args=[order_id]))
        second = self.client.post(checkout_url, payload)
        self.assertEqual(Order.objects.count(), 1)
        self.assertRedirects(second, reverse("core:order_confirmation", args=[order_id]))


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------


class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="Secret1234!"
        )

    def test_login_with_username(self):
        r = self.client.post(reverse("core:sign_up_login"), {
            "auth_action": "login",
            "username": "alice",
            "password": "Secret1234!",
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_email(self):
        r = self.client.post(reverse("core:sign_up_login"), {
            "auth_action": "login",
            "username": "alice@example.com",
            "password": "Secret1234!",
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_wrong_password_shows_error(self):
        r = self.client.post(reverse("core:sign_up_login"), {
            "auth_action": "login",
            "username": "alice",
            "password": "wrong-pw",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Invalid")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_redirected_from_auth_page(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("core:sign_up_login"))
        self.assertEqual(r.status_code, 302)

    def test_logout_redirects_and_clears_session(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("core:logout"))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(AUTH_SHOW_REGISTRATION=False)
    def test_registration_blocked_when_disabled(self):
        r = self.client.post(reverse("core:sign_up_login"), {
            "auth_action": "register",
            "username": "bob",
            "email": "bob@example.com",
            "password": "Abcdef1234!",
            "password_confirm": "Abcdef1234!",
        })
        self.assertEqual(r.status_code, 302)
        self.assertFalse(User.objects.filter(username="bob").exists())

    @override_settings(AUTH_SHOW_REGISTRATION=True)
    def test_registration_creates_user_when_enabled(self):
        r = self.client.post(reverse("core:sign_up_login"), {
            "auth_action": "register",
            "username": "bob",
            "email": "bob@example.com",
            "password": "Abcdef1234!",
            "password_confirm": "Abcdef1234!",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(username="bob").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_safe_next_url_prevents_open_redirect(self):
        # Already-authenticated users get redirected; external URLs must be ignored.
        self.client.force_login(self.user)
        r = self.client.get(reverse("core:sign_up_login") + "?next=http://evil.example.com/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], settings.LOGIN_REDIRECT_URL)


class NewsArticleAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = NewsArticleAdmin(NewsArticle, admin.site)
        self.editor_group = Group.objects.create(name="Editors")

    def _build_request(self, user):
        request = self.factory.post("/admin/core/newsarticle/add/")
        request.user = user
        return request

    def test_non_editor_cannot_publish(self):
        staff = User.objects.create_user(
            username="staff-only",
            email="staff-only@example.com",
            password="Secret1234!",
            is_staff=True,
        )
        article = NewsArticle(
            title="Test",
            slug="test",
            excerpt="",
            content="Body",
            status=NewsArticle.Status.PUBLISHED,
        )
        request = self._build_request(staff)
        with self.assertRaises(PermissionDenied):
            self.model_admin.save_model(request, article, form=None, change=False)

    def test_editor_can_publish_and_gets_timestamp(self):
        editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="Secret1234!",
            is_staff=True,
        )
        editor.groups.add(self.editor_group)
        article = NewsArticle(
            title="Published",
            slug="published",
            excerpt="",
            content="Body",
            status=NewsArticle.Status.PUBLISHED,
        )
        request = self._build_request(editor)
        self.model_admin.save_model(request, article, form=None, change=False)
        self.assertIsNotNone(article.published_at)


# ---------------------------------------------------------------------------
# Product admin — publish gate
# ---------------------------------------------------------------------------


class ProductAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.model_admin = ProductAdmin(Product, admin.site)
        self.editor_group, _ = Group.objects.get_or_create(name="Editors")

    def _build_request(self, user):
        request = self.factory.post("/admin/core/product/add/")
        request.user = user
        return request

    def _fresh_product(self, **overrides):
        data = dict(
            kind=Product.Kind.SHOP,
            slug="new-slug",
            title="Новый",
            image="images/shop/battletoad.png",
            price_rub=1000,
            is_published=True,
        )
        data.update(overrides)
        return Product(**data)

    def test_non_editor_cannot_publish(self):
        staff = User.objects.create_user(
            username="staff-p", email="sp@example.com", password="Secret1234!", is_staff=True
        )
        product = self._fresh_product()
        with self.assertRaises(PermissionDenied):
            self.model_admin.save_model(
                self._build_request(staff), product, form=None, change=False
            )

    def test_editor_can_publish(self):
        editor = User.objects.create_user(
            username="editor-p", email="ep@example.com", password="Secret1234!", is_staff=True
        )
        editor.groups.add(self.editor_group)
        product = self._fresh_product()
        self.model_admin.save_model(
            self._build_request(editor), product, form=None, change=False
        )
        self.assertTrue(Product.objects.filter(slug="new-slug", is_published=True).exists())

    def test_non_editor_can_save_as_draft(self):
        staff = User.objects.create_user(
            username="staff-d", email="sd@example.com", password="Secret1234!", is_staff=True
        )
        product = self._fresh_product(slug="draft-slug", is_published=False)
        self.model_admin.save_model(
            self._build_request(staff), product, form=None, change=False
        )
        saved = Product.objects.get(slug="draft-slug")
        self.assertFalse(saved.is_published)


# ---------------------------------------------------------------------------
# Shop / Free models views — rendering DB-backed products
# ---------------------------------------------------------------------------


class ShopFreeViewsTests(TestCase):
    def test_shop_page_lists_seeded_products(self):
        response = Client().get(reverse("core:shop"))
        self.assertEqual(response.status_code, 200)
        seed_product = get_shop_products()[0]
        self.assertContains(response, seed_product["title"])

    def test_free_models_page_renders_tabs_and_products(self):
        response = Client().get(reverse("core:free_models"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Халапеньо")
        # Все три таба присутствуют, даже если пустые:
        self.assertContains(response, 'data-tab-target="hobby"')
        self.assertContains(response, 'data-tab-target="art"')
        self.assertContains(response, 'data-tab-target="tech"')

    def test_free_models_shows_external_download_link(self):
        response = Client().get(reverse("core:free_models"))
        # Для download_url, начинающегося с http, рендерим как есть —
        # без {% static %}-префикса.
        self.assertContains(response, "https://disk.yandex.ru/")

    def test_free_models_respects_is_sold_out(self):
        # Снимаем публикацию у всех hobby-товаров и создаём один sold-out.
        Product.objects.filter(kind=Product.Kind.FREE, free_category="hobby").update(
            is_published=False
        )
        Product.objects.create(
            kind=Product.Kind.FREE,
            free_category="hobby",
            slug="sold-out-free",
            title="Завершённая раздача",
            image="images/shop/free/peper1.png",
            price_rub=0,
            download_url="https://example.com/file.zip",
            is_sold_out=True,
        )
        response = Client().get(reverse("core:free_models"))
        self.assertContains(response, "Завершённая раздача")
        self.assertContains(response, "Распродано")
        # Кнопка «Скачать» у sold-out карточки должна быть disabled.
        self.assertContains(response, "disabled")

    def test_shop_hides_unpublished_products(self):
        Product.objects.create(
            kind=Product.Kind.SHOP,
            slug="hidden-shop",
            title="Скрытый товар-XYZ",
            image="images/shop/battletoad.png",
            price_rub=999,
            is_published=False,
        )
        response = Client().get(reverse("core:shop"))
        self.assertNotContains(response, "Скрытый товар-XYZ")

    def test_free_models_renders_placeholder_product(self):
        # Placeholder-продукт в бесплатных моделях рендерится карточкой
        # «Скоро новая модель» — это замена прежнему хардкоду в шаблоне.
        Product.objects.create(
            kind=Product.Kind.FREE,
            free_category="hobby",
            slug="ph-hobby-soon",
            title="Скоро: Чумной доктор 2",
            description="Тестовый placeholder",
            is_placeholder=True,
        )
        response = Client().get(reverse("core:free_models"))
        self.assertContains(response, "free-placeholder-card")
        self.assertContains(response, "Скоро: Чумной доктор 2")
        self.assertContains(response, "Тестовый placeholder")

    def test_placeholder_product_cannot_be_added_to_cart(self):
        # Ключевая гарантия: placeholder — визуальный «скелет», не товар.
        # Попытка положить его в корзину должна мягко отсекаться get_product.
        from core.cart_utils import add_item
        from core.shop_data import get_product

        ph = Product.objects.create(
            kind=Product.Kind.SHOP,
            slug="ph-shop-soon",
            title="Скоро: новый товар",
            is_placeholder=True,
            price_rub=0,
        )
        # get_product возвращает dict; у placeholder-а not_for_sale=True,
        # и add_item его игнорирует.
        product_dict = get_product(ph.pk)
        self.assertIsNotNone(product_dict)
        self.assertTrue(product_dict["not_for_sale"])

        session = {}
        add_item(session, ph.pk, 1)
        self.assertEqual(session.get("cart", {}), {})

    def test_shop_pagination_non_last_pages_are_row_aligned(self):
        """Все страницы магазина, кроме последней, должны иметь число
        карточек, кратное ширине сетки (НОК sm=2, lg=3 = 6). Это гарантирует
        отсутствие дырявых рядов на лицевой части каталога — «добирание»
        карточками со следующей страницы достигается не JS-логикой, а
        row-aligned размером страницы.
        """
        from core.views import SHOP_PAGE_SIZE, _SHOP_ROW_LCM

        self.assertEqual(SHOP_PAGE_SIZE % _SHOP_ROW_LCM, 0)

        response = Client().get(reverse("core:shop") + "?page=1")
        self.assertEqual(response.status_code, 200)
        page_obj = response.context["shop_page_obj"]
        if page_obj.paginator.num_pages > 1:
            # Если есть следующая страница — текущая должна быть заполнена
            # ровно на per_page (все ряды полные).
            self.assertEqual(len(page_obj.object_list), SHOP_PAGE_SIZE)


# ---------------------------------------------------------------------------
# Профиль пользователя и единый модуль прав ``core.permissions``.
# Гарантируют, что staff/Editors/superuser видят /profile/, а формы
# /profile/products/add/ и /profile/articles/add/ блокируют публикацию
# для обычного staff.
# ---------------------------------------------------------------------------


class PermissionsHelpersTests(TestCase):
    """Единый модуль прав ``core.permissions`` — контракт для админки,
    форм и вью (см. AGENTS.md §6). Если кто-то дублирует логику или
    «откреплится» от модуля — тесты упадут."""

    @classmethod
    def setUpTestData(cls):
        cls.anon = None  # через request.user.is_authenticated=False
        cls.user = User.objects.create_user(username="u", password="pw")
        cls.staff = User.objects.create_user(username="s", password="pw", is_staff=True)
        cls.editor = User.objects.create_user(username="e", password="pw")
        cls.editor.groups.add(Group.objects.create(name="Editors"))
        cls.superuser = User.objects.create_superuser(username="a", password="pw")

    def test_role_key_maps_each_role(self):
        from core.permissions import role_key

        self.assertEqual(role_key(self.user), "user")
        self.assertEqual(role_key(self.staff), "staff")
        self.assertEqual(role_key(self.editor), "editor")
        self.assertEqual(role_key(self.superuser), "admin")

    def test_can_publish_content_only_superuser_and_editors(self):
        from core.permissions import can_publish_content

        self.assertFalse(can_publish_content(self.user))
        self.assertFalse(can_publish_content(self.staff))  # ключевое: staff ≠ publish
        self.assertTrue(can_publish_content(self.editor))
        self.assertTrue(can_publish_content(self.superuser))

    def test_can_manage_content_includes_staff(self):
        from core.permissions import can_manage_content

        self.assertFalse(can_manage_content(self.user))
        self.assertTrue(can_manage_content(self.staff))  # staff — ТОЛЬКО черновики
        self.assertTrue(can_manage_content(self.editor))
        self.assertTrue(can_manage_content(self.superuser))


class ProfileViewTests(TestCase):
    """Страница ``/profile/``: аутентификация, роль, recent-контент."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="plain", password="pw")
        cls.editor = User.objects.create_user(username="ed", password="pw")
        cls.editor.groups.add(Group.objects.create(name="Editors"))

    def test_anonymous_redirected_to_login(self):
        resp = Client().get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("core:sign_up_login"), resp["Location"])
        self.assertIn("next=", resp["Location"])

    def test_plain_user_sees_profile_without_content_panel(self):
        c = Client()
        c.force_login(self.user)
        resp = c.get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["can_manage_content"])
        self.assertEqual(resp.context["profile_role_key"], "user")
        # Обычный пользователь не видит список «недавних» товаров/статей.
        self.assertEqual(list(resp.context["recent_products"]), [])
        self.assertEqual(list(resp.context["recent_articles"]), [])

    def test_editor_sees_content_management(self):
        c = Client()
        c.force_login(self.editor)
        resp = c.get(reverse("core:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["can_manage_content"])
        self.assertEqual(resp.context["profile_role_key"], "editor")


class ProfileAddProductTests(TestCase):
    """Форма ``/profile/products/add/``: только staff/Editors, публикация ограничена."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="plain", password="pw")
        cls.staff = User.objects.create_user(username="stf", password="pw", is_staff=True)
        cls.editor = User.objects.create_user(username="ed", password="pw")
        cls.editor.groups.add(Group.objects.create(name="Editors"))

    # Slug генерируется из title через django.utils.text.slugify с
    # allow_unicode=False — кириллица выкидывается. Поэтому в тестах
    # фиксируем латинский slug явно, иначе generated-имя было бы "product".
    _PRODUCT_SLUG = "test-product-from-profile"

    def _valid_product_post(self, *, is_published=False):
        return {
            "kind": Product.Kind.SHOP,
            "file_type": Product.FileType.MODEL_3D,
            "free_category": "",
            "title": "Новый товар",
            "slug": self._PRODUCT_SLUG,
            "description": "desc",
            "badge": "",
            "image": "images/shop/x.png",
            "alt": "alt",
            "price_rub": 100,
            "download_url": "",
            "display_order": 0,
            "is_published": "on" if is_published else "",
            "is_sold_out": "",
            "is_placeholder": "",
        }

    def test_anonymous_redirected_to_login(self):
        resp = Client().get(reverse("core:profile_add_product"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("core:sign_up_login"), resp["Location"])

    def test_plain_user_redirected_to_profile(self):
        c = Client()
        c.force_login(self.user)
        resp = c.get(reverse("core:profile_add_product"))
        self.assertRedirects(resp, reverse("core:profile"))

    def test_staff_can_save_draft_but_not_publish(self):
        # Обычный staff заходит на форму, но если поставит is_published=True —
        # форма добавит ошибку (та же логика, что и в ProductAdmin).
        c = Client()
        c.force_login(self.staff)
        resp = c.post(
            reverse("core:profile_add_product"),
            self._valid_product_post(is_published=True),
        )
        self.assertEqual(resp.status_code, 200)  # остаёмся на форме с ошибкой
        self.assertFalse(Product.objects.filter(slug=self._PRODUCT_SLUG).exists())
        # А черновик — сохраняется.
        resp2 = c.post(
            reverse("core:profile_add_product"),
            self._valid_product_post(is_published=False),
        )
        self.assertRedirects(resp2, reverse("core:profile"))
        created = Product.objects.get(slug=self._PRODUCT_SLUG)
        self.assertFalse(created.is_published)

    def test_editor_can_publish(self):
        c = Client()
        c.force_login(self.editor)
        resp = c.post(
            reverse("core:profile_add_product"),
            self._valid_product_post(is_published=True),
        )
        self.assertRedirects(resp, reverse("core:profile"))
        created = Product.objects.get(slug=self._PRODUCT_SLUG)
        self.assertTrue(created.is_published)


class ProfileAddArticleTests(TestCase):
    """Форма ``/profile/articles/add/``: публикация только для Editors."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(username="stf", password="pw", is_staff=True)
        cls.editor = User.objects.create_user(username="ed", password="pw")
        cls.editor.groups.add(Group.objects.create(name="Editors"))

    # См. пояснение к ``ProfileAddProductTests._PRODUCT_SLUG``.
    _ARTICLE_SLUG = "test-article-from-profile"

    def _valid_article_post(self, status=NewsArticle.Status.DRAFT):
        return {
            "title": "Тестовая статья",
            "slug": self._ARTICLE_SLUG,
            "tag": "Статья",
            "excerpt": "Короткий анонс",
            "content": "Тело статьи.",
            "cover_image": "",
            "reading_time_minutes": 5,
            "status": status,
        }

    def test_staff_cannot_publish(self):
        c = Client()
        c.force_login(self.staff)
        resp = c.post(
            reverse("core:profile_add_article"),
            self._valid_article_post(status=NewsArticle.Status.PUBLISHED),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(NewsArticle.objects.filter(slug=self._ARTICLE_SLUG).exists())

    def test_staff_saves_draft_with_null_published_at(self):
        c = Client()
        c.force_login(self.staff)
        resp = c.post(
            reverse("core:profile_add_article"),
            self._valid_article_post(status=NewsArticle.Status.DRAFT),
        )
        self.assertRedirects(resp, reverse("core:profile"))
        art = NewsArticle.objects.get(slug=self._ARTICLE_SLUG)
        self.assertEqual(art.status, NewsArticle.Status.DRAFT)
        self.assertIsNone(art.published_at)
        self.assertEqual(art.author, self.staff)

    def test_editor_publishes_with_published_at_set(self):
        c = Client()
        c.force_login(self.editor)
        resp = c.post(
            reverse("core:profile_add_article"),
            self._valid_article_post(status=NewsArticle.Status.PUBLISHED),
        )
        self.assertRedirects(resp, reverse("core:profile"))
        art = NewsArticle.objects.get(slug=self._ARTICLE_SLUG)
        self.assertEqual(art.status, NewsArticle.Status.PUBLISHED)
        self.assertIsNotNone(art.published_at)