# AGENTS.md — Project map for AI coding agents

> Goal: give an AI agent everything it needs to make safe, targeted edits to this
> Django project **without reading every file**. Read this first, then jump only
> to the specific module you need to touch. Keep this file up to date when
> module responsibilities change.

---

## 1. What this project is

- **Name:** CreativeSphere / "KurilenkoArt" — a **Django 5** portfolio + shop site.
- **Surface:** server-rendered HTML (Tailwind via CDN), a small JSON cart API,
  Django admin for orders / contact messages.
- **Stack:** Django, SQLite, Gunicorn + Nginx + Let's Encrypt on Ubuntu/Debian
  VPS. **No JS build step, no database other than SQLite by default.**
- **Primary domain:** `kurilenkoart.ru` (see §8).

---

## 2. Directory layout (only what matters)

```
Django/
├── manage.py                           # Django entry point
├── runserver.py                        # Dev shortcut: sets up env + runs runserver on :8000
├── requirements.txt                    # Django, Pillow, gunicorn, python-dotenv
├── db.sqlite3                          # Dev DB (committed for convenience)
├── .env.example                        # Template for production .env
├── README.md                           # High-level overview for humans
├── DEPLOY_VPS.md                       # VPS deploy + SSL guide
├── AGENTS.md                           # ← this file
│
├── creativesphere/                     # Django "project" package
│   ├── settings.py                     # All settings (env-driven, production-hardened)
│   ├── urls.py                         # Root URLconf (admin, sitemap, core.urls, 404 catch-all)
│   └── wsgi.py
│
├── core/                               # The only first-party app
│   ├── apps.py                         # AppConfig (name="core", verbose_name="My studio")
│   ├── models.py                       # Order, OrderItem, ContactSubmission, NewsArticle
│   ├── admin.py                        # Read-mostly admin for Order + ContactSubmission
│   ├── forms.py                        # ContactForm, RegisterForm, CheckoutForm
│   ├── urls.py                         # app_name="core" route table
│   ├── views.py                        # All HTTP views (pages, cart API, checkout, auth)
│   ├── cart_utils.py                   # Session cart primitives (add/set/remove/clear/build_lines)
│   ├── pricing.py                      # format_minor_as_rub, usd_whole_to_rub_kopecks
│   ├── shop_data.py                    # SHOP_PRODUCTS catalog + get_product()
│   ├── portfolio_gallery_data.py       # PORTFOLIO_GALLERIES static data + gallery_context()
│   ├── context_processors.py           # site_seo (lazy), shop_cart
│   ├── seo.py                          # get_seo(), PAGE_SEO, JSON-LD builder (cached)
│   ├── sitemaps.py                     # CoreViewSitemap + NewsArticleSitemap
│   ├── templatetags/pricing_extras.py  # {{ value|rub_minor }}
│   ├── templatetags/article_extras.py  # {{ article.content|render_article_body }} (headings / ordered & unordered lists / inline images / bold / italic / safe links)
│   ├── tests.py                        # tests covering pricing/forms/cart/SEO/news/admin flows
│   └── migrations/                     # 0001_contact_submission, 0002_order, 0003_order_address_optional
│
├── templates/core/                     # HTML templates for every named URL
│   ├── base.html                       # Head/meta/OG/Twitter/JSON-LD wiring (consumes `seo`)
│   └── <page>.html                     # One per view
│
├── static/                             # Source static assets (CSS, JS, images)
├── staticfiles/                        # collectstatic target (generated in prod)
│
├── scripts/
│   ├── deploy-vps.sh                   # One-shot VPS installer: Nginx + Gunicorn + certbot SSL
│   ├── update.sh                       # git pull → pip → migrate → collectstatic → restart
│   ├── AUTO_UPDATE.md                  # How to wire update.sh into cron
│   └── crontab-daily.example
│
└── deploy/
    └── creativesphere-gunicorn.service # Reference systemd unit (script writes the real one)
```

