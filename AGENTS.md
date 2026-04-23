# AGENTS.md — Project map for AI coding agents

> Goal: give an AI agent everything it needs to make safe, targeted edits to this
> Django project **without reading every file**. Read this first, then jump only
> to the specific module you need to touch. Keep this file up to date when
> module responsibilities change. After each successful implementation iteration,
> update this file if behavior, structure, routes, i18n keys, or conventions
> changed.

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
│   ├── models.py                       # Order, OrderItem, ContactSubmission, NewsArticle, Product, ProductImage
│   ├── admin.py                        # Admin для Order, ContactSubmission, NewsArticle, Product (publish-gate для Editors/superuser)
│   ├── forms.py                        # ContactForm, RegisterForm, CheckoutForm, ProductCreateForm, NewsArticleCreateForm
│   ├── urls.py                         # app_name="core" route table
│   ├── views.py                        # All HTTP views (pages, cart API, checkout, auth, profile)
│   ├── permissions.py                  # Единая точка правды: can_publish_content / can_manage_content / role_key / @require_content_manager
│   ├── cart_utils.py                   # Session cart primitives (add/set/remove/clear/build_lines)
│   ├── pricing.py                      # format_minor_as_rub, usd_whole_to_rub_kopecks
│   ├── shop_data.py                    # Адаптер над Product: get_shop_products/get_free_products/get_product
│   ├── portfolio_gallery_data.py       # PORTFOLIO_GALLERIES static data + gallery_context()
│   ├── context_processors.py           # site_seo (lazy), shop_cart
│   ├── seo.py                          # get_seo(), PAGE_SEO, JSON-LD builder (cached)
│   ├── sitemaps.py                     # CoreViewSitemap + NewsArticleSitemap
│   ├── templatetags/pricing_extras.py  # {{ value|rub_minor }}
│   ├── templatetags/article_extras.py  # {{ article.content|render_article_body }} (headings / ordered & unordered lists / inline images / bold / italic / safe links)
│   ├── tests.py                        # tests covering pricing/forms/cart/SEO/news/admin/profile flows
│   └── migrations/                     # 0001_contact_submission, 0002_order, 0003_order_address_optional
│
├── templates/core/                     # HTML templates for every named URL
│   ├── base.html                       # Head/meta/OG/Twitter/JSON-LD wiring (consumes `seo`) + i18n engine (data-i18 / data-i18-placeholder / data-i18-aria-label)
│   ├── _form_field.html                # Универсальный рендер Django-поля (поддерживает help / help_i18 / as_checkbox)
│   ├── profile.html                    # Личный кабинет (логин, email, роль, ссылки на формы добавления)
│   ├── profile_product_form.html       # Форма /profile/products/add/ (обёртка над ProductAdmin)
│   ├── profile_article_form.html       # Форма /profile/articles/add/ (обёртка над NewsArticleAdmin)
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
| `free_models` | `/free-models/` | `views.free_models` | Dedicated free-download page with top folder-style tabs: `Художественные модели` / `Хоббийные модели` / `Технические модели` (порядок — из `Product.FreeCategory.choices`). Active tab uses site dark green (`#1a2e1a`) with white text. Карточки приходят из `Product` (`kind=free`, фильтр по `free_category`); пустые «Скоро новая модель» — это `Product.is_placeholder=True` (никакого хардкода в шаблоне). Названия табов переводятся через `data-i18="shop_free_tab_{{ tab.key }}"` (ключи `shop_free_tab_art`/`_hobby`/`_tech` — в `base.html::translations.ru/en`). Rows use a single light translucent background. Model cards use a click-driven image switcher (dots + image click). Клиентская пагинация в этом шаблоне использует общий helper `window.PaginationUtils` из `static/js/enhancements.js` (row-aligned окна страниц). |
| `cart_api` | `/api/cart/` | `views.cart_api` | GET returns cart JSON; POST body `{action, product_id, qty}` with `action ∈ {add,set,remove,clear}`. CSRF-protected. **IP-throttled** (`429 {"error":"rate_limited"}` when burst exceeds per-window limit in `core/views.py`). |
| `sign_up_login` | `/sign-up-login/` | `views.sign_up_login` | Login always; registration gated by `AUTH_SHOW_REGISTRATION`. Honors `?next=` (same-host only). |
| `logout` | `/logout/` | `views.logout_view` | |
| `profile` | `/profile/` | `views.profile` | Личный кабинет авторизованного пользователя. Анонимным — redirect на `core:sign_up_login?next=/profile/`. Staff/Editors/superuser (`can_manage_content(user)`) дополнительно видят блок «Управление контентом» со ссылками на формы добавления. Роль отдаётся шаблону как `profile_role` (русская подпись) + `profile_role_key` (ключ i18n: `admin`/`editor`/`staff`/`user`/`guest`). SEO — `noindex, nofollow`, без JSON-LD. |
| `profile_add_product` | `/profile/products/add/` | `views.profile_add_product` | UI-дружелюбный дубль `ProductAdmin` (форма `ProductCreateForm`). Gated декоратором `@require_content_manager` из `core.permissions`; публикацию (`is_published=True`) форма блокирует для обычного staff (только Editors/superuser). |
| `profile_add_article` | `/profile/articles/add/` | `views.profile_add_article` | UI-дружелюбный дубль `NewsArticleAdmin` (форма `NewsArticleCreateForm`). Те же правила прав + синхронизация `published_at` со `status`, как в `NewsArticleAdmin.save_model`. |
| `copyright` | `/copyright/` | `views.copyright` | |
| `checkout` | `/checkout/` | `views.checkout` | Empty cart → redirect to `core:shop`. Creates `Order` + `OrderItem`s, clears cart, emails admin. POST is **IP-throttled** and supports idempotency key (`idempotency_key` hidden form field or `X-Idempotency-Key` header) to prevent duplicate orders on retries. |
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

