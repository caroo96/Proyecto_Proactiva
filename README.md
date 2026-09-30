# PROACTIV@ TdeA - Backend

Backend de la aplicación web para la evaluación de estudios de caso empresariales en la Facultad de Administración del Tecnológico de Antioquia.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Academic-yellow.svg)]()

---

## Tabla de Contenidos

- [Tecnologías](#-tecnologías)
- [Características](#-características)
- [Instalación](#-instalación)
- [Configuración](#️-configuración)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API Endpoints](#-api-endpoints)
- [Datos de Prueba](#-datos-de-prueba)
- [Solución de Problemas](#-solución-de-problemas)
- [Autor](#-autor)

---

## Tecnologías

- **[Python 3.11+](https://www.python.org/)** - Lenguaje de programación
- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderno y rápido
- **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** - ORM con soporte async
- **[PostgreSQL](https://www.postgresql.org/)** - Base de datos relacional
- **[Alembic](https://alembic.sqlalchemy.org/)** - Migraciones de base de datos
- **[Pydantic](https://docs.pydantic.dev/)** - Validación de datos
- **[JWT](https://jwt.io/)** - Autenticación basada en tokens
- **[Bcrypt](https://github.com/pyca/bcrypt/)** - Hashing de contraseñas
- **[Uvicorn](https://www.uvicorn.org/)** - Servidor ASGI

---

## Características

- ✅ **Autenticación JWT** con control de acceso por roles
- ✅ **CRUD completo** de Usuarios, Casos, Competencias y Programas
- ✅ **Roles de usuario**: Coordinador, Profesor, Estudiante
- ✅ **Relaciones muchos-a-muchos** entre Casos y Competencias/Programas
- ✅ **Validación automática** con Pydantic
- ✅ **Documentación interactiva** con Swagger UI
- ✅ **Migraciones de BD** con Alembic
- ✅ **Async/await** para máximo rendimiento
- ✅ **CORS configurado** para integración con frontend

---

## 📦 Instalación

### Requisitos Previos

Asegúrate de tener instalado:

- **Python 3.11 o superior** ([Descargar](https://www.python.org/downloads/))
- **PostgreSQL 14 o superior** ([Descargar](https://www.postgresql.org/download/))
- **Git** ([Descargar](https://git-scm.com/downloads))

---

### 1️⃣ Clonar el Repositorio
```bash
git clone https://github.com/TU_USUARIO/proactiva-back.git
cd proactiva-back
```

---

### 2️⃣ Crear Entorno Virtual

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3️⃣ Instalar Dependencias
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración

### 1️⃣ Configurar PostgreSQL

**Opción A: Usando la terminal (psql)**
```bash
# Conectar a PostgreSQL
psql -U postgres

# Crear base de datos
CREATE DATABASE simuladorcasos;

# Verificar
\l

# Salir
\q
```

**Opción B: Usando pgAdmin**

1. Abrir pgAdmin
2. Click derecho en "Databases" → "Create" → "Database"
3. **Name**: `simuladorcasos`
4. Click "Save"

---

### 2️⃣ Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:
```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@localhost:5432/simuladorcasos

# JWT
SECRET_KEY=tu_clave_secreta_super_segura_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

**💡 Para generar una SECRET_KEY segura:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copia el resultado y pégalo en `SECRET_KEY`.

---

### 3️⃣ Ejecutar Migraciones
```bash
# Crear migración inicial (si no existe)
alembic revision --autogenerate -m "Initial migration"

# Aplicar todas las migraciones
alembic upgrade head
```

---

## 🚀 Uso

### Iniciar el Servidor

**Modo desarrollo (con auto-reload):**
```bash
python -m uvicorn main:app --reload --port 8000
```

**O directamente:**
```bash
uvicorn main:app --reload --port 8000
```

---

### Acceder a la Documentación

Una vez iniciado el servidor, accede a:

- **Swagger UI (Interactivo)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc (Alternativo)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/](http://localhost:8000/)

---

## 📁 Estructura del Proyecto
```
Proactiva_Back/
├── alembic/                  # Sistema de migraciones
│   ├── versions/            # Archivos de migración
│   └── env.py              # Configuración de Alembic
├── routers/                 # Endpoints organizados por módulo
│   ├── __init__.py
│   ├── casos.py            # CRUD de casos
│   ├── competencias.py     # CRUD de competencias
│   └── programas.py        # CRUD de programas
├── .env                     # Variables de entorno (NO subir a Git)
├── .env.example            # Plantilla de variables
├── .gitignore              # Archivos ignorados por Git
├── alembic.ini             # Configuración de Alembic
├── auth.py                 # Lógica de autenticación JWT
├── db_connection.py        # Configuración de base de datos
├── main.py                 # Punto de entrada de la aplicación
├── orm.py                  # Modelos de SQLAlchemy
├── schemas.py              # Esquemas de validación Pydantic
├── requirements.txt        # Dependencias del proyecto
└── README.md               # Este archivo
```

---

## 🔑 API Endpoints

### 🔐 Autenticación

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| `POST` | `/token` | Login (obtener token JWT) | No |
| `GET` | `/me` | Obtener usuario actual | Sí |

---

### 👤 Usuarios

| Método | Endpoint | Descripción | Roles |
|--------|----------|-------------|-------|
| `POST` | `/usuarios/` | Crear usuario | Público |
| `GET` | `/usuarios/` | Listar usuarios | Coordinador, Profesor |
| `GET` | `/usuarios/{id}` | Obtener usuario por ID | Todos |

---

### 📚 Casos

| Método | Endpoint | Descripción | Roles |
|--------|----------|-------------|-------|
| `POST` | `/casos/` | Crear caso | Coordinador, Profesor |
| `GET` | `/casos/` | Listar casos | Todos |
| `GET` | `/casos/{id}` | Obtener caso con detalles | Todos |
| `PUT` | `/casos/{id}` | Actualizar caso | Creador, Coordinador |
| `DELETE` | `/casos/{id}` | Eliminar caso | Coordinador |

---

### 🎯 Competencias

| Método | Endpoint | Descripción | Roles |
|--------|----------|-------------|-------|
| `POST` | `/competencias/` | Crear competencia | Coordinador |
| `GET` | `/competencias/` | Listar competencias | Todos |
| `GET` | `/competencias/{id}` | Obtener competencia | Todos |

---

### 🎓 Programas

| Método | Endpoint | Descripción | Roles |
|--------|----------|-------------|-------|
| `POST` | `/programas/` | Crear programa | Coordinador |
| `GET` | `/programas/` | Listar programas | Todos |
| `GET` | `/programas/{id}` | Obtener programa | Todos |

---

## 🧪 Datos de Prueba

### 1️⃣ Acceder a Swagger

Ve a [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2️⃣ Crear Usuarios

**Coordinador:**
```json
POST /usuarios/
{
  "nombre_usuario": "admin",
  "correo_electronico": "admin@tdea.edu.co",
  "contrasena": "admin123",
  "rol": "coordinador"
}
```

**Profesor:**
```json
POST /usuarios/
{
  "nombre_usuario": "profesor1",
  "correo_electronico": "profesor@tdea.edu.co",
  "contrasena": "profesor123",
  "rol": "profesor"
}
```

**Estudiante:**
```json
POST /usuarios/
{
  "nombre_usuario": "estudiante1",
  "correo_electronico": "estudiante@tdea.edu.co",
  "contrasena": "estudiante123",
  "rol": "estudiante"
}
```

---

### 3️⃣ Hacer Login
```
POST /token

username: admin
password: admin123
```

Copia el `access_token` devuelto.

---

### 4️⃣ Autorizar en Swagger

1. Click en el botón **"Authorize"** 🔓
2. Pegar: `Bearer TU_TOKEN_AQUI`
3. Click **"Authorize"** → **"Close"**

Ahora puedes usar todos los endpoints protegidos.

---

### 5️⃣ Crear Competencias
```json
POST /competencias/
{
  "nombre": "Pensamiento Crítico",
  "descripcion": "Capacidad para analizar situaciones complejas"
}
```

---

### 6️⃣ Crear Programas
```json
POST /programas/
{
  "nombre": "Administración de Empresas",
  "codigo": "ADE",
  "descripcion": "Formación en gestión empresarial"
}
```

---

### 7️⃣ Crear Casos
```json
POST /casos/
{
  "titulo": "Crisis Financiera en Startup",
  "descripcion": "Análisis de crisis de liquidez...",
  "competencias_ids": [1],
  "programas_ids": [1]
}
```

---

## 🐛 Solución de Problemas

### ❌ Error: "SECRET_KEY not defined"

**Solución:**
```bash
# Asegúrate de tener el archivo .env con SECRET_KEY definida
# Ver sección de Configuración
```

---

### ❌ Error: "bcrypt version conflict"

**Solución:**
```bash
pip uninstall bcrypt passlib -y
pip install bcrypt==4.0.1
pip install passlib==1.7.4
```

---

### ❌ Error: "connection refused" (PostgreSQL)

**Solución:**
1. Verifica que PostgreSQL esté corriendo
2. Revisa las credenciales en `.env`
3. Verifica el puerto (por defecto 5432)
```bash
# En Windows, verificar servicios:
services.msc
# Buscar "postgresql" y verificar que esté "Running"
```

---

### ❌ Error: "Table does not exist"

**Solución:**
```bash
# Ejecutar migraciones
alembic upgrade head
```

---

### ❌ Error al importar módulos

**Solución:**
```bash
# Reinstalar dependencias
pip install -r requirements.txt
```

---

## 👥 Autores

**Diana Milena Rios Vargas**  
**Wilson Javier Estrada Zapata**
Estudiante de Ingeniería en Software  
Tecnológico de Antioquia - TdeA

**Director del Proyecto:**  
Juan Pablo Vélez Uribe

---

## 📄 Licencia

Este proyecto es parte de un trabajo de grado académico del Tecnológico de Antioquia.

---

## 🔗 Enlaces Relacionados

- **Frontend**: [Repositorio Frontend](https://github.com/TU_USUARIO/proactiva-front)
- **Documentación FastAPI**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- **SQLAlchemy Docs**: [docs.sqlalchemy.org](https://docs.sqlalchemy.org/)

---

## 📧 Contacto