Anything under `.venv/`, `venv/`, `.idea/`, `.vscode/`, `.gigaide/`,
`__pycache__/`, `staticfiles/` is generated or editor-local — **ignore**.

---

## 3. Request lifecycle (mental model)

1. `creativesphere/urls.py` sends `""` to `core.urls` and keeps `admin/` +
   `sitemap.xml` + a trailing `<path:catchall>` 404 route.
2. `core/urls.py` (`app_name="core"`) maps URL names → view functions in
   `core/views.py`. **Always use `reverse("core:<name>")`**, never hard-code
   paths.
3. Two context processors run on every request (registered in
   `creativesphere/settings.py` → `TEMPLATES[0].OPTIONS.context_processors`):
   - `core.context_processors.site_seo` — adds `seo` (lazy) + `contact_email`.
   - `core.context_processors.shop_cart` — adds `shop_products`,
     `shop_preview_products`, `cart_lines`, `cart_total_items`,
     `cart_subtotal_cents`, `cart_subtotal_formatted`.
4. Views typically render `core/<page>.html` extending `templates/core/base.html`,
   which reads `seo.*` for every meta tag.

---

## 4. Data model (core/models.py)

| Model | Purpose | Notable fields |
|---|---|---|
| `Order` | Guest checkout order (no user FK). Status enum `new/processing/paid/shipped/completed/cancelled`, defaults to `new`. | `name`, `email`, `phone`, `country` (default `"Россия"`), `city`, `address`, `postal_code`, `total_cents` (PositiveInteger, kopecks), `notes`, `pd_consent` (required), `pd_consent_date` (auto_now_add), `ip_address`, `created_at`, `updated_at`. `ordering = ["-created_at"]`. |
| `OrderItem` | Line in an `Order` (FK `related_name="items"`). | `product_id`, `product_name`, `product_price_cents`, `quantity`. Property `total_cents = price * qty`. |
| `ContactSubmission` | Contact-form message stored in admin. | `name`, `email`, `subject`, `message`, `created_at`, `email_sent` (bool flag: notification actually delivered). |
| `NewsArticle` | Admin-managed article with draft/publish flow. Public pages show only `published`. | `title`, `slug`, `excerpt`, `content`, `tag`, `reading_time_minutes`, `cover_image` (path in `static/`), `author` (nullable FK), `status` (`draft/published`), `published_at`, `created_at`, `updated_at`. |

**Money is stored as integer kopecks** (`*_cents` fields despite the name).
Render with `core.pricing.format_minor_as_rub` or the `|rub_minor` filter.

---

## 5. URL map (core/urls.py)

