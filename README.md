
# 🛠️ Backend de Inspecciones Técnicas - Producción

Este es el backend en Django para el sistema de inspecciones técnicas de Goodyear Chile. El sistema gestiona zonas, equipos, inspecciones técnicas y autenticación vía LDAP.

---

## 🚀 Tecnologías utilizadas

- Python 3.13.x
- Django 5.2
- MySQL (conector: PyMySQL)
- Waitress (servidor WSGI en Windows)
- python-decouple (manejo de variables de entorno)
- django-cors-headers (manejo de CORS)
- LDAP3 (autenticación corporativa)

---

## 📁 Estructura del proyecto

```
mi-backend/
├── inspeccion/            # Aplicación principal
├── mi_formulario/         # Configuración Django (settings, wsgi)
├── static/                # Archivos estáticos recolectados
├── venv/                  # Entorno virtual (ignorado en Git)
├── .env                   # Variables de entorno (no subir a Git)
├── .gitignore
├── requirements.txt
├── run_waitress.py        # Script para ejecutar con Waitress
└── README.md
```

---

## ⚙️ Configuración inicial

### 1. Clona el repositorio

```bash
git clone https://github.com/usuario/backend-produccion.git
cd backend-produccion
```

### 2. Crea y activa el entorno virtual

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 4. Crea el archivo `.env`

Copia y completa el archivo según tu entorno. Ejemplo:

```env
SECRET_KEY=clave-secreta-django
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,10.107.202.51
CSRF_TRUSTED_ORIGINS=http://localhost:3010,http://10.107.202.51:3010

# Base de datos
MYSQL_DATABASE=inspecciones
MYSQL_USER=usuario
MYSQL_PASSWORD=clave
MYSQL_HOST=IP SERVIDOR
MYSQL_PORT=3306

# LDAP
LDAP_SERVER=SERVIDOR DE LDAP
LDAP_DOMAIN=miempresa.local

# CORS
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=http://localhost:3010,http://10.107.202.51:3010
```

---

## 🧪 Migraciones y carga inicial (solo si parte desde cero)

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## ▶️ Ejecución en producción (Windows + Waitress)

### Archivo: `run_waitress.py`

```python
from waitress import serve
from mi_formulario.wsgi import application

serve(application, host='0.0.0.0', port=8080)
```

### Para ejecutarlo:

```bash
python run_waitress.py
```

---

## 🔐 Panel de administración

- URL: [http://localhost:8080/admin](http://localhost:8080/admin)
- Crear superusuario (si no existe):

```bash
python manage.py createsuperuser
```

---

## 📦 Archivos importantes

- `.env`: configuración del entorno (no se sube al repositorio)
- `requirements.txt`: lista de dependencias
- `.gitignore`: ignora `venv/`, `.env`, `__pycache__/`, entre otros

---

## 🧠 Notas adicionales

- Asegúrate de que `CORS_ALLOWED_ORIGINS` coincida con el dominio/puerto del frontend.
- En producción real, usar `DEBUG=False` y definir correctamente `ALLOWED_HOSTS`.
- Este backend se comunica con un frontend hecho en Next.js (`:8000`) y requiere conexión con MySQL.

---

Privado · Uso interno en Goodyear Chile · 2024–2025
