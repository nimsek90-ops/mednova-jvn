import os
import sys
import secrets
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
# Only known environment file; never serve this directory as a static root.
env_path = BASE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
TESTING = "test" in sys.argv or os.getenv("MEDNOVA_TESTING") == "1"
LOCAL = os.getenv("APP_ENV", "production") == "local"
if not LOCAL and os.getenv("MEDNOVA_TESTING") == "1" and "test" not in sys.argv:
    raise ImproperlyConfigured("MEDNOVA_TESTING cannot be used to start a production application.")
DEBUG = False
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if TESTING:
    SECRET_KEY = secrets.token_urlsafe(64)
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "Set a random DJANGO_SECRET_KEY of at least 50 characters. Run configure.py first."
    )
ALLOWED_HOSTS = [
    x.strip()
    for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1" if LOCAL else "").split(
        ","
    )
    if x.strip()
]
if TESTING:
    ALLOWED_HOSTS += ["testserver"]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must list exact hostnames.")
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "care",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "care.middleware.SecurityPolicyMiddleware",
]
ROOT_URLCONF = "mednova.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "care.context.common",
            ]
        },
    }
]
WSGI_APPLICATION = "mednova.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "mednova"),
        "USER": os.getenv("MYSQL_USER", "mednova_app"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "isolation_level": "read committed",
        },
    }
}
if os.getenv("MYSQL_SSL_CA"):
    DATABASES["default"]["OPTIONS"]["ssl"] = {"ca": os.environ["MYSQL_SSL_CA"]}
if TESTING and os.getenv("MEDNOVA_TEST_MYSQL") != "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("MEDNOVA_TEST_DB", ":memory:"),
            "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
        }
    }
AUTH_USER_MODEL = "care.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Kolkata"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
WHITENOISE_USE_FINDERS = LOCAL or TESTING
MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT") or str(BASE_DIR / "private_uploads"))
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 80
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not (LOCAL or TESTING)
CSRF_COOKIE_SECURE = not (LOCAL or TESTING)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = not (LOCAL or TESTING)
SECURE_HSTS_SECONDS = 31536000 if not (LOCAL or TESTING) else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [
    s.strip() for s in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if s.strip()
]
# Enable only behind a proxy that strips incoming X-Forwarded-Proto.
if os.getenv("TRUST_PROXY") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"
PASSWORD_RESET_TIMEOUT = 1800
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")
PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "http://127.0.0.1:8000" if LOCAL else "")
TURN_URL = os.getenv("TURN_URL", "")
TURN_SECRET = os.getenv("TURN_SECRET", "")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
CLAMAV_COMMAND = os.getenv("CLAMAV_COMMAND", "")
CSRF_FAILURE_VIEW = "care.views.csrf_failure"
