"""
Django settings for CreativeSphere project.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = os.getenv('DEBUG', '1') == '1'


def _parse_domain_list(raw: str) -> list[str]:
    return [p.strip().lower() for p in raw.split(',') if p.strip()]


# Production apex hostnames (comma-separated). Used for ALLOWED_HOSTS / CSRF when not overridden.
# Default serves trally.ru now and kurilenkoart.ru when DNS points here.
_DEFAULT_SITE_DOMAINS = 'trally.ru,kurilenkoart.ru'

_site_domains_raw = os.getenv('DJANGO_SITE_DOMAINS', '').strip()
if _site_domains_raw:
    SITE_DOMAINS = _parse_domain_list(_site_domains_raw)
elif DEBUG:
    SITE_DOMAINS = []
else:
    SITE_DOMAINS = _parse_domain_list(os.getenv('DJANGO_SITE_DOMAINS_DEFAULT', _DEFAULT_SITE_DOMAINS))

# Primary apex: canonical URLs / legacy PRIMARY_DOMAIN. Prefer DJANGO_CANONICAL_DOMAIN, else first in SITE_DOMAINS, else trally.ru.
_canonical_apex = os.getenv('DJANGO_CANONICAL_DOMAIN', '').strip().lower()
if _canonical_apex:
    PRIMARY_DOMAIN = _canonical_apex
elif SITE_DOMAINS:
    PRIMARY_DOMAIN = SITE_DOMAINS[0]
else:
    PRIMARY_DOMAIN = os.getenv('DJANGO_PRIMARY_DOMAIN', 'trally.ru').strip().lower() or 'trally.ru'

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
SEO_DEFAULT_OG_IMAGE = os.getenv('SEO_DEFAULT_OG_IMAGE', 'images/news/bas-relief-depth-1920x1200.png').strip()
SEO_CONTACT_EMAIL = os.getenv('SEO_CONTACT_EMAIL', 'hello@creativesphere.art').strip()

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
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_seo',
                'core.context_processors.shop_cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'creativesphere.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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
