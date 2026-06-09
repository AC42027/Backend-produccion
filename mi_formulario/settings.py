import os
from pathlib import Path  # type: ignore
from decouple import config
from decouple import Csv as CsvParser
import pymysql

pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [
                       s.strip() for s in v.split(',')])


CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=lambda v: [
                              s.strip() for s in v.split(',')], default=[])


INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'inspeccion',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'inspeccion.middleware.RestringirIPMiddleware',
]

ROOT_URLCONF = 'mi_formulario.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mi_formulario.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('MYSQL_DATABASE'),
        'USER': config('MYSQL_USER'),
        'PASSWORD': config('MYSQL_PASSWORD'),
        'HOST': config('MYSQL_HOST'),
        'PORT': config('MYSQL_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

# CORS: usar IP desde .env
CORS_ALLOW_ALL_ORIGINS = config(
    'CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool)

if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = CsvParser()(config('CORS_ALLOWED_ORIGINS', default=''))
    print("✔️ CORS_ALLOWED_ORIGINS:", CORS_ALLOWED_ORIGINS)


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = False

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static_files'),
]
print('valores staticos:', STATIC_ROOT)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Duración de la sesión: 60 minutos (3600 segundos)
SESSION_COOKIE_AGE = 60 * 60  # 1 hora

# Mantener la sesión activa si el usuario sigue navegando
SESSION_SAVE_EVERY_REQUEST = True

# Opcional: evitar que se cierre al cerrar el navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = False



# settings.py (Agrégalo al final)

# Lista de rangos de IP o IPs fijas permitidas
ALLOWED_IP_PREFIXES = [
    '10.107.205.',
    '10.107.204.',
]

# Lista de nombres de equipos (Hostnames) permitidos
ALLOWED_DYNAMIC_HOSTNAMES = [
    'CL01NL1826.la.ad.goodyear.com',  # Equipo Diego
    'CL01NL1981.la.ad.goodyear.com',  # PC turno
    'CL01NL1884.la.ad.goodyear.com',
]

# Rutas que pueden ser accedidas desde cualquier IP
EXEMPT_IP_RESTRICTION_PATHS = [
    '/api/dashboard/inspecciones/',
    '/api/login-ldap/'
]

# Jazzmin settings
JAZZMIN_SETTINGS = {
    "site_title": "Goodyear Admin",
    "site_header": "Goodyear Admin",
    "site_brand": "Goodyear",
    "welcome_sign": "Bienvenido al Panel de Administración de Inspecciones",
    "copyright": "Goodyear Chile",
    "search_model": ["auth.User", "inspeccion.Inspeccion"],
    "user_avatar": None,
    "site_logo": "img/logo_goodyear.png",
    "login_logo": "img/logo_goodyear.png",
    "topmenu_links": [
        {"name": "Inicio", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "auth.User"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "inspeccion.Inspeccion": "fas fa-clipboard-check",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "custom_js": None,
    "custom_css": "css/custom_admin_v2.css",
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}