import os
import socket
import platform
from pathlib import Path

from dotenv import load_dotenv
import dj_database_url


def get_local_ip():
    """Best-effort LAN IP so the Vite dev server (and a phone on the same
    network) can reach runserver during development."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


LOCAL_IP = get_local_ip()

os.environ["DJANGO_RUNSERVER_HIDE_WARNING"] = "true"

# settings.py -> config -> src -> server  ==> BASE_DIR is src/server
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# env/ lives at the repo root (two levels above src/server), like cosound.
load_dotenv(BASE_DIR.parent.parent / "env" / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-u8#1l$95&vq3w2(ei^=ng+4tdid@by!s+&u&jlizx&xr&w&(gk",
)

# SECURITY WARNING: don't run with debug turned on in production!
# Production (the droplet's env/.env.prod) sets DEBUG=false.
DEBUG = os.environ.get("DEBUG", "True").strip().lower() in ("1", "true", "yes", "on")

ALLOWED_HOSTS = []
if DEBUG:
    ALLOWED_HOSTS.extend(
        [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "localhost:5173",
            "127.0.0.1:5173",
            "0.0.0.0:5173",
            LOCAL_IP,
            f"{LOCAL_IP}:5173",
        ]
    )
else:
    # Comma-separated domains/IPs, e.g. "wagon.example.com,203.0.113.5"
    prod_hosts = os.environ.get("PROD_HOSTS", "")
    ALLOWED_HOSTS.extend(h.strip() for h in prod_hosts.split(",") if h.strip())

# CSRF trusted origins (production runs behind Caddy over HTTPS).
CSRF_TRUSTED_ORIGINS = []
for entry in os.environ.get("PROD_HOSTS", "").split(","):
    entry = entry.strip().rstrip("/")
    if not entry:
        continue
    if "://" not in entry:
        entry = f"https://{entry}"
    CSRF_TRUSTED_ORIGINS.append(entry)

# Caddy terminates TLS and forwards the original scheme in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Production security hardening (HTTPS is terminated by Caddy). Kept out of DEBUG
# so local HTTP development isn't broken by secure-only cookies.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600  # raise (e.g. 31536000) once HTTPS is confirmed
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[%(asctime)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "no_timestamp": {"format": "%(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "console_no_timestamp": {
            "class": "logging.StreamHandler",
            "formatter": "no_timestamp",
        },
    },
    "loggers": {
        "django.server": {
            "handlers": ["console_no_timestamp"],
            "level": "INFO",
            "propagate": False,
        },
        "django_tasks": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

INSTALLED_APPS = [
    # Admin theme — must precede django.contrib.admin.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    # Background tasks (database backend).
    "django_tasks",
    "django_tasks.backends.database",
    # Third-party.
    "django_vite",
    "django_htmx",
    "django_tables2",
    "django_cotton",
    "widget_tweaks",
    "storages",
    "anymail",
    # Local apps.
    "core",
    "dashboard",
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
    "django_htmx.middleware.HtmxMiddleware",
]

# Dev-only live reload — django-browser-reload is a dev dependency and is not
# installed in the production image, so only wire it up when DEBUG is on.
if DEBUG:
    INSTALLED_APPS.append("django_browser_reload")
    MIDDLEWARE.append("django_browser_reload.middleware.BrowserReloadMiddleware")

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                [
                    "django.template.loaders.cached.Loader",
                    [
                        "django_cotton.cotton_loader.Loader",
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                ]
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context.maps_api_key",
            ],
            "builtins": [
                "django_cotton.templatetags.cotton",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"

# Database — PostGIS. dj-database-url parses DATABASE_URL; the explicit engine
# forces the GIS backend even when the URL scheme is plain "postgres://"
# (e.g. a managed DB), so GeoDjango keeps working.
DATABASES = {
    "default": dj_database_url.config(
        default="postgis://admin:changeme@localhost:5432/wagon_db",
        conn_max_age=600,
        engine="django.contrib.gis.db.backends.postgis",
    )
}

# GeoDjango native libs. Linux/Docker auto-detects them; macOS (Homebrew) needs
# explicit paths. Override via env if your Homebrew prefix differs (Intel Macs
# use /usr/local).
if platform.system() == "Darwin":
    GDAL_LIBRARY_PATH = os.getenv(
        "GDAL_LIBRARY_PATH", "/opt/homebrew/opt/gdal/lib/libgdal.dylib"
    )
    GEOS_LIBRARY_PATH = os.getenv(
        "GEOS_LIBRARY_PATH", "/opt/homebrew/opt/geos/lib/libgeos_c.dylib"
    )

# Cache — database-backed (works across multiple gunicorn workers). Table is
# created by `createcachetable` (run in the build/start scripts).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# Background tasks — database backend, processed by the `db_worker` process.
TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.database.DatabaseBackend",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTH_USER_MODEL = "core.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Static files: Vite builds into vite/static (+ manifest); collectstatic gathers
# everything into staticfiles/, served by WhiteNoise in production.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "vite/static",
]

DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "dev_server_host": LOCAL_IP,
        "dev_server_port": 5173,
        "manifest_path": BASE_DIR / "vite/static/manifest.json",
    }
}

# ---------------------------------------------------------------------------
# Storage (AWS S3) + email (AWS SES) — scaffolded like cosound, but inert until
# the AWS_* env vars are present, so local dev and a no-AWS droplet just work.
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
AWS_S3_SIGNATURE_VERSION = "s3v4"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Switch default (media) storage to S3 only when a bucket is configured.
if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME,
            "endpoint_url": (
                f"https://s3.{AWS_S3_REGION_NAME}.amazonaws.com"
                if AWS_S3_REGION_NAME
                else None
            ),
            "signature_version": AWS_S3_SIGNATURE_VERSION,
        },
    }
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"

# WhiteNoise compressed/hashed static files in production.
if not DEBUG:
    STORAGES["staticfiles"] = {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }

# Email: console in dev / without AWS creds; AWS SES via Anymail when configured.
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@wagon.local")
ANYMAIL = {
    "AMAZON_SES_CLIENT_PARAMS": {
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "region_name": os.getenv("AWS_S3_REGION_NAME", "us-east-1"),
    },
}
if DEBUG or not AWS_ACCESS_KEY_ID:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"

# ---------------------------------------------------------------------------
# django-unfold admin theme
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Wagon Admin",
    "SITE_HEADER": "Wagon",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}
