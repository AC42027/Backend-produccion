"""
Settings para pruebas locales (no usar en producción).
Hereda todo de settings.py pero usa SQLite y host permisivo.
Requiere variables de entorno mínimas (SECRET_KEY, ALLOWED_HOSTS, etc.)
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'local_test_db.sqlite3'),  # type: ignore # noqa
    }
}

ALLOWED_HOSTS = ['*']
DEBUG = True
