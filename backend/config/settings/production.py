"""Production overrides — hardened security defaults."""

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# SECURE_REDIRECT_EXEMPT (the health-check exemption) lives in base.py so the
# test suite can assert it. It is inert while SECURE_SSL_REDIRECT is False.

SENTRY_DSN = config("SENTRY_DSN", default="")

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    integrations = [DjangoIntegration()]
    try:
        from sentry_sdk.integrations.celery import CeleryIntegration

        integrations.append(CeleryIntegration())
    except ImportError:
        pass
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=integrations,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
