from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=True)

DJANGO_Q_ENABLED = os.getenv('ENABLE_DJANGO_Q', 'False') == 'True'

if DJANGO_Q_ENABLED:
    try:
        import django_q  # noqa: F401
        DJANGO_Q_AVAILABLE = True
    except Exception:
        DJANGO_Q_AVAILABLE = False
else:
    DJANGO_Q_AVAILABLE = False

SECRET_KEY = os.getenv('SECRET_KEY') or os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    secret_file = BASE_DIR / '.runtime_secret_key'
    if secret_file.exists():
        SECRET_KEY = secret_file.read_text(encoding='utf-8').strip()
    else:
        SECRET_KEY = get_random_secret_key()
        secret_file.write_text(SECRET_KEY, encoding='utf-8')

DEBUG = (os.getenv('DEBUG', 'True') or 'True').strip().lower() in ('1', 'true', 'yes', 'on')

ALLOWED_HOSTS = [
    'afyacom.pythonanywhere.com',
    '.pythonanywhere.com',
    'localhost',
    '127.0.0.1',
    '.ngrok-free.dev',
    '.ngrok-free.app',
    '.ngrok.io',
]

CSRF_TRUSTED_ORIGINS = [
    'https://afyacom.pythonanywhere.com',
    'https://*.pythonanywhere.com',
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
    'https://*.ngrok-free.dev',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# ── Production / PythonAnywhere security ───────────────────────────────────
# PythonAnywhere terminates SSL at their proxy, so Django must NOT redirect
# HTTP→HTTPS itself (that causes redirect loops). Cookie security is still on.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False          # PythonAnywhere proxy already enforces HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000       # 1 year — only after you're sure HTTPS works
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
# ───────────────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
AI_PROVIDER = (os.getenv('AI_PROVIDER', 'groq') or 'groq').strip().lower()
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'qwen/qwen-2.5-72b-instruct:free')
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
AT_USERNAME = (os.getenv('AT_USERNAME', '') or '').strip().strip('"').strip("'")
AT_API_KEY = (os.getenv('AT_API_KEY', '') or '').strip().strip('"').strip("'")
AT_AUTH_TOKEN = (os.getenv('AT_AUTH_TOKEN', '') or '').strip().strip('"').strip("'")
AT_SENDER_ID = (os.getenv('AT_SENDER_ID', '') or '').strip().strip('"').strip("'")
AT_ENV = (os.getenv('AT_ENV', 'sandbox') or 'sandbox').strip().strip('"').strip("'")
TWILIO_ACCOUNT_SID = (os.getenv('TWILIO_ACCOUNT_SID', '') or '').strip().strip('"').strip("'")
TWILIO_AUTH_TOKEN = (os.getenv('TWILIO_AUTH_TOKEN', '') or '').strip().strip('"').strip("'")
TWILIO_PHONE_NUMBER = (os.getenv('TWILIO_PHONE_NUMBER', '') or '').strip().strip('"').strip("'")
TWILIO_MESSAGING_SERVICE_SID = (os.getenv('TWILIO_MESSAGING_SERVICE_SID', '') or '').strip().strip('"').strip("'")
BEEM_API_KEY = os.getenv('BEEM_API_KEY', '')
BEEM_SECRET_KEY = os.getenv('BEEM_SECRET_KEY', '')
BEEM_SENDER_ID = os.getenv('BEEM_SENDER_ID', '')
BEEM_SEND_URL = os.getenv('BEEM_SEND_URL', 'https://apisms.beem.africa/v1/send')
ANDROID_SMS_GATEWAY_SEND_URL = os.getenv('ANDROID_SMS_GATEWAY_SEND_URL', '')
ANDROID_SMS_GATEWAY_TOKEN = os.getenv('ANDROID_SMS_GATEWAY_TOKEN', '')

