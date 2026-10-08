import pytest
from cryptography.fernet import Fernet
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.administration.models import ApplicationConfiguration
from apps.common.crypto import decrypt_json, encrypt_json
from apps.families.tests.factories import FamilyFactory

pytestmark = pytest.mark.django_db


def test_browser_preflight_allows_the_request_id_header():
    response = APIClient().options(
        reverse("health"),
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,x-request-id",
    )
    assert response.status_code == 200
    assert "x-request-id" in response["Access-Control-Allow-Headers"]


def test_health_is_public():
    response = APIClient().get(reverse("health"))
    assert response.status_code == 200
    assert response.data["data"]["database"] == "ok"


def test_metrics_require_staff():
    user = UserFactory(password="Str0ng!Pass1")
    client = APIClient()
    login = client.post(
        reverse("accounts:login"),
        {"identifier": user.email, "password": "Str0ng!Pass1"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['data']['tokens']['access']}")
    assert client.get(reverse("metrics")).status_code == 403


@override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
def test_provider_secrets_are_encrypted_at_rest():
    family = FamilyFactory()
    config = ApplicationConfiguration.objects.create(
        family=family, email_config={"api_key": "secret-value"}
    )
    config.refresh_from_db()
    assert "secret-value" not in str(config.email_config)
    assert decrypt_json(config.email_config)["api_key"] == "secret-value"
    assert encrypt_json({}) == {}


def test_rate_limited_requests_return_429_not_403():
    """django-ratelimit's Ratelimited subclasses PermissionDenied.

    Without an explicit translation DRF reports 403, which tells the client the
    request is forbidden forever instead of "slow down". Clients that branch on
    429 (and read Retry-After) would back off incorrectly.
    """
    from django_ratelimit.exceptions import Ratelimited
    from rest_framework.test import APIRequestFactory

    from apps.common.exceptions import custom_exception_handler

    request = APIRequestFactory().post("/api/v1/auth/login/")
    response = custom_exception_handler(Ratelimited("blocked"), {"request": request, "view": None})

    assert response is not None
    assert response.status_code == 429
    assert response["Retry-After"] == "60"
    assert response.data["errors"]["code"] == "rate_limited"
    assert response.data["success"] is False


def test_login_throttle_surfaces_as_429(settings):
    """End-to-end: a blocked login must not look like a permission problem."""
    settings.RATELIMIT_ENABLE = True
    client = APIClient()

    statuses = [
        client.post(
            reverse("accounts:login"),
            {"identifier": "nobody@example.com", "password": "WrongPass!123"},
            format="json",
        ).status_code
        for _ in range(12)
    ]

    assert 401 in statuses, "bad credentials should be 401 before the limit trips"
    assert 429 in statuses, f"expected a 429 once the limit trips, saw {statuses}"
    assert 403 not in statuses, f"a rate limit must never be reported as 403: {statuses}"


def test_api_responses_carry_a_content_security_policy(settings):
    """A SaaS handling family finances must not run injected script.

    The API returns JSON, so the policy can be near-maximally strict: no
    scripts, no frames, no third-party origins except PostHog when configured.
    """
    settings.DEBUG = False
    settings.POSTHOG_HOST = "https://us.i.posthog.com"

    response = APIClient().get(reverse("health"))

    csp = response["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "https://us.i.posthog.com" in csp


def test_content_security_policy_can_be_disabled(settings):
    """Operators behind a proxy that sets its own CSP can switch this off."""
    settings.DEBUG = False
    settings.CONTENT_SECURITY_POLICY = ""

    response = APIClient().get(reverse("health"))

    assert "Content-Security-Policy" not in response


def test_debug_does_not_emit_a_breaking_content_security_policy(settings):
    """Vite injects inline scripts in dev; a strict CSP there would blank the app."""
    settings.DEBUG = True

    response = APIClient().get(reverse("health"))

    assert "Content-Security-Policy" not in response


def test_security_headers_present_on_every_response():
    response = APIClient().get(reverse("health"))

    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"
