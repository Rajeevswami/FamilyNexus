"""
Custom DRF exception handler.

Wraps every error response (validation, permission, auth, throttling,
uncaught 500s) into the same envelope shape as success_response(), and
logs unexpected exceptions to the security/error log.
"""

import logging

from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("apps.errors")


# Seconds a client should wait before retrying a login/register style endpoint.
# Only used to fill Retry-After; the real window is enforced by the cache key.
RATELIMIT_RETRY_AFTER_SECONDS = 60


class ApplicationError(Exception):
    """Base class for domain-level errors raised inside services."""

    def __init__(self, message: str, code: str = "application_error", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def custom_exception_handler(exc, context):
    if isinstance(exc, ApplicationError):
        return Response(
            {"success": False, "message": exc.message, "errors": {"code": exc.code}},
            status=exc.status_code,
        )

    # django-ratelimit raises Ratelimited, which subclasses Django's
    # PermissionDenied. DRF therefore turns it into a 403, hiding the real
    # cause from clients and from logs. Translate it to a proper 429 with
    # Retry-After before DRF can reinterpret it. 403 means "you may never
    # do this"; 429 means "you may, just not this often".
    try:
        from django_ratelimit.exceptions import Ratelimited
    except ImportError:  # pragma: no cover - ratelimit is a hard dependency
        Ratelimited = None

    if Ratelimited is not None and isinstance(exc, Ratelimited):
        logger.warning(
            "Rate limit hit on %s for %s",
            context.get("view"),
            context.get("request").META.get("REMOTE_ADDR") if context.get("request") else "?",
        )
        response = Response(
            {
                "success": False,
                "message": "Too many requests. Please try again shortly.",
                "errors": {"code": "rate_limited"},
            },
            status=429,
        )
        response["Retry-After"] = str(RATELIMIT_RETRY_AFTER_SECONDS)
        return response

    if isinstance(exc, Http404):
        exc = drf_exceptions.NotFound()

    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled exception — log with full context, never leak internals to the client.
        logger.exception("Unhandled exception in %s", context.get("view"), exc_info=exc)
        return Response(
            {"success": False, "message": "Internal server error", "errors": {}},
            status=500,
        )

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
        errors = detail
    elif isinstance(detail, dict):
        # Field/non-field validation errors, e.g. {"non_field_errors": [...]}
        first_key = next(iter(detail))
        first_value = detail[first_key]
        first_message = (
            first_value[0] if isinstance(first_value, list) and first_value else first_value
        )
        message = str(first_message)
        errors = detail
    else:
        message = "Request failed"
        errors = {"detail": detail}

    response.data = {"success": False, "message": message, "errors": errors}
    return response