### `core/shop_data.py` — адаптер над `Product`

Данные товаров магазина и бесплатных моделей лежат в таблице
`core_product` (см. модель `Product` ниже); этот модуль — тонкая обёртка,
которая отдаёт им словарную форму, совместимую со старым контрактом.

```python
def get_shop_products() -> list[dict]              # опубликованные товары магазина
def get_shop_preview_products(limit: int = 4) -> list[dict]   # превью на главной (только покупабельные)
def get_free_products() -> list[dict]              # опубликованные бесплатные модели
def get_product(product_id) -> dict | None         # любого kind; None если черновик
def get_product_instance(product_id) -> Product | None  # то же, но инстанс модели
```

Словарь товара (`Product.as_cart_dict()`) содержит ключи:
`id, title, description, img, alt, badge, type_label, price, price_cents,
price_rub, not_for_sale, is_sold_out, is_free, download_url, slug`.

- `not_for_sale` и `is_sold_out` — алиасы одного и того же флага
  (оставлено для совместимости старых шаблонов/тестов).
- `type_label` заменил прежний `type_i18` — это готовая русская метка
  из `Product.FileType.choices` (i18n-ключа больше нет).

**Запрещено** импортировать `SHOP_PRODUCTS` / `SHOP_PREVIEW_PRODUCTS` —
этих модульных констант больше нет. Модуль не делает запросов на импорте,
поэтому его можно загрузить на чистой БД без ошибок (это важно для
`manage.py migrate` и `dumpdata`).

`views.shop` использует `SHOP_PAGE_SIZE=12` (кратно НОК сетки 2/3 = 6), чтобы
все страницы, кроме последней, имели полные ряды карточек на `sm` и `lg`.
Это серверная часть правила "если есть следующая страница — текущая не
заканчивается дыркой в ряду".

### `Product` / `ProductImage` (модели)

- `Product.kind`: `shop` | `free` — дискриминатор; один `ModelAdmin`
  обслуживает обе страницы `/shop/` и `/free_models/`.
- `Product.file_type`: `3d` | `2d` | `other` — подпись «3D модель» / «2D файл»
  в карточке берётся из `get_file_type_display()`, без i18n.
- `Product.free_category`: `hobby` | `art` | `tech` — в какой таб на
  `/free_models/` попадёт карточка (пусто для `kind=shop`).
- `Product.price_rub` — целое число в **рублях**. Копейки нигде не хранятся,
  но `Product.price_cents` (property = `price_rub * 100`) сохранён для
  совместимости с `Order.total_cents` / `OrderItem.product_price_cents`.
- `Product.is_sold_out` — показывать «Распродано» и отключить кнопку купить/
  скачать. `cart_utils.add_item` / `set_qty` такие товары не добавят
  (`as_cart_dict()["not_for_sale"] == True`).
- `Product.is_placeholder` — «Скоро новая модель». Заменяет прежний хардкод
  placeholder-карточек в `templates/core/free_models.html`. Позволяет
  редактору создать пустую карточку без `image`/`description`/`download_url`
  (поле `image` — `blank=True`). Шаблоны `shop.html` и `free_models.html`
  для таких товаров рендерят `<article class="free-placeholder-card">` (CSS
  в `static/css/enhancements.css`). Placeholder никогда не попадёт в
  корзину (`not_for_sale=True` независимо от `is_sold_out`) и скрыт из
  `get_shop_preview_products()` (главная не должна показывать «скелет»).