| URL name (`core:…`) | Path | View | Notes |
|---|---|---|---|
| `robots_txt` | `/robots.txt` | `views.robots_txt` | Plain text; appends `Sitemap:` line when `PUBLIC_SITE_URL` is set. |
| `homepage` | `/` | `views.homepage` | Hosts the contact form POST (hidden field `contact_form=1`). |
| `homepage_path` | `/homepage/` | `views.homepage` | Alias. Not in sitemap. |
| `about` | `/about/` | `views.about` | |
| `news` | `/news/` | `views.news` | |
| `news_article` | `/news/<slug>/` | `views.news_article` | Reads `NewsArticle` by slug. Public users can open only `status=published`; staff can preview drafts. SEO is built via `core.seo.news_article_seo_overrides(request, slug, title)` with per-slug `NEWS_ARTICLE_SEO` fallback behavior preserved. |
| `portfolio` | `/portfolio/` | `views.portfolio` | `?category=3d\|ai\|all` redirects to anchors or base. The homepage carousel (`templates/core/homepage.html`) links its three cards to `/portfolio/#portfolio-3d`, `#portfolio-products`, `#portfolio-ai` — keep those anchors in sync with `templates/core/portfolio.html`. |
| `portfolio_gallery` | `/portfolio/<slug>/` | `views.portfolio_gallery` | Slugs: `3d`, `ai`, `products`. Unknown → `Http404`. |
| `shop` | `/shop/` | `views.shop` | Data comes from context processor. Header includes a CTA button to `core:free_models`. |
| `free_models` | `/free-models/` | `views.free_models` | Dedicated free-download page with top folder-style tabs: `Хоббийные модели` / `Художественные модели` / `Технические модели`. Active tab uses site dark green (`#1a2e1a`) with white text. Real cards are currently in the hobby tab; all tabs include 4 placeholder cards for future photos. Rows use a single light translucent background. Model cards use a click-driven image switcher (dots + image click). |
| `cart_api` | `/api/cart/` | `views.cart_api` | GET returns cart JSON; POST body `{action, product_id, qty}` with `action ∈ {add,set,remove,clear}`. CSRF-protected. |
| `sign_up_login` | `/sign-up-login/` | `views.sign_up_login` | Login always; registration gated by `AUTH_SHOW_REGISTRATION`. Honors `?next=` (same-host only). |
| `logout` | `/logout/` | `views.logout_view` | |
| `copyright` | `/copyright/` | `views.copyright` | |
| `checkout` | `/checkout/` | `views.checkout` | Empty cart → redirect to `core:shop`. Creates `Order` + `OrderItem`s, clears cart, emails admin. |
| `order_confirmation` | `/order/<int>/confirmation/` | `views.order_confirmation` | Missing order → redirect to shop. |
| `forum`, `forum_topic` | — | views exist, routes **commented out**. Re-enable by uncommenting in `core/urls.py` + `core/sitemaps.py` + templates (search `FORUM DISABLED`). |

Root-level URLs (in `creativesphere/urls.py`): `admin/`, `sitemap.xml`, and the
catch-all `<path:catchall>` → `views.page_not_found_catchall` (status 404).
`handler404` and `handler500` are wired to `views.handler404` / `handler500`.

---

## 6. Key module APIs (signatures + invariants)

### `core/pricing.py`

```python
USD_TO_RUB_RATE = 80
def format_minor_as_rub(minor: int) -> str          # "1 000 ₽" / "12.34 ₽"
def usd_whole_to_rub_kopecks(usd_whole: int) -> tuple[str, int]  # (display, kopecks)
```

### `core/shop_data.py`

- `SHOP_PRODUCTS: list[dict]` — catalog of 6 products, ids `1..6`.
- `SHOP_PREVIEW_PRODUCTS = SHOP_PRODUCTS[:4]`.
- `get_product(product_id) -> dict | None` — by id (accepts int or numeric str).

Product dict keys: `id, title, type_i18, img, alt, badge, description, price, price_cents`.

### `core/cart_utils.py`

Session is the dict-like `request.session` (or any object supporting
`session.modified = True`). Cart lives under
`CART_SESSION_KEY = "creativesphere_cart_v1"` as `{str(product_id): int_qty}`.
**Never mutate that dict directly — always go through these helpers:**

```python
def add_item(session, product_id: int, qty: int = 1) -> None   # increments; unknown ids ignored
def set_qty(session, product_id: int, qty: int) -> None        # qty < 1 removes; unknown ids ignored
def remove_item(session, product_id: int) -> None
def clear_cart(session) -> None
def build_lines(session) -> list[dict]                         # [{"product": {...}, "qty": n}], sorted by id
def get_cart_summary(request) -> dict                          # {cart_lines, cart_total_items, cart_subtotal_cents}
def catalog_for_api() -> list[dict]                            # [{"id","title"}]
```

Malformed / non-numeric keys are silently dropped.

### `core/portfolio_gallery_data.py`