# ── Email / Gmail SMTP ─────────────────────────────────────────────────────
_email_backend_env = (os.getenv('EMAIL_BACKEND', '') or '').strip()
EMAIL_BACKEND = _email_backend_env if _email_backend_env else (
    'django.core.mail.backends.smtp.EmailBackend'
    if os.getenv('EMAIL_HOST_USER') else
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST         = (os.getenv('EMAIL_HOST', 'smtp.gmail.com') or 'smtp.gmail.com').strip()
EMAIL_PORT         = int(os.getenv('EMAIL_PORT', '587') or '587')
EMAIL_USE_TLS      = (os.getenv('EMAIL_USE_TLS', 'True') or 'True').strip().lower() in ('1', 'true', 'yes')
EMAIL_USE_SSL      = (os.getenv('EMAIL_USE_SSL', 'False') or 'False').strip().lower() in ('1', 'true', 'yes')
EMAIL_HOST_USER    = (os.getenv('EMAIL_HOST_USER', '') or '').strip()
EMAIL_HOST_PASSWORD = (os.getenv('EMAIL_HOST_PASSWORD', '') or '').strip()
DEFAULT_FROM_EMAIL = (os.getenv('DEFAULT_FROM_EMAIL', '') or '').strip() or (
    f'AfyaSmart Health <{EMAIL_HOST_USER}>' if EMAIL_HOST_USER else 'AfyaSmart Health <noreply@afyasmart.app>'
)
SERVER_EMAIL       = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = '[AfyaSmart] '
EMAIL_TIMEOUT      = 20   # seconds
# ───────────────────────────────────────────────────────────────────────────


INSTALLED_APPS = [
    'jazzmin',
    'daphne',
    'channels',

    # Authentication providers
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.twitter_oauth2',

    # Local apps
    'AI_brain',
    'users',
    'chats',
    'doctor',
    'main',
    'menstrual',
    'pregnancy',
    'reproduction',
    'card',
    'offline_chat',
    'mobile_api',
    'medics',
    'diseases',
    'machine_learning',

    # Third-party apps


    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

if DJANGO_Q_AVAILABLE:
    INSTALLED_APPS.append('django_q')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'card.middleware.PersonaReminderMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
                BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'menstrual.context_processors.reminders_processor',
                'users.context_processors.role_flags',
                'main.context_processors.admin_dashboard_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'sw'  # Lugha ya kuanzia (Default)

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "assests",
]

_mobile_web_dir = BASE_DIR / "mobile_app" / "web"
if _mobile_web_dir.exists():
    STATICFILES_DIRS.append(_mobile_web_dir)

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from django.utils.translation import gettext_lazy as _

# Orodha ya lugha ambazo mfumo utazikubali
LANGUAGES = [
    ('sw', _('Swahili')),
    ('en', _('English')),
    ('ar', _('Arabic')),
]

# Hapa ndipo mafaili ya tafsiri yatahifadhiwa
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

LOGIN_URL = 'users:login'  # Or whatever your login name is
LOGIN_REDIRECT_URL = 'main:home'
LOGOUT_REDIRECT_URL = 'main:home'
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_ADAPTER = 'users.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'users.adapters.SocialAccountAdapter'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_STORE_TOKENS = True

# ── Allauth email verification ─────────────────────────────────────────────
ACCOUNT_EMAIL_VERIFICATION    = os.getenv('ACCOUNT_EMAIL_VERIFICATION', 'optional').strip().lower()
# Set ACCOUNT_EMAIL_VERIFICATION=mandatory in .env when you are ready to enforce it.
# 'optional'  → email sent but not required to proceed
# 'mandatory' → user must confirm email before logging in
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION     = True
ACCOUNT_CONFIRM_EMAIL_ON_GET            = True
ACCOUNT_UNIQUE_EMAIL                    = True
ACCOUNT_EMAIL_SUBJECT_PREFIX            = '[AfyaSmart] '

# Social logins (Google, Facebook, X) skip email verification entirely —
# the provider (e.g. Google) already guarantees the email is verified.
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_EMAIL_REQUIRED     = False

# New-style allauth settings (replaces deprecated ACCOUNT_EMAIL_REQUIRED,
# ACCOUNT_USERNAME_REQUIRED, ACCOUNT_AUTHENTICATION_METHOD)
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_LOGIN_METHODS = {'email'}
# ───────────────────────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID = (os.getenv('GOOGLE_CLIENT_ID', '') or '').strip()
GOOGLE_CLIENT_SECRET = (os.getenv('GOOGLE_CLIENT_SECRET', '') or '').strip()
FACEBOOK_APP_ID = (os.getenv('FACEBOOK_APP_ID', os.getenv('FACEBOOK_CLIENT_ID', '')) or '').strip()
FACEBOOK_APP_SECRET = (os.getenv('FACEBOOK_APP_SECRET', os.getenv('FACEBOOK_CLIENT_SECRET', '')) or '').strip()
X_CLIENT_ID = (os.getenv('X_CLIENT_ID', os.getenv('TWITTER_CLIENT_ID', '')) or '').strip()
X_CLIENT_SECRET = (os.getenv('X_CLIENT_SECRET', os.getenv('TWITTER_CLIENT_SECRET', '')) or '').strip()

GOOGLE_OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
FACEBOOK_OAUTH_ENABLED = bool(FACEBOOK_APP_ID and FACEBOOK_APP_SECRET)
X_OAUTH_ENABLED = bool(X_CLIENT_ID and X_CLIENT_SECRET)


def _social_apps(client_id, secret, key=''):
    if not client_id or not secret:
        return []
    return [{
        'client_id': client_id,
        'secret': secret,
        'key': key,
    }]


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'prompt': 'select_account'},
        'APPS': _social_apps(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name'],
        'VERIFIED_EMAIL': False,
        'VERSION': 'v22.0',
        'APPS': _social_apps(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET),
    },
    'twitter_oauth2': {
        'SCOPE': ['tweet.read', 'users.read'],
        'APPS': _social_apps(X_CLIENT_ID, X_CLIENT_SECRET),
    },
}

