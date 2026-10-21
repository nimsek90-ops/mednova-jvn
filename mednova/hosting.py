"""Environment-only hosting configuration. Never contacts providers or runs migrations."""
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured


def storage_config(env, vercel=False):
    backend = env.get("PRIVATE_STORAGE_BACKEND", "filesystem")
    if backend not in ("filesystem", "s3"):
        raise ImproperlyConfigured("PRIVATE_STORAGE_BACKEND must be filesystem or s3.")
    if vercel and backend != "s3":
        raise ImproperlyConfigured("Vercel requires PRIVATE_STORAGE_BACKEND=s3 for durable private reports.")
    storages = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    if backend == "s3":
        required = ("S3_BUCKET_NAME", "S3_REGION_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
        missing = [name for name in required if not env.get(name)]
        if missing:
            raise ImproperlyConfigured("Missing private storage settings: " + ", ".join(missing))
        endpoint = env.get("S3_ENDPOINT_URL") or None
        if endpoint and (urlparse(endpoint).scheme != "https" or not urlparse(endpoint).hostname):
            raise ImproperlyConfigured("S3_ENDPOINT_URL must use HTTPS.")
        storages["default"] = {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": env["S3_BUCKET_NAME"],
                "region_name": env["S3_REGION_NAME"],
                "endpoint_url": endpoint,
                "default_acl": None,
                "querystring_auth": True,
                "querystring_expire": 60,
                "custom_domain": None,
                "signature_version": "s3v4",
                "file_overwrite": False,
                "verify": True,
                "object_parameters": {"CacheControl": "private, no-store"},
            },
        }
    return backend, storages


def validate_vercel(env):
    if env.get("APP_ENV") != "production" or any(env.get(name) for name in ("MEDNOVA_TESTING", "MEDNOVA_TEST_DB", "MEDNOVA_TEST_MYSQL")):
        raise ImproperlyConfigured("Vercel requires APP_ENV=production and no MEDNOVA_TEST* variables.")
    required = ("MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_SSL_CA", "PUBLIC_ORIGIN", "ALLOWED_HOSTS")
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise ImproperlyConfigured("Missing Vercel settings: " + ", ".join(missing))
    if env["MYSQL_HOST"].lower() in ("localhost", "127.0.0.1", "::1"):
        raise ImproperlyConfigured("Vercel requires a remote managed MySQL service.")
    origin = urlparse(env["PUBLIC_ORIGIN"])
    if origin.scheme != "https" or not origin.hostname or origin.path not in ("", "/") or origin.query or origin.fragment or origin.username:
        raise ImproperlyConfigured("PUBLIC_ORIGIN must be an HTTPS origin without a path or credentials.")
    hosts = {host.strip() for host in env["ALLOWED_HOSTS"].split(",")}
    if "*" in hosts or origin.hostname not in hosts:
        raise ImproperlyConfigured("ALLOWED_HOSTS must explicitly include the PUBLIC_ORIGIN hostname.")
