from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv(override=True)


BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = os.getenv('DEBUG') == 'True'

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
    'https://*.ngrok-free.dev',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
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


INSTALLED_APPS = [
    'jazzmin',
    'channels',

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
    'django_q',

    # Third-party apps


    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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

LANGUAGE_CODE = 'en-us'

LANGUAGE_CODE = 'sw' # Lugha ya kuanzia (Default)

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "assests",
]
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
    "site_title": "ZanzHub Admin",
    "site_header": "ZanzHub AI Health",
    "site_brand": "ZanzHub Admin",
    "site_logo_classes": "img-circle",
    "welcome_sign": "Karibu kwenye control center ya ZanzHub",
    "copyright": "ZanzHub AI Health",
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