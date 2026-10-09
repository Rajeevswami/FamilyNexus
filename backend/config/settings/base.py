"""
Base settings shared across all environments.
Environment-specific overrides live in development.py / production.py.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from corsheaders.defaults import default_headers
from decouple import Csv, config

from apps.common.storage import object_storage_settings
from config import product

PRODUCT_NAME = product.PRODUCT_NAME
PRODUCT_SLUG = product.PRODUCT_SLUG
PRODUCT_DOMAIN = product.PRODUCT_DOMAIN
PLACEHOLDER_EMAIL_DOMAIN = product.PLACEHOLDER_EMAIL_DOMAIN

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
TESTING = config("TESTING", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
]

# Local apps are registered here as they are built, module by module.
# apps.common is a utility package (response/exceptions/permissions/etc.)
# and intentionally NOT registered — it has no models or migrations.
# NOTE: apps.accounts will hold the custom UUID-based User model — it
# MUST land before the first migration, since AUTH_USER_MODEL cannot be
# swapped after that without a manual data migration.
LOCAL_APPS: list[str] = [
    "apps.accounts",
    "apps.families",
    "apps.households",
    "apps.members",
    "apps.expenses",
    "apps.income",
    "apps.loans",
    "apps.borrow_lend",
    "apps.ledger",
    "apps.transactions",
    "apps.documents",
    "apps.reports",
    "apps.notifications",
    "apps.dashboard",
    "apps.audit",
    "apps.administration",
    "apps.billing",
    "apps.privacy",
    "apps.referrals",
    "apps.onboarding",
    "apps.flags",
    "apps.assistant",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "apps.common.middleware.observability.RequestObservabilityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.observability.SecurityHeadersMiddleware",
    "apps.common.middleware.conditional_get.ConditionalGetMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database (Postgres — configured per environment via DATABASE_URL parts)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=(
            f"postgresql://"
            f"{config('DB_USER', default=PRODUCT_SLUG)}:"
            f"{config('DB_PASSWORD', default='')}@"
            f"{config('DB_HOST', default='localhost')}:"
            f"{config('DB_PORT', default='5432')}/"
            f"{config('DB_NAME', default=PRODUCT_SLUG)}"
        ),
        conn_max_age=60,
        conn_health_checks=True,
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth / Password hashing (Argon2 first, per security requirements)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.PasswordComplexityValidator"},
]

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "apps.common.openapi.FamilyNexusAutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "600/hour",
        "anon": "60/hour",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": f"{PRODUCT_NAME} API",
    "DESCRIPTION": (
        "Connecting Families Through Financial Transparency. "
        "JSON responses use {success, message, data} plus optional pagination meta. "
        "File exports and the simplejwt refresh endpoint are not enveloped."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_AUTHENTICATION": [],
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "apps.common.openapi.postprocess_schema",
    ],
}

# ---------------------------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------------------------
# Platform health checkers (Render, Fly, Kubernetes probes) connect straight to
# the container and do not always send X-Forwarded-Proto. With
# SECURE_SSL_REDIRECT on in production that would become a 301 and the deploy
# would be marked unhealthy even though the app is fine. The endpoint returns no
# user data, so answering it over plain HTTP exposes nothing. Inert outside
# production because SECURE_SSL_REDIRECT is False there.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:5173", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="http://localhost:5173", cast=Csv())
# SPA sends X-Request-ID. corsheaders defaults omit it, so browser preflight fails.
CORS_ALLOW_HEADERS = (*default_headers, "x-request-id")

# ---------------------------------------------------------------------------
# Redis / Celery
# ---------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_BEAT_SCHEDULE = {
    "weekly-family-summary": {
        "task": "apps.assistant.tasks.send_weekly_family_summaries",
        "schedule": 60 * 60 * 24 * 7,
    }
}

CACHE_MIDDLEWARE_SECONDS = 60
CACHE_MIDDLEWARE_KEY_PREFIX = PRODUCT_SLUG

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": PRODUCT_SLUG,
    }
}

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Uploaded media goes to S3-compatible object storage when AWS_STORAGE_BUCKET_NAME
# / AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are set. Without them the local
# disk is used, which is correct for development and for tests. On a container
# platform with an ephemeral filesystem, leaving these unset means every
# uploaded document and avatar is deleted on the next deploy — see
# docs/DEPLOY_FREE.md.
_object_storage = object_storage_settings(config)
if _object_storage:
    STORAGES = _object_storage
    MEDIA_URL = config("AWS_MEDIA_URL", default=f"{MEDIA_URL}")

# ---------------------------------------------------------------------------
# Email — console backend for now; swapped to a real provider (SES/SendGrid/
# etc.) via EMAIL_BACKEND override in an environment-specific settings file
# once a provider is chosen. Templates already exist under templates/emails/.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default=f"{PRODUCT_NAME} <no-reply@{PRODUCT_DOMAIN}>",
)

# ---------------------------------------------------------------------------
# Auth-specific application settings
# ---------------------------------------------------------------------------
PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 30
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")

STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_PRICE_IDS = {
    "family": config("STRIPE_FAMILY_PRICE_ID", default=""),
    "premium": config("STRIPE_PREMIUM_PRICE_ID", default=""),
}
RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = config("RAZORPAY_WEBHOOK_SECRET", default="")
EMAIL_PROVIDER = config("EMAIL_PROVIDER", default="console")
SENDGRID_API_KEY = config("SENDGRID_API_KEY", default="")
FIELD_ENCRYPTION_KEY = config("FIELD_ENCRYPTION_KEY", default="")
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL = config("ANTHROPIC_MODEL", default="claude-sonnet-4-5")
POSTHOG_API_KEY = config("POSTHOG_API_KEY", default="")
POSTHOG_HOST = config("POSTHOG_HOST", default="https://us.i.posthog.com")
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_WEBHOOK_SECRET = config("TELEGRAM_WEBHOOK_SECRET", default="")
WHATSAPP_VERIFY_TOKEN = config("WHATSAPP_VERIFY_TOKEN", default="")
WHATSAPP_APP_SECRET = config("WHATSAPP_APP_SECRET", default="")
VAULT_ADDR = config("VAULT_ADDR", default="")
VAULT_TOKEN = config("VAULT_TOKEN", default="")

# ---------------------------------------------------------------------------
# Logging — separate rotating files for app, error, and security events
# ---------------------------------------------------------------------------
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {module}.{funcName}:{lineno} — {message}",
            "style": "{",
        },
        "simple": {"format": "{asctime} {levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "error.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "level": "ERROR",
            "formatter": "verbose",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "security.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "app_file"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console", "app_file"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["error_file"], "level": "ERROR", "propagate": False},
        "django.security": {
            "handlers": ["security_file", "console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps.errors": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps.security": {
            "handlers": ["security_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
