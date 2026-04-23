"""
Django settings for CreativeSphere project.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = os.getenv('DEBUG', '1') == '1'


def _parse_domain_list(raw: str) -> list[str]:
    return [p.strip().lower() for p in raw.split(',') if p.strip()]


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(minimum, value)


# Production apex hostnames (comma-separated). Used for ALLOWED_HOSTS / CSRF when not overridden.
_DEFAULT_SITE_DOMAINS = 'kurilenkoart.ru'

_site_domains_raw = os.getenv('DJANGO_SITE_DOMAINS', '').strip()
if _site_domains_raw:
    SITE_DOMAINS = _parse_domain_list(_site_domains_raw)
elif DEBUG:
    SITE_DOMAINS = []
else:
    SITE_DOMAINS = _parse_domain_list(os.getenv('DJANGO_SITE_DOMAINS_DEFAULT', _DEFAULT_SITE_DOMAINS))

# Primary apex: canonical URLs / legacy PRIMARY_DOMAIN. Prefer DJANGO_CANONICAL_DOMAIN, else first in SITE_DOMAINS, else kurilenkoart.ru.
_canonical_apex = os.getenv('DJANGO_CANONICAL_DOMAIN', '').strip().lower()
if _canonical_apex:
    PRIMARY_DOMAIN = _canonical_apex
elif SITE_DOMAINS:
    PRIMARY_DOMAIN = SITE_DOMAINS[0]
else:
    PRIMARY_DOMAIN = os.getenv('DJANGO_PRIMARY_DOMAIN', 'kurilenkoart.ru').strip().lower() or 'kurilenkoart.ru'

WWW_HOST = os.getenv('DJANGO_WWW_HOST', f'www.{PRIMARY_DOMAIN}').strip() or f'www.{PRIMARY_DOMAIN}'

_allowed = os.getenv('ALLOWED_HOSTS', '').strip()
if _allowed:
    ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',') if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    if SITE_DOMAINS:
        ALLOWED_HOSTS = []
        for apex in SITE_DOMAINS:
            ALLOWED_HOSTS.append(apex)
            ALLOWED_HOSTS.append(f'www.{apex}')
        ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))
        for _local in ('127.0.0.1', 'localhost'):
            if _local not in ALLOWED_HOSTS:
                ALLOWED_HOSTS.append(_local)
    else:
        ALLOWED_HOSTS = [PRIMARY_DOMAIN, WWW_HOST]

_csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '').strip()
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
elif DEBUG:
    CSRF_TRUSTED_ORIGINS = []
else:
    if SITE_DOMAINS:
        CSRF_TRUSTED_ORIGINS = []
        for apex in SITE_DOMAINS:
            CSRF_TRUSTED_ORIGINS.append(f'https://{apex}')
            CSRF_TRUSTED_ORIGINS.append(f'https://www.{apex}')
        CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))
    else:
        CSRF_TRUSTED_ORIGINS = [
            f'https://{PRIMARY_DOMAIN}',
            f'https://{WWW_HOST}',
        ]

# Canonical / absolute URLs for SEO, OG tags, robots Sitemap line (no trailing slash).
_public = os.getenv('PUBLIC_SITE_URL', '').strip().rstrip('/')
if _public:
    PUBLIC_SITE_URL = _public
elif not DEBUG:
    PUBLIC_SITE_URL = f'https://{PRIMARY_DOMAIN}'
else:
    PUBLIC_SITE_URL = ''

SEO_SITE_NAME = os.getenv('SEO_SITE_NAME', 'KurilenkoArt').strip() or 'KurilenkoArt'
SEO_DEFAULT_OG_IMAGE = os.getenv('SEO_DEFAULT_OG_IMAGE', 'images/news/model5.jpg').strip()
SEO_CONTACT_EMAIL = os.getenv('SEO_CONTACT_EMAIL', 'me@nobito.ru').strip() or 'me@nobito.ru'

# Yandex.Metrica and Top.Mail.ru counters (numeric IDs). Empty = disabled. Override in .env if needed.
YANDEX_METRIKA_ID = os.getenv('YANDEX_METRIKA_ID', '103952385').strip()
MAILRU_TOP_ID = os.getenv('MAILRU_TOP_ID', '').strip()

# Outbound email (SMTP or compatible transactional provider). Dev default: print to console.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend',
).strip()
EMAIL_HOST = os.getenv('EMAIL_HOST', '').strip()
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587').strip() or '587')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1').strip() != '0'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', '0').strip() == '1'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '').strip()
DEFAULT_FROM_EMAIL = (os.getenv('DEFAULT_FROM_EMAIL', '') or SEO_CONTACT_EMAIL).strip()
# Where contact form submissions are delivered (inbox you monitor).
CONTACT_FORM_RECIPIENT = (os.getenv('CONTACT_FORM_RECIPIENT', '') or SEO_CONTACT_EMAIL).strip()
# If true, also attempt SMTP/console notification after saving to the database (failures are logged only).
CONTACT_FORM_TRY_EMAIL = os.getenv('CONTACT_FORM_TRY_EMAIL', '1').strip() == '1'

# Abuse protection / throttling (cache-backed in core.views)
CONTACT_FORM_POST_LIMIT = _env_int("CONTACT_FORM_POST_LIMIT", 5)
CONTACT_FORM_WINDOW_SECONDS = _env_int("CONTACT_FORM_WINDOW_SECONDS", 600)
AUTH_POST_LIMIT = _env_int("AUTH_POST_LIMIT", 20)
AUTH_WINDOW_SECONDS = _env_int("AUTH_WINDOW_SECONDS", 300)
CART_API_POST_LIMIT = _env_int("CART_API_POST_LIMIT", 120)
CART_API_WINDOW_SECONDS = _env_int("CART_API_WINDOW_SECONDS", 60)
CHECKOUT_POST_LIMIT = _env_int("CHECKOUT_POST_LIMIT", 8)
CHECKOUT_WINDOW_SECONDS = _env_int("CHECKOUT_WINDOW_SECONDS", 600)
CHECKOUT_IDEMPOTENCY_TTL_SECONDS = _env_int("CHECKOUT_IDEMPOTENCY_TTL_SECONDS", 60 * 60 * 24)
CHECKOUT_IDEMPOTENCY_SESSION_KEY = (
    os.getenv("CHECKOUT_IDEMPOTENCY_SESSION_KEY", "checkout_idempotency_key").strip()
    or "checkout_idempotency_key"
)

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Redirect HTTP→HTTPS (requires proxy to set X-Forwarded-Proto: https).
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', '1').strip() != '0'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    _hsts = int(os.getenv('SECURE_HSTS_SECONDS', '31536000').strip() or '0')
    SECURE_HSTS_SECONDS = max(0, _hsts)
    if SECURE_HSTS_SECONDS:
        SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', '1').strip() == '1'
        SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', '0').strip() == '1'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'creativesphere.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            "libraries": {
                "article_extras": "core.templatetags.article_extras",
            },
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_seo',
                'core.context_processors.analytics',
                'core.context_processors.shop_cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'creativesphere.wsgi.application'

# --- Database: PostgreSQL on VPS (recommended) or SQLite (default / dev) ---
# Postgres lives outside the git tree; only credentials in .env — pull never touches the DB file.
_pg_flag = os.getenv("DJANGO_DATABASE", "").strip().lower() in (
    "postgres",
    "postgresql",
    "pgsql",
)
if _pg_flag:
    _pg_db = os.getenv("POSTGRES_DB", "").strip()
    _pg_user = os.getenv("POSTGRES_USER", "").strip()
    _pg_pass = os.getenv("POSTGRES_PASSWORD", "").strip()
    _pg_host = os.getenv("POSTGRES_HOST", "localhost").strip() or "localhost"
    _pg_port = os.getenv("POSTGRES_PORT", "5432").strip() or "5432"
    if not _pg_db or not _pg_user:
        raise ImproperlyConfigured(
            "DJANGO_DATABASE=postgresql set but POSTGRES_DB or POSTGRES_USER is empty. "
            "See .env.example."
        )
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _pg_db,
            "USER": _pg_user,
            "PASSWORD": _pg_pass,
            "HOST": _pg_host,
            "PORT": _pg_port,
            "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60").strip() or "60"),
        }
    }
else:
    # SQLite: по умолчанию файл в каталоге проекта. На VPS можно DJANGO_SQLITE_PATH вне репо.
    _sqlite_env = os.getenv("DJANGO_SQLITE_PATH", "").strip()
    if _sqlite_env:
        _db_file = Path(_sqlite_env).expanduser()
    else:
        _db_file = BASE_DIR / "db.sqlite3"
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(_db_file),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

LOGIN_URL = '/sign-up-login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Registration UI on /sign-up-login/ (Sign up link + form). Set AUTH_SHOW_REGISTRATION=1 in .env to show again.
AUTH_SHOW_REGISTRATION = os.getenv('AUTH_SHOW_REGISTRATION', '0').strip() == '1'
