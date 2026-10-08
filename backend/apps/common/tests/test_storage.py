"""Object storage wiring.

The failure this guards against is silent: if AWS_* keys are missing on a
container platform the app still boots, uploads still appear to succeed, and
every file vanishes on the next deploy. These tests pin the switch so that
behaviour cannot change without a failing test.
"""

import logging

from apps.common.storage import object_storage_settings


def _env(mapping):
    def getter(key, default=""):
        return mapping.get(key, default)

    return getter


def test_local_disk_is_used_when_object_storage_is_not_configured():
    assert object_storage_settings(_env({})) == {}


def test_media_moves_to_s3_when_credentials_are_present():
    storage = object_storage_settings(
        _env(
            {
                "AWS_STORAGE_BUCKET_NAME": "familynexus-media",
                "AWS_ACCESS_KEY_ID": "key",
                "AWS_SECRET_ACCESS_KEY": "secret",
            }
        )
    )

    assert storage["media"]["BACKEND"] == "storages.backends.s3.S3Storage"
    assert storage["media"]["OPTIONS"]["bucket_name"] == "familynexus-media"
    # Static files must stay on WhiteNoise; only user media moves to the bucket.
    assert "whitenoise" in storage["staticfiles"]["BACKEND"]


def test_optional_endpoint_and_custom_domain_are_passed_through():
    storage = object_storage_settings(
        _env(
            {
                "AWS_STORAGE_BUCKET_NAME": "bucket",
                "AWS_ACCESS_KEY_ID": "key",
                "AWS_SECRET_ACCESS_KEY": "secret",
                "AWS_S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
                "AWS_S3_REGION_NAME": "auto",
                "AWS_S3_CUSTOM_DOMAIN": "cdn.example.com",
            }
        )
    )

    options = storage["media"]["OPTIONS"]
    assert options["endpoint_url"] == "https://account.r2.cloudflarestorage.com"
    assert options["region_name"] == "auto"
    assert options["custom_domain"] == "cdn.example.com"


def test_media_urls_are_not_signed():
    """Public media URLs must not carry credentials or they cannot be cached."""
    storage = object_storage_settings(
        _env(
            {
                "AWS_STORAGE_BUCKET_NAME": "bucket",
                "AWS_ACCESS_KEY_ID": "key",
                "AWS_SECRET_ACCESS_KEY": "secret",
            }
        )
    )

    assert storage["media"]["OPTIONS"]["querystring_auth"] is False
    assert storage["media"]["OPTIONS"]["default_acl"] is None


def test_partial_credentials_are_reported_loudly(caplog):
    """A typo in one variable must not look like a working configuration."""
    with caplog.at_level(logging.ERROR, logger="apps.common.storage"):
        storage = object_storage_settings(
            _env({"AWS_STORAGE_BUCKET_NAME": "bucket", "AWS_ACCESS_KEY_ID": "key"})
        )

    assert storage == {}
    assert "AWS_SECRET_ACCESS_KEY" in caplog.text