if DJANGO_Q_AVAILABLE:
    Q_CLUSTER = {
        'name': 'DjangORM',
        'workers': 4,
        'timeout': 60,
        'retry': 120,
        'queue_limit': 50,
        'bulk': 10,
        'orm': 'default'
    }

JAZZMIN_SETTINGS = {
    "site_title": "AfyaSmart Admin",
    "site_header": "AfyaSmart Health",
    "site_brand": "AfyaSmart Admin",
    "site_logo_classes": "img-circle",
    "welcome_sign": "Karibu kwenye control center ya AfyaSmart",
    "copyright": "AfyaSmart Health",
    "search_model": [
        "auth.User",
        "menstrual.DoctorProfile",
        "menstrual.CommunityPost",
        "menstrual.DailyTip",
        "menstrual.DailyLog",
        "menstrual.MenstrualCycle",
        "menstrual.Reminder",
    ],
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Analytics", "url": "main:control_center", "permissions": ["auth.view_user"]},
        {"model": "auth.User"},
        {"model": "menstrual.DoctorProfile"},
        {"model": "menstrual.DailyTip"},
        {"model": "menstrual.CommunityPost"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "menstrual.MenstrualCycle": "fas fa-calendar-alt",
        "menstrual.DailyLog": "fas fa-notes-medical",
        "menstrual.DailyTip": "fas fa-lightbulb",
        "menstrual.CommunityPost": "fas fa-comments",
        "menstrual.CommunityReply": "fas fa-comment-dots",
        "menstrual.DoctorProfile": "fas fa-user-md",
        "menstrual.Reminder": "fas fa-bell",
    },
    "hide_apps": [],
    "order_with_respect_to": [
        "auth",
        "menstrual",
    ],
    "custom_links": {
        "auth": [{"name": "Admin Analytics Dashboard", "url": "main:control_center", "icon": "fas fa-chart-line", "permissions": ["auth.view_user"]}],
        "menstrual": [{"name": "AI Content Insights", "url": "main:control_center", "icon": "fas fa-brain", "permissions": ["auth.view_user"]}],
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "dark_mode_theme": "darkly",
    "navbar": "navbar-danger navbar-dark",
    "brand_colour": "navbar-danger",
    "accent": "accent-pink",
    "sidebar": "sidebar-dark-danger",
    "button_classes": {
        "primary": "btn-danger",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# File Upload Configuration
# Allow large file uploads (500MB max)
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Temporary file upload location (ensure it exists and is writable)
FILE_UPLOAD_TEMP_DIR = BASE_DIR / 'tmp_uploads'
FILE_UPLOAD_PERMISSIONS = 0o644

# Create tmp_uploads directory if it doesn't exist
import os
os.makedirs(FILE_UPLOAD_TEMP_DIR, exist_ok=True)


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