- `Product.image` — путь относительно `static/` (например,
  `images/shop/battletoad.png`). Необязателен, если товар — placeholder.
- `Product.download_url` — для бесплатных моделей. Если начинается с `http`,
  шаблон подставляет значение как есть; иначе оборачивает в `{% static %}`
  (A + C из обсуждения — допустимы и внешние URL, и локальные файлы в
  `static/files/free/`).
- `ProductImage(product=, image=, alt=, display_order=)` — доп. ракурсы для
  switcher'а (точки под картинкой). Главная картинка всё равно берётся из
  `Product.image`; `product.all_image_paths()` возвращает `[(path, alt), …]`
  главная + все `extra_images`.
- IDs 1..14 зарезервированы под исторические товары магазина (их знают
  `OrderItem.product_id` и сессии корзин); бесплатные модели начинаются
  со 101. После data-миграции `0012_seed_products` Postgres-последовательность
  выставляется так, чтобы admin-товары получили `id > max(id)`.

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

**SEO и DB-контент — что обновляется автоматически, а что нет.**

| Действие редактора в админке                  | `PAGE_SEO` | `NEWS_ARTICLE_SEO` | `sitemap.xml` | Нужно ли править код? |
|-----------------------------------------------|------------|---------------------|---------------|-----------------------|
| Опубликовал новую `NewsArticle`               | —          | fallback (generic)  | **+** (авто)  | По желанию — добавить `NEWS_ARTICLE_SEO[slug]` для «богатой» SEO (custom og_image + `article_ld` + ключи). |
| Добавил `Product` (shop/free) через админку   | —          | —                   | —             | **Нет.** У товара нет собственного URL; он отображается на `/shop/` или `/free_models/`, SEO которых уже задан. |
| Хочу расширить ключи `/shop/` или `/free-models/` под новый ассортимент | **да**, `PAGE_SEO[...]["keywords"]` | — | — | Редактирование `core/seo.py` + деплой. |
| Скрыл товар (`is_published=False` / `is_placeholder=True`) | — | — | — | Не влияет: страницы `/shop/` и `/free_models/` всё равно индексируются. |

Ключевое правило: **SEO привязано к URL-маршрутам, а не к строкам в БД.**
Товары/бесплатные модели не имеют собственных страниц, поэтому их добавление
не требует изменения SEO. Новые статьи получают свой `/news/<slug>/`, он
сразу попадает в `NewsArticleSitemap` (см. `core/sitemaps.py`) и получает
дефолтную SEO-обёртку через generic ветку `news_article_seo_overrides`;
«богатую» SEO заведёшь, когда действительно захочешь выделить статью.

Картинки на `og:image` для товаров не нужны — если однажды появится
товарная страница `/shop/<slug>/`, добавь соответствующий `url_name` в
`PAGE_SEO` и в зависимости от задачи — либо `og_image_url=…` через
override в view, либо свой `PRODUCT_SEO[slug]`-словарь по аналогии с
`NEWS_ARTICLE_SEO`.

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

### `core/permissions.py` — единая точка правды для прав на контент

Был дубляж: одинаковая логика «кто может публиковать» жила в
`admin.py::_user_can_publish`, `forms.py::_user_can_publish_content` и
`views.py::_user_is_content_manager`. Теперь всё это в одном модуле:

```python
EDITORS_GROUP_NAME = "Editors"                  # переименование здесь — одновременно во всех call-sites

def can_publish_content(user) -> bool           # superuser OR Editors — может ставить is_published=True / status=published
def can_manage_content(user) -> bool            # can_publish_content OR staff — пускаем в /profile/*/add/ (staff сохранит только черновик)
def role_key(user) -> str                       # "admin" / "editor" / "staff" / "user" / "guest" — для data-i18="profile_role_<key>"
def role_label_ru(user) -> str                  # русская подпись роли для первичного SSR-рендера profile.html

def require_content_manager(view_func) -> view_func   # декоратор: gate для профильных форм
#   anon → redirect("core:sign_up_login?next=…")
#   can_manage_content=False → messages.error + redirect("core:profile")
```

Правила:

- **`admin.py::_user_can_publish(request)`** — тонкая обёртка над
  `can_publish_content(request.user)`; оставлена как public-name, чтобы
  сохранить совместимость с `ProductAdminTests` и другими внешними точками.
- **`forms.py` (`ProductCreateForm.clean`, `NewsArticleCreateForm.clean`)** —
  импортируют `can_publish_content` напрямую; никакой локальной копии логики.
- **`views.py` (`profile_add_product`, `profile_add_article`)** — обёрнуты
  `@require_content_manager`; не делают свою проверку на `is_authenticated`.