- `PORTFOLIO_GALLERIES: dict[slug, {slug, portfolio_hash, items[]}]` for `3d`, `ai`, `products`.
- `PORTFOLIO_GALLERY_SEO: dict[slug, {title, description}]`.
- `gallery_context(slug) -> dict | None` — returns `{gallery, gallery_slug, gallery_seo}` or `None`. Case-insensitive, trims whitespace.
- **Filesystem-scanned helpers** build the `items[]` dynamically at import time — drop a new file in the right folder and it appears in the gallery without a code change. Each helper ignores non-files and is safe on missing dirs:
  - `news_model_gallery_items()` — files in `static/images/news/` whose name contains `model` (case-insensitive). Feeds the `3d` gallery alongside `_PORTFOLIO_3D_BASE`; `model9` is lifted to the front as the hero.
  - `news_ai_gallery_items()` — files in `static/images/news/` whose name contains `ai` (case-insensitive), sorted so `AI1, AI2, …` come first by numeric suffix. Used by the `ai` gallery after the static "Verdant Machine" lead.
  - `portfolio_products_gallery_items()` — all files in `static/images/medals/`, sorted `medal1, medal2, …`; per-file titles come from `MEDAL_CAPTIONS`. The same map feeds `_medal_seo_description()` for the `products` gallery meta description.
- `GalleryItem` is a `TypedDict` with `image` (relative to `static/`), `title_i18`, `subtitle_i18`, `alt`. When you add a new bucket of images, reuse one of the existing i18n keys (`portfolio_3d_model_piece`, `portfolio_ai_piece`, `portfolio_products_item`, …) or add a new pair in both locale dicts in `templates/core/base.html`.

### `core/seo.py` — **read this before touching SEO**

Public API:

```python
SEO_TOPIC_KEYWORDS: str
PAGE_SEO: dict[url_name, dict]              # Per-page defaults (title/description/keywords/robots/no_json_ld)
NEWS_ARTICLE_SEO: dict[slug, dict]          # Per-news-article rich overrides (title/description/keywords/og_image/article_ld)
def get_seo(request, **overrides) -> dict
def news_article_seo_overrides(request, slug, label) -> dict   # → splat into get_seo
```

`get_seo` merges in this order (later wins):
`_DEFAULT_PAGE` → `PAGE_SEO[request.resolver_match.url_name]` → `**overrides`.
Then stamps in `canonical_url`, `og_image`, `site_name`, and `json_ld`.

Recognized special overrides: `canonical_path`, `og_image_url`, `article_ld`
(dict spread into a schema.org `Article` node), `no_json_ld` (truthy → empty
`json_ld`).

**News articles.** `views.news_article` delegates all SEO construction to
`news_article_seo_overrides(request, slug, label)`:

- If `slug` is a key in `NEWS_ARTICLE_SEO`, its entry (`title`, `description`,
  `keywords`, optional `og_image` as a `static/`-relative path, optional
  `article_ld` dict) is used. `article_ld.headline` is auto-filled from
  `label` if missing; `og_image` is resolved to an absolute URL via the
  internal `_absolute_url(static(...))`.
- Otherwise a generic per-`label` template is returned, preserving the old
  behavior for slugs without a dedicated entry.

To add rich SEO for a new article, just add a `NEWS_ARTICLE_SEO[<slug>]`
entry — no view edits needed. Keep values plain strings / lists / small dicts
(the module stays shallow-copy-safe).

