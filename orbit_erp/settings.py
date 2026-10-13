"""Django settings for the Orbit ERP platform.

Multi-company enterprise ERP. Configuration comes from environment variables.
Production hardening toggles engage automatically when DEBUG=0.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()
]
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
if _render_host:
    _render_origin = f"https://{_render_host}"
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)


def _parse_database_url(url: str):
    p = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (p.path or "").lstrip("/") or "orbiterp",
        "USER": p.username or "",
        "PASSWORD": p.password or "",
        "HOST": p.hostname or "localhost",
        "PORT": str(p.port or 5432),
    }


_db_url = os.environ.get("DATABASE_URL")


def _ensure_database():
    """Create the target Postgres database on first boot if it is missing.

    Render's free tier allows only one database *instance*; Orbit ERP shares
    the instance with the sibling app and keeps its own logical database.
    Runs only when DATABASE_URL is set (production); never blocks boot.
    """
    if not _db_url:
        return
    try:
        import psycopg
        from psycopg import sql
        from urllib.parse import urlunparse

        p = urlparse(_db_url)
        dbname = (p.path or "").lstrip("/") or "orbiterp"
        maint_url = urlunparse(p._replace(path="/postgres"))
        with psycopg.connect(maint_url, autocommit=True, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                if not cur.fetchone():
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
    except Exception:
        pass  # migrate will surface any real connection problem


_ensure_database()

DATABASES = {
    "default": _parse_database_url(_db_url)
    if _db_url
    else {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "fleet",
    "shared",
    "imports",
    "exports",
    "manufacturing",
    "rentals",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ActiveCompanyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "orbit_erp.urls"

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
                "core.context_processors.active_company",
            ],
        },
    },
]

WSGI_APPLICATION = "orbit_erp.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Addis_Ababa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "company_hub"
LOGOUT_REDIRECT_URL = "login"

# Company roles
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_DISPATCHER = "dispatcher"
ROLE_ACCOUNTANT = "accountant"
ROLE_VIEWER = "viewer"
ROLES = [
    (ROLE_OWNER, "Owner"),
    (ROLE_ADMIN, "Administrator"),
    (ROLE_MANAGER, "Operations Manager"),
    (ROLE_DISPATCHER, "Dispatcher"),
    (ROLE_ACCOUNTANT, "Accountant"),
    (ROLE_VIEWER, "Viewer"),
]
# Roles allowed to create/edit operational records
EDITOR_ROLES = {ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_DISPATCHER}
FINANCE_ROLES = {ROLE_OWNER, ROLE_ADMIN, ROLE_ACCOUNTANT}