- **Новые админ-модели с publish-gate** подключаем сюда же. Если появится
  четвёртое место, где нужна «разрешено только Editors/superuser», — не
  дублируйте логику, импортируйте `can_publish_content`.

Тесты контракта — `PermissionsHelpersTests`, `ProfileViewTests`,
`ProfileAddProductTests`, `ProfileAddArticleTests` в `core/tests.py`. Они
явно проверяют, что `staff ≠ publish`, но `staff` может зайти в форму и
сохранить черновик.

### `core/forms.py`

| Form | Fields | Notable validation |
|---|---|---|
| `ContactForm` | name, email, subject (max 200), message (max 5000) | All required. |
| `RegisterForm(UserCreationForm)` | username, email, password1/2 | `clean_email` lowercases + rejects duplicates case-insensitively. |
| `CheckoutForm` | name, email, phone?, country (default "Россия"), city, address?, postal_code?, notes?, **pd_consent** | `clean_pd_consent` **requires True** — enforces 152-ФЗ consent. |
| `ProductCreateForm(ModelForm)` | `kind/file_type/free_category/title/slug?/description?/badge?/image?/alt?/price_rub/download_url?/is_published/is_sold_out/is_placeholder/display_order` | Принимает `user=` в `__init__`. `clean_slug` автогенерит slug из title. `clean()` зависит от `kind`: для `free` требует `free_category` + `download_url` (если не placeholder), для `shop` — `price_rub > 0`. `is_published=True` разрешён только если `permissions.can_publish_content(user)`. |
| `NewsArticleCreateForm(ModelForm)` | `title/slug?/tag/excerpt/content/cover_image?/reading_time_minutes/status` | `user=` в `__init__`. `clean_slug` автогенерит slug из title. `status=published` блокируется в `clean()` для не-Editors/superuser. |

### `core/views.py` — conventions

- `_safe_next_url(request, default)` — uses `url_has_allowed_host_and_scheme`; use it every time you honor a `?next=` parameter.
- `_username_for_login(raw)` — resolves username **or** email (case-insensitive) to the actual username before `authenticate`.
- `_send_contact_email(cleaned)` / `_send_order_email(order, data)` — plain `EmailMessage` → `settings.CONTACT_FORM_RECIPIENT` via whatever email backend is configured. Both call sites wrap the send in `try/except` and log via `logger.exception`; never let email failures break a response.
- `sensitive_post_parameters` decorates `sign_up_login` — keep password fields listed there if you add any.
- `_is_rate_limited(request, scope, limit, window_seconds)` — cache-backed IP throttling helper for POST-heavy endpoints (`homepage` contact submit, `sign_up_login`, `cart_api`, `checkout`). Keep error contract stable: JSON endpoints return `429` with machine-readable error; HTML endpoints render with messages and `429` status.
- Checkout idempotency contract:
  - `templates/core/checkout.html` sends hidden `idempotency_key`.
  - `views.checkout` also accepts `X-Idempotency-Key`.
  - If the same key was already processed for that client IP within TTL, view redirects to existing `order_confirmation` instead of creating a duplicate order.

---

## 7. Templates (`templates/core/`)

- `base.html` is the layout; every page `{% extends "core/base.html" %}`.
- Header responsive contract: on narrow phones (`<sm`) top row keeps logo left
  and language switcher right; cart button moves to the lower row (`sm:hidden`)
  right after `Магазин` (burger + shop + cart + optional sign in for guests).
- Flash messages (`{% if messages %}` block in `base.html`) must clear the fixed
  header on mobile (no overlap), and homepage hero should reduce top padding when
  flash is present to avoid a large visual gap before "Творческое Портфолио".
  Flash message text is centered inside the pill (`text-center` on the `<p>`).
- It already renders full meta + Open Graph + Twitter Card + JSON-LD using the
  `seo` context var. **Never hard-code meta tags in child templates** — extend
  `PAGE_SEO` or pass overrides to `get_seo` instead.
- Tailwind is loaded from the CDN script tag; site theme tokens are defined in
  a `<style>` block at the top of `base.html`. **No build step.**
