import logging
import time
import uuid

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("apps.performance")


class RequestObservabilityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request._started_at = time.perf_counter()

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        started = getattr(request, "_started_at", None)
        if started is not None:
            elapsed = (time.perf_counter() - started) * 1000
            response["X-Response-Time-Ms"] = f"{elapsed:.1f}"
            if elapsed > 500:
                logger.warning(
                    "slow_request request_id=%s path=%s status=%s duration_ms=%.1f",
                    request_id,
                    request.path,
                    response.status_code,
                    elapsed,
                )
        return response


def build_content_security_policy() -> str:
    """CSP for API responses.

    The API is consumed by the React SPA and returns JSON, so the policy can be
    tighter than a server-rendered site: nothing needs to load scripts or frames
    from the API origin. PostHog is the only optional third party and its host is
    read from settings so a self-hosted instance keeps working.

    Set CONTENT_SECURITY_POLICY to override the whole header, or to None/"" to
    turn it off (for example when a proxy already sets one).
    """
    override = getattr(settings, "CONTENT_SECURITY_POLICY", None)
    if override is not None:
        return override

    connect_src = ["'self'"]
    posthog_host = getattr(settings, "POSTHOG_HOST", "") or ""
    if posthog_host.startswith("http"):
        connect_src.append(posthog_host)

    directives = {
        "default-src": ["'none'"],
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "blob:"],
        "font-src": ["'self'", "data:"],
        "connect-src": connect_src,
        "frame-ancestors": ["'none'"],
        "base-uri": ["'none'"],
        "form-action": ["'self'"],
        "object-src": ["'none'"],
    }
    return "; ".join(f"{key} {' '.join(values)}" for key, values in directives.items())


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("Cross-Origin-Resource-Policy", "same-site")

        # Applies to JSON API responses only. The Swagger/ReDoc pages and the
        # Django admin are HTML and load their own inline scripts, so a strict
        # policy there would break them; they are hardened by X-Frame-Options
        # and the admin's own protections instead.
        content_type = response.get("Content-Type", "")
        if content_type.startswith("application/json") and not settings.DEBUG:
            policy = build_content_security_policy()
            if policy:
                response.setdefault("Content-Security-Policy", policy)
        return response
