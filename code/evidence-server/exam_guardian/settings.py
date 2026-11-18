import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("EG_DEBUG") == "1"
SECRET_KEY = os.getenv("EG_SECRET_KEY") or ("local-development-only-secret" if DEBUG else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Set EG_SECRET_KEY, or EG_DEBUG=1 for loopback development.")

ALLOWED_HOSTS = os.getenv("EG_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "evidence",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "exam_guardian.urls"
WSGI_APPLICATION = "exam_guardian.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
if os.getenv("EG_DB_NAME"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ["EG_DB_NAME"],
        "HOST": os.getenv("EG_DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("EG_DB_PORT", "3306"),
        "USER": os.environ["EG_DB_USER"],
        "PASSWORD": os.environ["EG_DB_PASSWORD"],
        "OPTIONS": {"charset": "utf8mb4"},
    }}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.getenv("EG_SQLITE", BASE_DIR / "db.sqlite3")),
        "OPTIONS": {"timeout": 15, "transaction_mode": "IMMEDIATE"},
    }}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{validator}"}
    for validator in (
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    )
]
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "var" / "static"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "review_list"
LOGOUT_REDIRECT_URL = "login"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not DEBUG
if os.getenv("EG_TRUST_PROXY") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = os.getenv("EG_CSRF_TRUSTED_ORIGINS", "").split()
EG_MEDIA_ROOT = Path(os.getenv("EG_MEDIA_ROOT", BASE_DIR / "var" / "private")).resolve()
EG_MOODLE_SITE = os.getenv("EG_MOODLE_SITE", "moodle-lab")
EG_MOODLE_SECRET = os.getenv("EG_MOODLE_SECRET", "")
EG_MOODLE_REVIEW_BASE = os.getenv("EG_MOODLE_REVIEW_BASE", "")
EG_ACCEL_MEDIA = os.getenv("EG_ACCEL_MEDIA") == "1"
EG_ENABLE_STANDALONE = os.getenv("EG_ENABLE_STANDALONE", "1" if DEBUG else "0") == "1"
EG_MAX_SEGMENT_BYTES = 8 * 1024 * 1024
EG_MAX_SESSION_BYTES = 1024 * 1024 * 1024
EG_MAX_SESSION_SECONDS = 4 * 60 * 60
EG_UPLOAD_GRACE_SECONDS = 120
EG_SEGMENT_MS = 5000
EG_CAPTURE_SCRIPT = Path(os.getenv("EG_CAPTURE_SCRIPT", BASE_DIR.parent / "lab/moodle-media/capture.js"))
EG_FACE_MODEL = Path(os.getenv("EG_FACE_MODEL", BASE_DIR / "var" / "models" / "blaze_face_short_range.tflite"))
EG_HAAR_MODEL = Path(os.getenv("EG_HAAR_MODEL", BASE_DIR / "var" / "models" / "haarcascade_frontalface_default.xml"))
FILE_UPLOAD_MAX_MEMORY_SIZE = 512 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 1