- `base.html` also owns the light/dark theme switcher (`#theme-toggle`):
  - Theme state is stored in `localStorage["themePreference"]` (`light|dark`).
  - First visit / empty localStorage must default to **light** theme. Do not
    auto-switch by `prefers-color-scheme`; dark is enabled only by saved user
    choice (`themePreference="dark"`).
  - `<html data-theme="...">` drives CSS variable palettes; keep dark colors in
    the dedicated `html[data-theme="dark"]` block to retheme in one place.
  - Toggle UI is rendered as a fixed floating action button (`.theme-fab`) near
    the bottom-right, intentionally outside the header nav cluster to avoid
    responsive-header layout regressions.
  - Current baseline keeps dark-token colors aligned with light theme values;
    visual dark styling is expected to be tuned by editing only
    `html[data-theme="dark"]` in `base.html`.
  - Animated background spheres are also theme-scoped in the same file:
    tune their dark look only via `html[data-theme="dark"] .orb-a/.orb-b/.orb-c`
    (gradients + glow), and keep movement shape in shared `@keyframes orbFloat*`.
  - A tiny preload script in `<head>` applies saved theme before first paint
    (prevents light flash before JS init).
  - Scrolled header color contract: `static/css/enhancements.css` sets
    `.site-header.is-scrolled` background via
    `var(--header-bg-scrolled, rgba(220, 232, 207, 0.92))`; therefore both
    light and dark values of `--header-bg-scrolled` must be defined in
    `templates/core/base.html`. If dark header turns green on scroll in prod,
    verify this variable in the dark block and redeploy with `collectstatic`
    so updated `enhancements.css` reaches Nginx-served staticfiles.
  - Hero gradient text (`.text-gradient-animated`) has a dual-path contract:
    - `html.can-clip-text` → classic background-clip gradient text.
    - `html.no-clip-text` → JS fallback `applyGradientTextFallback()` wraps text
      into `.gradient-char` spans and animates per-character color wave (no
      `-webkit-text-fill-color` dependency, no rectangle artifacts).
  - `updatePageTranslations()` must keep calling `applyGradientTextFallback()`
    after `[data-i18]` updates, otherwise language switch will revert the hero
    lines to plain text in no-clip browsers.
  - Rollback path: remove the preload script + `#theme-toggle` button +
    `setupThemeToggle/applyTheme` JS block and dark-override CSS in
    `templates/core/base.html`.
- `{% load pricing_extras %}` unlocks `{{ kopecks|rub_minor }}`.
- `{% load article_extras %}` unlocks `{{ article.content|render_article_body }}` for news body markup. Input is HTML-escaped first, then the following markup is transformed:
  - Block-level: `## heading` → `<h3>`, `- item` → `<ul><li>`, `1. item` (any positive integer) → `<ol><li>`, `![alt](images/news/file.jpg)` on its own line → styled `<img>` block, blank line separates paragraphs.
  - Inline (works inside paragraphs, headings and list items): `**bold**` → `<strong>`, `*italic*` → `<em>`, `[label](url)` → `<a>` with `rel="noopener noreferrer"`. Only `http://`, `https://`, `mailto:`, `tel:`, `#`, `/`, `./` and `../` URLs are allowed — `javascript:`, `data:` and unknown schemes are rendered as plain text.
  - Cover image is rendered separately by the template from `NewsArticle.cover_image`; don't duplicate it inside `content` via `![]()`.
- `homepage.html` hero carousel (`.cs-card`) should keep hover motion smooth and calm (no spring overshoot curves that cause visual jerk on pointer hover). Prefer gentle `ease-out`-style cubic-bezier and moderate lift/scale. **Stacking:** the middle card uses the highest base `z-index` (fan “front”), so it is never covered by both side cards at once; sides use lower layers (`0→1`, `1→3`, `2→2`); hovered card still uses `z-index: 10`.
- Homepage dark-mode card contract:
  - News section wrapper uses `.home-news-section`; article cards use
    `.home-news-card`.
  - Featured news image overlay is normalized via
    `.home-news-featured-overlay` (prevents legacy green tint in dark mode).
  - Shop preview cards use `.home-shop-card`; product price uses
    `.home-shop-price` for dark-mode contrast tokening.
  - Keep these classes if card markup is edited; dark-mode palette is applied
    in `templates/core/base.html` through these hooks.
- Portfolio dark-mode text contract:
  - `templates/core/portfolio.html` uses `.portfolio-page .portfolio-muted-note`
    for the subtitle under the main H1 (`portfolio_subtitle`); in dark mode this
    is intentionally the same soft-contrast token as homepage muted notes.
  - `templates/core/portfolio_gallery.html` uses
    `.portfolio-gallery-page .portfolio-gallery-subtitle` for card category
    captions (e.g. "Барельеф / медаль", "AI изображение"); in dark mode these
    captions are forced to dark-blue text for contrast on light cards.

### 7.1 i18n (клиентская — `data-i18` в `base.html`)

Сайт не использует Django gettext/`LocaleMiddleware`. Переключение языка
полностью клиентское: `base.html` содержит `const translations = { ru: {...}, en: {...} }`
и функцию `updatePageTranslations()`, которая:

1. **Один обобщённый цикл** пробегает `[data-i18]` и ставит
   `el.textContent = t[key]` (если ключ есть). **Это покрывает все текстовые
   переводы** — больше не нужно добавлять по `querySelectorAll('[data-i18="X"]')`
   на каждый новый ключ (так было раньше; около 175 строк дубляжа удалено).
