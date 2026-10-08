"""Object storage for uploaded media.

Django's default FileSystemStorage writes to MEDIA_ROOT, which is fine on a
server with a real disk but is lost on every deploy on a container platform
whose filesystem is ephemeral. Uploaded family documents and profile photos
are user data, so production must point MEDIA at object storage.

Configured entirely through the environment; when the four AWS_* values below
are absent the default filesystem storage is used, so local development and the
test suite keep working with no extra service. Any S3-compatible provider
works — Cloudflare R2, Backblaze B2, Supabase Storage, MinIO, or real S3.

    AWS_STORAGE_BUCKET_NAME=familynexus-media
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    AWS_S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com   # optional
    AWS_S3_REGION_NAME=auto                                          # optional
    AWS_S3_CUSTOM_DOMAIN=cdn.example.com                             # optional
"""

import logging

logger = logging.getLogger(__name__)

REQUIRED_FOR_OBJECT_STORAGE = (
    "AWS_STORAGE_BUCKET_NAME",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
)


def object_storage_settings(env) -> dict:
    """Return the STORAGES override for media, or {} to keep the local disk.

    `env` is any mapping-like getter, usually decouple's config(). It is
    injected so this can be unit tested without touching the real environment.
    """
    values = {key: (env(key, default="") or "") for key in REQUIRED_FOR_OBJECT_STORAGE}
    missing = [key for key, value in values.items() if not value]

    if missing:
        # Partly-configured credentials are the dangerous case: a typo in one
        # variable would silently fall back to an ephemeral disk and uploads
        # would start disappearing on the next deploy. Say so loudly.
        if len(missing) < len(REQUIRED_FOR_OBJECT_STORAGE):
            logger.error(
                "Object storage is only partly configured; missing %s. "
                "Falling back to local disk, which loses uploads on redeploy.",
                ", ".join(missing),
            )
        return {}

    options = {
        "bucket_name": values["AWS_STORAGE_BUCKET_NAME"],
        "access_key": values["AWS_ACCESS_KEY_ID"],
        "secret_key": values["AWS_SECRET_ACCESS_KEY"],
        # Media URLs are served from the bucket/CDN; never append a query
        # signature to a public URL or every response becomes uncacheable and
        # the links leak credentials.
        "querystring_auth": False,
        "file_overwrite": False,
        "default_acl": None,
    }

    for env_key, option in (
        ("AWS_S3_ENDPOINT_URL", "endpoint_url"),
        ("AWS_S3_REGION_NAME", "region_name"),
        ("AWS_S3_CUSTOM_DOMAIN", "custom_domain"),
    ):
        value = env(env_key, default="") or ""
        if value:
            options[option] = value

    return {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
        "media": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": options,
        },
    }
