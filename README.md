# 🛠️ Backend de Inspecciones Técnicas - Goodyear

Este backend está desarrollado en **Django 5** con conexión a base de datos **MySQL**, autenticación segura mediante **LDAP corporativo**, y estructura modular para manejo de inspecciones técnicas.

---

## 🚀 Tecnologías utilizadas

- [Django 5.x](https://www.djangoproject.com/)
- [MySQL](https://www.mysql.com/)
- [LDAP3](https://ldap3.readthedocs.io/) (autenticación corporativa)
- [python-decouple](https://github.com/henriquebastos/python-decouple) (gestión segura de variables)
- [Django REST](https://www.django-rest-framework.org/) *(opcional para futuro uso)*

---

## 🧾 Funcionalidades

- Registro de inspecciones técnicas por fecha, hora y responsable.
- Asociaciones entre **División → Área → Zona → Equipo**.
- Control de categoría, ubicación física y responsable del equipo (owner).
- Preguntas técnicas dinámicas por categoría.
- Panel de dashboard con JSON listo para consumir en frontend.
- Autenticación con **servidor LDAP de Goodyear**.
- Protección de endpoints (`/api/guardar/`) mediante login corporativo.

---

## 📂 Estructura principal

```bash
mi-proyecto-backend/
│
├── .env                    # Variables de entorno seguras
├── manage.py              # Arranque de Django
├── mi_formulario/         # Configuración global del proyecto
│   └── settings.py        # Incluye conexión MySQL y LDAP desde .env
│
├── inspeccion/            # App principal del backend
│   ├── models.py          # Tablas: División, Área, Zona, Equipo, etc.
│   ├── views.py           # Endpoints de API
│   ├── urls.py            # Rutas del backend
│   ├── ldap_auth.py       # Lógica de autenticación corporativa
│   └── ...
```

---

## ⚙️ Configuración e instalación local

```bash
# Clona el repositorio
git clone https://github.com/TU_USUARIO/TU_REPO.git
cd mi-proyecto-backend

# Crea un entorno virtual
python -m venv venv
venv\Scripts\activate  # En Windows

# Instala dependencias
pip install -r requirements.txt

# Configura variables en .env
```

---

## 🔐 Variables de entorno (.env)

```env
SECRET_KEY=tu_clave_django
DEBUG=True

# Base de datos MySQL
MYSQL_DATABASE=inspecciones
MYSQL_USER=root
MYSQL_PASSWORD=1234
MYSQL_HOST=localhost
MYSQL_PORT=3306

# LDAP corporativo
LDAP_SERVER=ldap://CLSDCLA2.la.ad.goodyear.com:3268
LDAP_DOMAIN=la.ad.goodyear.com
```

---

## 📡 Endpoints disponibles

| Método | Ruta                               | Descripción                         |
|--------|------------------------------------|-------------------------------------|
| POST   | `/api/login-ldap/`                 | Login corporativo (LDAP)           |
| POST   | `/api/logout/`                     | Cerrar sesión                      |
| POST   | `/api/guardar/`                    | Guardar inspección técnica 🔒       |
| GET    | `/api/divisiones/`                 | Listar divisiones                  |
| GET    | `/api/areas/`                      | Listar áreas                       |
| GET    | `/api/zonas/`                      | Listar zonas                       |
| GET    | `/api/equipos/`                    | Listar equipos completos           |
| GET    | `/api/equipo/<id>/`                | Obtener detalles de un equipo      |
| GET    | `/api/categorias/`                 | Listar categorías de equipos       |
| GET    | `/api/preguntas/<categoria>/`      | Preguntas técnicas por categoría   |
| GET    | `/api/dashboard/inspecciones/`     | Datos para el dashboard técnico    |

---

## 🔐 Seguridad

- Las credenciales de base de datos y LDAP **no están en el código**, sino en `.env`.
- El endpoint de inspecciones está **protegido por autenticación LDAP y sesión de Django**.
- El proyecto utiliza `@login_required` y `SessionMiddleware`.

---

## 🤝 Colaboración

1. Forkea el repositorio
2. Crea tu rama: `git checkout -b feature/mi-funcionalidad`
3. Haz commit: `git commit -m "Agrega nueva funcionalidad"`
4. Haz push: `git push origin feature/mi-funcionalidad`
5. Abre un Pull Request

---

## 📌 Requisitos

- Python 3.11 o superior
- MySQL 8 o compatible
- Acceso al servidor LDAP corporativo (Goodyear)

---

¿Tienes dudas o sugerencias? ¡Contáctame o crea un issue en GitHub!