2. `[data-i18-placeholder="<key>"]` — `setAttribute("placeholder", t[key])`.
3. `[data-i18-aria-label="<key>"]` — `setAttribute("aria-label", t[key])`.
4. `window.__CART_I18N__` заполняется отдельно (корзина берёт переводы через
   `window.applyCartI18n()`).

Правила при добавлении новой текстовой строки:

- Добавьте **пару** ключей (`ru`+`en`) в `const translations` в `base.html`.
- На элементе поставьте `data-i18="<key>"` и **обязательно** заполните
  русский текст как fallback (SSR-рендер отдаёт русский до старта JS).
- Для input-а placeholder'а — `data-i18-placeholder="<key>"` + `placeholder="..."`
  в атрибуте для SSR.
- Для icon-кнопок — `data-i18-aria-label="<key>"` + `aria-label="..."`.
- Ключ помещайте в обе локали. Если какой-то ключ существует только в `ru`,
  JS просто оставит русский текст в en-режиме (`if (key && t[key])` skip).

**Не добавляйте** ручные `document.querySelectorAll('[data-i18="X"]').forEach(el => el.textContent = t.X)`
в `updatePageTranslations()` — обобщённый цикл уже делает это. Любой такой
код — дубляж, мы его вычистили (см. историю `base.html`).

### 7.2 Шаблоны профиля и `_form_field.html`

`templates/core/_form_field.html` — универсальный рендер одного поля
Django-формы. Параметры (передаются через `{% include ... with ... %}`):

| Параметр     | Что делает |
|--------------|------------|
| `field`      | сам bound-field (обязателен) |
| `help`       | статическая подсказка под полем (перезаписывает `field.help_text`) |
| `help_i18`   | ключ в `translations` (`base.html`). Рендерится как `data-i18="<key>"`, JS подменяет при смене языка. Можно комбинировать с `help` (тогда `help` — это ru-fallback). |
| `as_checkbox`| truthy → inline-разметка для чекбокса |

`profile*.html` используют `data-i18` для всех chrome-текстов (заголовки,
section-labels, кнопки, help-тексты) и `help_i18` для подсказок у полей.
**Русский fallback обязателен прямо в разметке**, чтобы SSR возвращал
полноценную русскую страницу без JS. Field-лейблы приходят из
`Model._meta.verbose_name` (русские) и остаются русскими на en-локали —
полный перевод лейблов потребовал бы Django gettext, что выходит за
рамки нынешней клиентской i18n-схемы.

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
| `*_POST_LIMIT`, `*_WINDOW_SECONDS`, `CHECKOUT_IDEMPOTENCY_TTL_SECONDS`, `CHECKOUT_IDEMPOTENCY_SESSION_KEY` | Abuse-protection tuning (contact/auth/cart/checkout throttles + idempotency retention/session key name). See `.env.example` keys. |
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

`scripts/update-safe.sh` wraps `update.sh` with a pre-deploy backup of the prod
PostgreSQL database (`pg_dump -Fc` to `/var/backups/creativesphere/db-<ts>.dump`,
keeping the last 30) and a JSON snapshot of `core.NewsArticle` in the same
directory. Prefer it over bare `update.sh` whenever content might have been
edited via Django admin between deploys (see §11 "Content vs code" rule).

---

## 10. Tests (`core/tests.py`) — **use these as the contract**