Performance contract (don't regress):

- Uses **shallow** dict copies (all base values are immutable strings/bools
  or small dicts / tuples of strings).
- `_static_graph_nodes(...)` is `@lru_cache`d; **don't mutate the returned
  dicts** — always copy or extend into a fresh list.
- Context processor wraps the default dict in `SimpleLazyObject` so views that
  set their own `ctx["seo"]` skip one full JSON-LD build per request.

Templates already read: `seo.title`, `.description`, `.keywords`, `.robots`,
`.canonical_url`, `.og_type`, `.og_image`, `.site_name`, `.json_ld` (via
`mark_safe`). If you add a field, add it in `base.html` too.

### `core/forms.py`

| Form | Fields | Notable validation |
|---|---|---|
| `ContactForm` | name, email, subject (max 200), message (max 5000) | All required. |
| `RegisterForm(UserCreationForm)` | username, email, password1/2 | `clean_email` lowercases + rejects duplicates case-insensitively. |
| `CheckoutForm` | name, email, phone?, country (default "Россия"), city, address?, postal_code?, notes?, **pd_consent** | `clean_pd_consent` **requires True** — enforces 152-ФЗ consent. |

### `core/views.py` — conventions

- `_safe_next_url(request, default)` — uses `url_has_allowed_host_and_scheme`; use it every time you honor a `?next=` parameter.
- `_username_for_login(raw)` — resolves username **or** email (case-insensitive) to the actual username before `authenticate`.
- `_send_contact_email(cleaned)` / `_send_order_email(order, data)` — plain `EmailMessage` → `settings.CONTACT_FORM_RECIPIENT` via whatever email backend is configured. Both call sites wrap the send in `try/except` and log via `logger.exception`; never let email failures break a response.
- `sensitive_post_parameters` decorates `sign_up_login` — keep password fields listed there if you add any.

---

## 7. Templates (`templates/core/`)

- `base.html` is the layout; every page `{% extends "core/base.html" %}`.
- It already renders full meta + Open Graph + Twitter Card + JSON-LD using the
  `seo` context var. **Never hard-code meta tags in child templates** — extend
  `PAGE_SEO` or pass overrides to `get_seo` instead.
- Tailwind is loaded from the CDN script tag; site theme tokens are defined in
  a `<style>` block at the top of `base.html`. **No build step.**
- `{% load pricing_extras %}` unlocks `{{ kopecks|rub_minor }}`.
- `{% load article_extras %}` unlocks `{{ article.content|render_article_body }}` for news body markup. Input is HTML-escaped first, then the following markup is transformed:
  - Block-level: `## heading` → `<h3>`, `- item` → `<ul><li>`, `1. item` (any positive integer) → `<ol><li>`, `![alt](images/news/file.jpg)` on its own line → styled `<img>` block, blank line separates paragraphs.
  - Inline (works inside paragraphs, headings and list items): `**bold**` → `<strong>`, `*italic*` → `<em>`, `[label](url)` → `<a>` with `rel="noopener noreferrer"`. Only `http://`, `https://`, `mailto:`, `tel:`, `#`, `/`, `./` and `../` URLs are allowed — `javascript:`, `data:` and unknown schemes are rendered as plain text.
  - Cover image is rendered separately by the template from `NewsArticle.cover_image`; don't duplicate it inside `content` via `![]()`.

---

## 8. Settings & environment (`creativesphere/settings.py`)

Env-driven; sensible defaults for both dev (`DEBUG=1`) and production
(`DEBUG=0`). Canonical production domain: **`kurilenkoart.ru`** — there is no
legacy `trally.ru` anywhere.

Env vars (see `.env.example`):

| Var | Meaning |
|---|---|
| `DJANGO_SECRET_KEY` | Required in prod. Dev default is a throwaway. |
| `DEBUG` | `"1"` → DEBUG on. |
| `DJANGO_SITE_DOMAINS` | Comma-separated apices. Prod default: `kurilenkoart.ru`. Derives `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for both apex and `www.`. |
| `DJANGO_CANONICAL_DOMAIN` | Override for `PRIMARY_DOMAIN`. Defaults to first of `SITE_DOMAINS`. |
| `PUBLIC_SITE_URL` | e.g. `https://kurilenkoart.ru`. Used for absolute canonical / OG / sitemap URLs. Prod default: `https://<PRIMARY_DOMAIN>`. |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Fully override the derived values. |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `SEO_CONTACT_EMAIL`, `CONTACT_FORM_RECIPIENT`, `CONTACT_FORM_TRY_EMAIL` | Email wiring. Dev default: console backend. |
| `AUTH_SHOW_REGISTRATION` | `"1"` to expose the sign-up form on `/sign-up-login/`. Default off. |
| `SECURE_*`, `SECURE_HSTS_*` | HTTPS hardening switches (only active when `DEBUG=0`). |

Apps installed: `django.contrib.{admin,auth,contenttypes,sessions,messages,staticfiles,sites,sitemaps}` + `core`. `SITE_ID = 1`.

Login: `LOGIN_URL=/sign-up-login/`, `LOGIN_REDIRECT_URL=/`, `LOGOUT_REDIRECT_URL=/`.

---

## 9. Deployment & SSL (short form)

Full doc: `DEPLOY_VPS.md`. Quick recap so agents editing the script know the shape:

```bash
sudo bash scripts/deploy-vps.sh                              # defaults to kurilenkoart.ru, /var/www/Django
sudo bash scripts/deploy-vps.sh kurilenkoart.ru /var/www/Django [extra-apex ...]
```

`deploy-vps.sh` installs Python + Nginx + certbot, writes `.env`, creates the
`creativesphere-gunicorn` systemd unit bound to `127.0.0.1:8000`, writes an
Nginx `server_name <apex> www.<apex> …` block, then runs:

```
certbot --nginx -d <apex> -d www.<apex> … --non-interactive --agree-tos -m ${LETSENCRYPT_EMAIL:-admin@<primary>} --redirect
```

Auto-renew is handled by `certbot.timer` (installed by the deb package). Verify
with `sudo certbot renew --dry-run`.

`scripts/update.sh` is the in-place update path: `git pull` → `pip install` →
`migrate` → `collectstatic` → `systemctl restart creativesphere-gunicorn`. It
does **not** touch `.env` or Nginx config.

---

## 10. Tests (`core/tests.py`) — **use these as the contract**

89 tests. Run with:

```powershell
.\.venv\Scripts\python.exe manage.py test core
```

or on Linux/macOS:

```bash
python manage.py test core
```

Coverage map (read a test before making a semantically-loaded change):

| Class | What it pins |
|---|---|
| `PricingTests` | Formatting, RUB conversion. |
| `ShopDataTests` | Catalog shape, unique ids, `get_product`. |
| `PortfolioGalleryDataTests` | `gallery_context` for known/unknown slugs. |
| `CartUtilsTests` | Add/set/remove/clear, sort order, malformed session data. Uses a `dict` subclass that accepts `.modified = True`. |
| `ModelTests` | `__str__`s + `OrderItem.total_cents`. |
| `FormTests` | Contact / Checkout (pd_consent mandatory) / Register (duplicate email, email lowercased). |
| `PricingExtrasTemplateTagTests` | `\|rub_minor`. |
| `ArticleExtrasTemplateTagTests` | `\|render_article_body` — headings, ordered & unordered lists, inline images, bold / italic, safe links (and rejection of `javascript:`), HTML escaping. |
| `SeoTests` | Defaults, overrides, JSON-LD structure, HTML-closer escaping, `lru_cache` behavior, `PUBLIC_SITE_URL`, lazy context processor. |
| `StaticPagesViewTests` | Every public page renders 200; portfolio redirects; robots.txt and sitemap; 404 catch-all. |
| `CartApiTests` | Full GET/POST add/set/remove/clear + all 400 error paths. |
| `ContactFormSubmissionTests` | Happy path + invalid form + SMTP failure path. |
| `CheckoutFlowTests` | Empty cart redirect, full POST creates `Order` + items + email + clears cart, pd_consent blocks. |
| `AuthViewTests` | Login by username/email, wrong password, authenticated redirect, logout, registration gated, `?next=` open-redirect guard. |

---

## 11. Conventions & gotchas

- **Money = integer kopecks** (minor units). Never store floats. Format with
  `format_minor_as_rub` / `|rub_minor`.
- **URL building**: always `reverse("core:<name>", kwargs={...})`. The catch-all
  means a typo does not 404 the resolver — it renders the 404 template.
- **SEO**: don't hard-code meta tags in templates; extend `PAGE_SEO` or override
  via `get_seo(...)`. Base template reads every field it needs.
- **Cart**: mutate through `cart_utils.*` so `session.modified = True` is set
  correctly and unknown product ids are filtered.
- **152-ФЗ personal data consent**: `CheckoutForm.pd_consent` must stay
  required (checked in `CheckoutFlowTests`). `Order.pd_consent` and
  `pd_consent_date` must be persisted.
- **Forum**: code and templates exist but routes are commented out. See
  `core/urls.py` for the exact re-enable checklist.
- **Python version**: project is running on Python 3.14 locally (see
  `.venv`) but is compatible with 3.11+. Keep type hints `from __future__
  import annotations`-friendly; model files use plain `str` / builtins.
- **Windows dev**: PowerShell doesn't accept `&&` on old versions — use `;` or
  separate commands. The venv is at `.venv\Scripts\python.exe`.
- **Don't commit `.env`**. `.env.example` is the template.
- **Don't regress `core/seo.py` performance**: shallow copy + `lru_cache` are
  intentional. The `SeoTests` suite will catch accidental breakages.
- **News articles are DB-backed (`NewsArticle`).** Create/edit from Django admin.
  Public list/detail pages read only `status=published`; staff can preview draft
  detail pages. For a richer snippet in SERP/OG, add optional per-slug overrides
  in `core/seo.py::NEWS_ARTICLE_SEO` (title/description/keywords/og_image/article_ld).

  Hero / in-body images for news articles currently live under
  `static/images/news/` (see `gener1..gener8`, `Artcam2..4`, `model*`, `AI*`
  naming conventions).

---

## 12. Quick "I need to change X" cheat sheet

| I want to… | Edit |
|---|---|
| Add a product | `core/shop_data.py` (append to `SHOP_PRODUCTS`; ids are integers, unique). |
| Edit free downloads section/page | `templates/core/free_models.html` (folder tabs, cards, placeholders, single row background style, media switcher, links), `core/urls.py` + `core/views.py` (route/view), and `core/seo.py::PAGE_SEO["free_models"]`. |
| Change product pricing logic | `core/pricing.py` (+ its tests). |
| Add a new public page | `core/urls.py` (route) + `core/views.py` (view) + `templates/core/<page>.html` + optionally `core/seo.py::PAGE_SEO`. |
| Add a field to `Order` | `core/models.py` → new migration in `core/migrations/` → template + form if user-facing → tests. |
| Change meta/SEO per page | `core/seo.py::PAGE_SEO` **or** pass override kwargs to `get_seo` in the view. |
| Add rich SEO for a news article | `core/seo.py::NEWS_ARTICLE_SEO[<slug>]` — title / description / keywords / optional `og_image` / `article_ld`. `views.news_article` picks it up automatically. |
| Add a new news article | Create a `NewsArticle` in Django admin (`status=draft` or `published`). Public pages render DB data automatically; optional SEO enhancement goes to `core/seo.py::NEWS_ARTICLE_SEO[slug]`. |
| Add images to a portfolio sub-gallery | Drop files in the right folder — `static/images/medals/` feeds `products`; `static/images/news/` with `model*` feeds `3d` and with `AI*` feeds `ai`. No code changes needed; for per-medal captions, extend `MEDAL_CAPTIONS` in `core/portfolio_gallery_data.py`. |
| Change sitemap | `core/sitemaps.py`. |
| Change checkout email body | `core/views.py::_send_order_email`. |
| Change contact email recipient | env var `CONTACT_FORM_RECIPIENT` (falls back to `SEO_CONTACT_EMAIL`). |
| Tweak deploy | `scripts/deploy-vps.sh` + docs in `DEPLOY_VPS.md`. |
| Add daily job | hook into `scripts/update.sh` or add a new script + entry in `scripts/crontab-daily.example`. |
| Run tests | `python manage.py test core`. |

If the task needs context not covered here, open the specific file from §2 —
this document is the index.
