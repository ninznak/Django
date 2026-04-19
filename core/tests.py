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
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import mail
from django.template import Context, Template
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from core import cart_utils
from core.forms import CheckoutForm, ContactForm, RegisterForm
from core.models import ContactSubmission, Order, OrderItem
from core.portfolio_gallery_data import gallery_context
from core.pricing import (
    USD_TO_RUB_RATE,
    format_minor_as_rub,
    usd_whole_to_rub_kopecks,
)
from core.seo import get_seo
from core.shop_data import SHOP_PRODUCTS, get_product

User = get_user_model()


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
        for p in SHOP_PRODUCTS:
            with self.subTest(product=p["id"]):
                self.assertTrue(required.issubset(p.keys()))
                self.assertIsInstance(p["id"], int)
                self.assertIsInstance(p["price_cents"], int)
                self.assertGreater(p["price_cents"], 0)

    def test_product_ids_are_unique(self):
        ids = [p["id"] for p in SHOP_PRODUCTS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_get_product_found_and_missing(self):
        first = SHOP_PRODUCTS[0]
        self.assertEqual(get_product(first["id"])["title"], first["title"])
        self.assertIsNone(get_product(9999))

    def test_get_product_accepts_numeric_strings(self):
        first = SHOP_PRODUCTS[0]
        self.assertEqual(get_product(str(first["id"])), first)


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
        self.valid_id = SHOP_PRODUCTS[0]["id"]
        self.other_id = SHOP_PRODUCTS[1]["id"]

    def test_add_item_increments_qty(self):
        cart_utils.add_item(self.session, self.valid_id, 2)
        cart_utils.add_item(self.session, self.valid_id, 3)
        stored = self.session[cart_utils.CART_SESSION_KEY]
        self.assertEqual(stored[str(self.valid_id)], 5)

    def test_add_item_ignores_unknown_product(self):
        cart_utils.add_item(self.session, 9999, 1)
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
    def test_pages_render_successfully(self):
        c = Client()
        for name in (
            "core:homepage",
            "core:homepage_path",
            "core:about",
            "core:news",
            "core:portfolio",
            "core:shop",
            "core:copyright",
            "core:sign_up_login",
        ):
            with self.subTest(url=name):
                response = c.get(reverse(name))
                self.assertEqual(response.status_code, 200, name)

    def test_news_article_renders(self):
        c = Client()
        response = c.get(reverse("core:news_article", args=["some-slug"]))
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

    def test_catchall_returns_404(self):
        response = Client().get("/definitely-does-not-exist/")
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Cart JSON API
# ---------------------------------------------------------------------------


class CartApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("core:cart_api")
        self.product_id = SHOP_PRODUCTS[0]["id"]

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
        self.client = Client()
        self.product = SHOP_PRODUCTS[0]

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