109 tests. Run with:

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
| `ShopDataTests` | Форма словарей, уникальность id, `get_product` (включая отбраковку черновиков), превью без sold-out, `get_free_products`. |
| `ProductModelTests` | `price_cents`/`price_display`, `is_purchasable` (с учётом placeholder), `all_image_paths`, `as_cart_dict` (sold-out + placeholder). Фичу placeholder прикрывают `test_is_purchasable_respects_flags` и `test_placeholder_product_not_for_sale_and_image_optional`. |
| `ProductAdminTests` | Публикация `Product.is_published=True` — только superuser/Editors; staff может сохранять черновик. |
| `ShopFreeViewsTests` | `/shop/` и `/free_models/` рендерят посеянных товаров, табы всегда присутствуют, external-download URL остаётся как есть, sold-out отключает кнопку, непубликованные не видны. Placeholder-продукт рендерится как `.free-placeholder-card`, в корзину не попадает. |
| `PortfolioGalleryDataTests` | `gallery_context` for known/unknown slugs. |
| `CartUtilsTests` | Add/set/remove/clear, sort order, malformed session data. Uses a `dict` subclass that accepts `.modified = True`. |
| `ModelTests` | `__str__`s + `OrderItem.total_cents`. |
| `FormTests` | Contact / Checkout (pd_consent mandatory) / Register (duplicate email, email lowercased). |
| `PricingExtrasTemplateTagTests` | `\|rub_minor`. |
| `ArticleExtrasTemplateTagTests` | `\|render_article_body` — headings, ordered & unordered lists, inline images, bold / italic, safe links (and rejection of `javascript:`), HTML escaping. |
| `SeoTests` | Defaults, overrides, JSON-LD structure, HTML-closer escaping, `lru_cache` behavior, `PUBLIC_SITE_URL`, lazy context processor. |
| `StaticPagesViewTests` | Every public page renders 200; portfolio redirects; robots.txt and sitemap; 404 catch-all. |
| `CartApiTests` | Full GET/POST add/set/remove/clear + all 400 error paths + `429 rate_limited` branch. |
| `ContactFormSubmissionTests` | Happy path + invalid form + SMTP failure path. |
| `CheckoutFlowTests` | Empty cart redirect, full POST creates `Order` + items + email + clears cart, pd_consent blocks, idempotency-key repeat does not create duplicate order. |
| `AuthViewTests` | Login by username/email, wrong password, authenticated redirect, logout, registration gated, `?next=` open-redirect guard. |

---

## 11. Conventions & gotchas

- **AGENTS.md update discipline**: after each successful iteration/task, update
  this file if anything changed in architecture, module ownership, URL map,
  templates/i18n contracts, permissions, tests coverage, or operational rules.
  If nothing changed materially, no update is required.
- **Money = integer kopecks** (minor units). Never store floats. Format with
  `format_minor_as_rub` / `|rub_minor`.
- **URL building**: always `reverse("core:<name>", kwargs={...})`. The catch-all
  means a typo does not 404 the resolver — it renders the 404 template.
- **SEO**: don't hard-code meta tags in templates; extend `PAGE_SEO` or override
  via `get_seo(...)`. Base template reads every field it needs.
- **Cart**: mutate through `cart_utils.*` so `session.modified = True` is set
  correctly and unknown product ids are filtered.
- **Gradient fallback gotchas** (`templates/core/base.html`):
  - Runtime feature-detection adds either `can-clip-text` or `no-clip-text` to
    `<html>`; keep this detection in `<head>` so first paint is stable.
  - In `no-clip-text` mode the hero gradient words are rendered as many
    `.gradient-char` spans. This can affect CSS selectors targeting raw text
    nodes or scripts that expect `el.firstChild` to be a text node.
  - If the hero heading starts stuttering on low-end phones, tune
    `@keyframes gradientCharFlow` duration and per-char delay before changing
    the fallback architecture.
- **Abuse controls**:
  - POST endpoints with side effects are IP-throttled in `core/views.py` via
    `_is_rate_limited(...)` (contact form, auth form submits, cart API POST,
    checkout POST).
  - Preserve `429` behavior contracts (`{"error":"rate_limited"}` for JSON API,
    status-429 page render + message for HTML forms).
  - Checkout uses idempotency keys (`idempotency_key` form field or
    `X-Idempotency-Key`) to collapse accidental duplicate submits/retries into
    one order.
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
- **Shared front-end pagination helpers** live in `static/js/enhancements.js`
  as `window.PaginationUtils`:
  - `buildRowAlignedWindows(totalItems, targetPerPage, rowLcm)` — page windows
    with row-filling from next page start when possible.
  - `renderNumberedPager(host, {current,total,makeHref|onNavigate})` — unified
    shop/free_models pager rendering.
  Do not re-implement pager math in templates; call helper from inline scripts.
- **Don't regress `core/seo.py` performance**: shallow copy + `lru_cache` are
  intentional. The `SeoTests` suite will catch accidental breakages.
- **News articles are DB-backed (`NewsArticle`).** Create/edit from Django admin.
  Public list/detail pages read only `status=published`; staff can preview draft
  detail pages. For a richer snippet in SERP/OG, add optional per-slug overrides
  in `core/seo.py::NEWS_ARTICLE_SEO` (title/description/keywords/og_image/article_ld).

  Hero / in-body images for news articles currently live under
  `static/images/news/` (see `gener1..gener8`, `Artcam2..4`, `model*`, `AI*`
  naming conventions).

- **Content vs code rule (don't clobber admin edits on prod).** Articles live in
  two places: the production PostgreSQL DB (filled via Django admin) and the git
  repo (initial seed in `core/migrations/0007_seed_news_articles.py`, later
  reformats in `0008/0009/0010`). **Data migrations must never unconditionally
  `.update()` a field that could have been hand-edited on prod.** The safe
  patterns are:
  - `get_or_create` / `update_or_create(defaults={...})` **only on first seed**
    (by slug).
  - For later schema-neutral content fixes (like `0010_restore_full_news_content`),
    gate every `.update()` on a legacy-content check — e.g. skip if
    `len(existing.content) > LEGACY_SEED_LIMIT` **and** it doesn't already
    match the target. That migration is the reference pattern; copy its
    guard when writing similar ones.
  - New articles should be added **via Django admin in production**, not via
    migrations. Use migrations/commands only for the initial baseline that
    should ship with a fresh install.
  - Always deploy with `scripts/update-safe.sh` (pg_dump + news JSON snapshot
    before `migrate`) so an accidental clobber can be reverted from
    `/var/backups/creativesphere/`.

- **То же правило — для `Product` (товары магазина и бесплатные модели).**
  Каталог лежит в таблице `core_product`, и редакторы правят его через админку.
  Data-миграции должны быть идемпотентны и никогда не затирать админские
  правки:
  - Первичный посев `core/migrations/0012_seed_products.py` использует
    `get_or_create(pk=…, defaults={...})` — если запись с таким `id`
    уже есть в прод-БД (например, `id=1..14` из легаси-магазина),
    миграция её не трогает.
  - Доп. ракурсы (`ProductImage`) добавляются только если у товара ещё нет
    ни одного ракурса — чтобы при повторном прогоне не клонировать их.
  - Placeholder-карточки «Скоро» посеяны отдельной миграцией
    `0015_seed_placeholder_products.py` (id 201..299, зарезервированный
    коридор). Тот же паттерн `get_or_create(pk=…)` + обновление
    Postgres-sequence. Дополнительные placeholder'ы заводятся через
    админку (`Product.is_placeholder=True`), а не миграциями.
  - Новые товары/модели добавляются **через админку**, а не через миграции.
  - После массового `INSERT ... (id=…)` Postgres-последовательность
    выставляется через `setval(pg_get_serial_sequence(...), MAX(id), true)` —
    иначе следующий admin-товар получит конфликт по первичному ключу.
  - `scripts/update-safe.sh` делает `pg_dump` **всей** БД перед миграцией,
    так что `core_product` тоже покрыт бэкапом.
  - Порядок табов на `/free_models/` определяется **порядком enum-членов**
    `Product.FreeCategory` (не полем `display_order`). `views.free_models`
    строит табы через `for key, label in FreeCategory.choices`, поэтому
    изменение порядка в модели == изменение порядка табов (см.
    `0014_reorder_free_categories`). Django генерирует на это миграцию
    (`AlterField` для `choices`), схема БД при этом не меняется.

---

## 12. Quick "I need to change X" cheat sheet

| I want to… | Edit |
|---|---|
| Add a product | Создайте `Product` в Django admin (`kind=shop`, заполните title/slug/image/alt/price_rub/description; при необходимости добавьте доп. ракурсы через инлайн `ProductImage`). Публиковать (`is_published=True`) может только superuser или группа Editors. Код трогать не нужно. |
| Add a free model | То же, но `kind=free`, `price_rub=0`, выбрать `free_category` (`hobby`/`art`/`tech`) — именно этот таб будет содержать карточку. В `download_url` — полный `https://…`-URL или путь `files/free/xxx.zip` (последний прогонится через `{% static %}`). |
| Mark a product as "Распродано" | Включить `is_sold_out` на карточке в админке. Кнопка «Купить/Скачать» станет неактивной, `cart_utils.add_item` такие товары больше не добавит. |
| Add a «Скоро» placeholder-card | Создайте `Product` и включите `is_placeholder` (раздел «Публикация»). Можно оставить `image`/`description`/`download_url` пустыми. Карточка отрисуется как `free-placeholder-card` в шаблонах `shop.html`/`free_models.html`, не попадёт в корзину и исчезнет, как только вы снимете галочку `is_placeholder` и заполните остальные поля. |
| Edit free downloads section/page | Контент — через админку (`Product`, в т.ч. placeholder'ы). Вёрстка табов/карточек — `templates/core/free_models.html`; общие стили placeholder + pagination — `static/css/enhancements.css`; общая логика пагинации — `static/js/enhancements.js` (`window.PaginationUtils`). Список и **порядок** табов определяется `Product.FreeCategory.choices` в `core/models.py` (после правки — `makemigrations`, получится `AlterField` без изменения схемы). Перевод названий табов — ключи `shop_free_tab_art`/`_hobby`/`_tech` в `base.html::translations.ru/en`; шаблон подставляет их через `data-i18="shop_free_tab_{{ tab.key }}"`. SEO — `core/seo.py::PAGE_SEO["free_models"]`. |
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
