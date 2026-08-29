# TheCloeIntegration

## Integración Tributaria — Módulo de Intermediación con SimpleAPI (SII)

Sistema completo de integración tributaria que conecta la plataforma de gestión de ventas de **The Cloe** con **SimpleAPI** del **Servicio de Impuestos Internos (SII)** de Chile. Por cada venta generada en The Cloe, el sistema toma los datos, los envía a SimpleAPI para la emisión de boletas electrónicas y registra el resultado — todo con persistencia en SQL Server, frontend de administración, y arquitectura resiliente con Circuit Breaker.

---

## 📋 Descripción del Proyecto

### Problema que resuelve

The Cloe necesita un microservicio de intermediación que:

1. **Reciba ventas** desde la plataforma principal (por ID e items)
2. **Transforme** el modelo de datos interno al formato que exige SimpleAPI (estructuras anidadas SII, sumatorias, TipoDTE 39)
3. **Comunique** con SimpleAPI para generar el folio tributario del SII
4. **Persista** la relación Venta ↔ Folio en una base de datos trazable
5. **Exponga** endpoints para consultas, reportes y gestión de credenciales
6. **Proteja** la integración con Circuit Breaker ante caídas de SimpleAPI
7. **Visualice** todo desde un dashboard web con React

### ¿Por qué esta arquitectura?

| Decisión | Justificación |
|----------|---------------|
| **Django + DRF** | ORM nativo, migrations automáticas, admin panel gratis, serializers con validación — un framework para todo |
| **SQL Server** | Base empresarial escalable, compatible con django-mssql-backend, soporte para la migración con Alembic/Django |
| **React + Vite + TailwindCSS** | SPA moderna, tipo seguro con TypeScript, styling rápido con utilitarios, build optimizado |
| **Docker Compose** | Un solo comando levanta los servicios (Django + React). SQL Server corre en tu máquina local |
| **Circuit Breaker** | Evita agotar recursos esperando a un servicio caído — falla rápida con reintento automático |

---

## 🏗️ Arquitectura

### Diagrama de flujo

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│   React SPA  │────▶│                  │────▶│              │     │              │
│  Puerto 3000 │     │   Django API     │────▶│  SimpleAPI   │────▶│     SII      │
│              │     │   Puerto 8000    │     │  (HTTP/JSON) │     │  (Boletas)   │
└──────────────┘     │                  │     └──────────────┘     └──────────────┘
                      │  ┌─────────────┐ │
                      │  │ Circuit     │ │
                      │  │ Breaker     │ │
                      │  └─────────────┘ │
                      └──────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  SQL Server (LOCAL) │
                    │  Puerto 1433        │
                    │  host.docker.internal│
                    └─────────────────────┘
```

### Flujo de emisión de boleta

```
The Cloe → POST /api/v1/integraciones/emitir-boleta/
  1. Valida DTO con Pydantic (id_venta, items con nombre/cantidad/precio)
  2. Verifica Circuit Breaker (¿SimpleAPI disponible?)
  3. Obtiene credenciales activas de la BD
  4. Transforma VentaDTO → payload SII (Encabezado, Detalle, Totales)
  5. POST a SimpleAPI /dte/emitir con Bearer token
  6. Si éxito: guarda DocumentoTributario en SQL Server (id_venta, folio, estado)
  7. Si error: registra falla en Circuit Breaker, retorna 502
  8. Retorna { id_venta, folio, estado, monto_total }
```

### Estructura del proyecto

```
TheCloeIntegration/
│
├── backend/                         # Proyecto Django
│   ├── config/                      # Configuración del proyecto
│   │   ├── __init__.py
│   │   ├── settings.py              # Settings: DB, DRF, CORS, apps
│   │   ├── urls.py                  # URL conf global
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── core/                        # Utilidades compartidas
│   │   ├── circuit_breaker.py       # Patrón Circuit Breaker (CLOSED/OPEN/HALF_OPEN)
│   │   └── config.py                # Dataclasses con config desde Django settings
│   │
│   ├── integrations/                # App principal: emisión y consulta
│   │   ├── models.py                # DocumentoTributario, LogConsulta
│   │   ├── serializers.py           # VentaEmitirSerializer, DocumentoTributarioSerializer
│   │   ├── views.py                 # IntegracionViewSet (emitir, consultar, reportes)
│   │   ├── urls.py                  # Router DRF
│   │   └── admin.py                 # Admin Django
│   │
│   ├── credentials/                 # Gestión de API Keys
│   │   ├── models.py                # CredencialSimpleAPI
│   │   ├── serializers.py
│   │   ├── views.py                 # CredencialViewSet (CRUD)
│   │   └── admin.py
│   │
│   ├── configurations/              # Configuración de la integración
│   │   ├── models.py                # ConfiguracionIntegracion (empresa, timbrado, ambiente)
│   │   ├── serializers.py
│   │   ├── views.py                 # ConfiguracionViewSet
│   │   └── admin.py
│   │
│   ├── reports/                     # Dashboard y reportes
│   │   ├── models.py                # (sin modelos propios, consulta integrations)
│   │   ├── serializers.py           # ResumenReporteSerializer, EstadoDocumentoSerializer
│   │   ├── views.py                 # ReporteViewSet (resumen, por_estado, historial, logs)
│   │   └── urls.py
│   │
│   ├── manage.py                    # CLI de Django
│   └── requirements.txt             # Dependencias Python
│
├── frontend/                        # Proyecto React
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts            # Axios instance con baseURL /api/v1
│   │   ├── components/              # Componentes reutilizables
│   │   │   ├── Layout.tsx           # Sidebar + main layout
│   │   │   ├── Card.tsx             # Card wrapper
│   │   │   └── Button.tsx           # Button con variants
│   │   ├── pages/                   # Páginas de la aplicación
│   │   │   ├── Dashboard.tsx        # KPIs: total, emitidos, rechazados, monto
│   │   │   ├── EmitirBoleta.tsx     # Formulario de emisión con items dinámicos
│   │   │   ├── Consulta.tsx         # Búsqueda por ID de venta
│   │   │   ├── Configuracion.tsx    # Credenciales + configuración de integración
│   │   │   └── Reportes.tsx         # Resumen ejecutivo + estados
│   │   ├── App.tsx                  # Router con react-router-dom
│   │   ├── main.tsx                 # Entry point
│   │   └── index.css                # Tailwind directives
│   │
│   ├── index.html
│   ├── package.json                 # React 19, Vite, TailwindCSS, TypeScript
│   ├── vite.config.ts               # Proxy /api → http://django:8000
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   └── Dockerfile.dev
│
├── docker-compose.yml               # Orquesta django + react (sqlserver corre local)
├── Dockerfile.backend               # Python 3.12 + ODBC Driver 17
├── Dockerfile.frontend              # Node 22 Alpine multi-stage
├── .env                             # Variables de entorno (secretas)
├── .env.example                     # Template de variables
└── README.md                        # Este archivo
```

---

## 🚀 Cómo correr el proyecto

### Requisitos previos

- **Docker** 20.10+ y **Docker Compose** v2+ instalados
- **Git** para clonar el repositorio
- **Node.js 22+** solo si se quiere ejecutar el frontend localmente sin Docker
- **SQL Server** instalado localmente (2022 Express o Developer) con conexión en puerto 1433

### SQL Server local — configuración rápida

1. **Instalar SQL Server 2022** (Developer o Express) desde [docs.microsoft.com](https://docs.microsoft.com/en-us/sql/sql-server/install/install-sql-server)
2. **Habilitar modo de autenticación mixto** (SQL Authentication + Windows Authentication) durante la instalación
3. **Crear el login `sa`** con una contraseña segura (8+ caracteres, mayúscula, minúscula, número, especial)
4. **Habilitar TCP/IP** en SQL Server Configuration Manager → Protocolos → TCP/IP → Activado
5. **Verificar que el puerto 1433** está escuchando:
   ```bash
   # PowerShell
   Test-NetConnection -ComputerName localhost -Port 1433
   ```
6. **Crear la base de datos** (opcional — Django crea las tablas automáticamente con `migrate`):
   ```sql
   CREATE DATABASE the_cloe;
   ```

### Paso 1: Clonar y configurar el entorno

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd TheCloeIntegration

# Copiar el archivo de entorno y configurar
cp .env.example .env

# Editar .env con las credenciales reales
nano .env
```

**Variables clave en `.env`:**

```bash
# Django
DJANGO_SECRET_KEY=tu-clave-secreta-cambiar-en-produccion
DEBUG=True

# Base de Datos - SQL Server (LOCAL)
# SQL Server corre en tu máquina, Django en Docker se conecta vía host.docker.internal
DB_HOST=host.docker.internal
DB_PORT=1433
DB_NAME=the_cloe
DB_USER=sa
DB_PASSWORD=TuPasswordFuerte!123

# SimpleAPI (SII)
SIMPLEAPI_KEY=tu-api-key-real
SIMPLEAPI_BASE_URL=https://api.simpleapi.cl/api/v1
SIMPLEAPI_TIMEOUT=30

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30

# CORS
CORS_ORIGINS=http://localhost:3000
```

### Paso 2: Levantar todo con un solo comando

```bash
# Construye imágenes y levanta los servicios (Django + React)
docker compose up --build

# Para correr en segundo plano
docker compose up --build -d

# Para detener todo
docker compose down

# Para detener y eliminar volúmenes (resetear BD)
docker compose down -v
```

**¿Qué pasa cuando ejecutas `docker compose up --build`?**

1. **Django** se construye con Python 3.12 + ODBC Driver 17
   - Instala dependencias de `requirements.txt`
   - **Retry loop**: intenta `migrate` hasta que SQL Server local esté listo (30 intentos, 2s entre cada uno)
   - Ejecuta `python manage.py migrate` (crea todas las tablas automáticamente)
   - Inicia servidor en `0.0.0.0:8000`

2. **React** se construye con Node 22 + Vite
   - Instala dependencias de `package.json`
   - Inicia dev server en `0.0.0.0:3000`
   - **Proxy**: `/api` → `http://localhost:8000` (conecta al Django en Docker)

> **Nota**: SQL Server debe estar corriendo localmente antes de levantar Django. Los contenedores se conectan a `host.docker.internal:1433`.

### Paso 3: Verificar que todo corre

```bash
# Verificar que los contenedores están activos
docker compose ps

# Ver logs en tiempo real
docker compose logs -f django
```

Deberías ver:
- Django: `Esperando SQL Server local...` → `System check identified no issues` → `Starting development server`
- React: `VITE v6.x.x ready in xxx ms`

### Paso 4: Acceder a las interfaces

| Servicio | URL | Descripción |
|---------|-----|-------------|
| **Frontend React** | http://localhost:3000 | Dashboard, emisión, consulta, reportes |
| **API REST (DRF)** | http://localhost:8000 | Todos los endpoints JSON |
| **Swagger UI** | http://localhost:8000/swagger/ | Documentación interactiva auto-generada |
| **ReDoc** | http://localhost:8000/redoc/ | Documentación alternativa |
| **Admin Django** | http://localhost:8000/admin/ | Panel de administración (crear superusuario) |
| **SQL Server** | localhost:1433 | Para conectar con SSMS, DBeaver, etc. |

**Para crear un superusuario de Django Admin:**

```bash
docker compose exec django python manage.py createsuperuser
```

---

## 📡 Endpoints de la API

Todos los endpoints están bajo el prefijo `/api/v1/`.

### Integración Tributaria

| Método | Endpoint | Cuerpo | Descripción |
|--------|----------|--------|-------------|
| `POST` | `/integraciones/emitir-boleta/` | `{id_venta, items: [{nombre_producto, cantidad, precio_unitario}]}` | Emite boleta vía SimpleAPI |
| `GET` | `/integraciones/consulta/{id_venta}/` | — | Consulta documento por ID de venta |
| `GET` | `/integraciones/reportes/` | — | Estadísticas: total, emitidos, rechazados, monto |
| `GET` | `/integraciones/estado-circuito/` | — | Estado del Circuit Breaker (CLOSED/OPEN/HALF_OPEN) |
| `GET` | `/integraciones/` | — | Lista todos los documentos tributarios |

### Credenciales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/credenciales/` | Lista credenciales |
| `POST` | `/credenciales/` | Agrega nueva credencial |
| `GET` | `/credenciales/{id}/` | Detalle de credencial |
| `PUT` | `/credenciales/{id}/` | Actualiza credencial |
| `DELETE` | `/credenciales/{id}/` | Elimina credencial |

### Configuración

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/configuracion/` | Obtiene configuración activa |
| `POST` | `/configuracion/` | Crea nueva configuración (desactiva la anterior) |
| `PUT` | `/configuracion/{id}/` | Actualiza configuración |

### Reportes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/reportes/resumen/` | Resumen ejecutivo (7 días, 30 días, tasa éxito) |
| `GET` | `/reportes/por-estado/` | Documentos agrupados por estado |
| `GET` | `/reportes/historial/?limit=20` | Últimos documentos emitidos |
| `GET` | `/reportes/logs/?limit=50` | Logs de consultas realizadas |

### Ejemplo de petición de emisión

```bash
curl -X POST http://localhost:8000/api/v1/integraciones/emitir-boleta/ \
  -H "Content-Type: application/json" \
  -d '{
    "id_venta": "V-2026-08-001",
    "items": [
      {"nombre_producto": "Sándwich de Bulgogi", "cantidad": 2, "precio_unitario": 6500},
      {"nombre_producto": "Bebida Express", "cantidad": 2, "precio_unitario": 1500}
    ]
  }'
```

### Ejemplo de respuesta exitosa

```json
{
  "id_venta": "V-2026-08-001",
  "folio": 12345,
  "estado": "EMITIDO",
  "monto_total": 16000,
  "tipo_documento": 39,
  "message": "Boleta emitida correctamente"
}
```

---

## 🗄️ Modelos de la Base de Datos

### `documentos_tributarios`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | BigAutoField | PK |
| `id_venta` | CharField(50), único | ID interno de The Cloe |
| `folio` | IntegerField, nullable | Folio asignado por el SII |
| `tipo_documento` | IntegerField (default 39) | Tipo DTE SII (39 = Boleta) |
| `estado` | CharField(20) | PENDIENTE / EMITIDO / RECHAZADO / ANULADO |
| `respuesta_sii` | JSONField, nullable | Respuesta cruda del SII |
| `mensaje_error` | TextField, nullable | Error si estado es RECHAZADO |
| `monto_total` | DecimalField(12,2) | Monto total de la venta |
| `fecha_creacion` | DateTimeField | Auto Now Add |
| `fecha_actualizacion` | DateTimeField | Auto Now |

### `credenciales_simpleapi`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | BigAutoField | PK |
| `nombre` | CharField(100) | Identificador de credenciales |
| `api_key` | CharField(255) | API Key de SimpleAPI |
| `base_url` | URLField | URL base de SimpleAPI |
| `activa` | BooleanField | Credencial activa o no |
| `fecha_creacion` | DateTimeField | Auto Now Add |
| `fecha_actualizacion` | DateTimeField | Auto Now |

### `configuracion_integracion`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | BigAutoField | PK |
| `empresa` | CharField(200) | Nombre de la empresa |
| `timbrado` | CharField(20) | Número de timbrado |
| `prefijo_folio` | CharField(10) | Prefijo para folios |
| `ambiente` | CharField(20) | produccion / testing |
| `activa` | BooleanField | Configuración activa |

### `log_consultas`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | BigAutoField | PK |
| `tipo_consulta` | CharField(20) | EMISION / CONSULTA / REPORTE |
| `id_venta_ref` | CharField(50) | ID de venta referenciada |
| `parametros` | JSONField | Parámetros de la consulta |
| `respuesta` | JSONField | Respuesta obtenida |
| `fecha_consulta` | DateTimeField | Fecha de la consulta |

---

## ⚙️ Patrones Arquitectónicos Implementados

### Circuit Breaker

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   CLOSED     │───▶│   OPEN       │───▶│  HALF_OPEN   │
│  (Normal)    │    │ (Servicio    │    │ (Prueba de   │
│              │    │  caído)      │    │  recuperación)│
└──────────────┘    └──────────────┘    └──────────────┘
     ▲                                             │
     │              recovery_timeout               │ Éxito
     │                 (30s)                       │
     └─────────────────────────────────────────────┘
```

- **CLOSED**: Las peticiones pasan normalmente. Se registra éxito o falla.
- **OPEN**: Si fallas consecutivas ≥ umbral (3), el circuito se abre. Las peticiones se rechazan inmediatamente con error.
- **HALF_OPEN**: Tras el timeout de recuperación (30s), se permite una petición de prueba. Si succeede → CLOSED. Si falla → OPEN.

### DTO (Data Transfer Object)

- `VentaEmitirSerializer`: Contrato de entrada — valida `id_venta` y `items` con tipado estricto
- `DocumentoTributarioSerializer`: Contrato de salida — expone solo campos necesarios
- Validación automática: tipos, rangos, campos obligatorios

### DAO (Data Access Object)

- Los modelos de Django actúan como DAO — aíslan toda la persistencia SQL
- Solo los modelos tienen acceso directo a la base de datos
- Las vistas (ViewSets) no ejecutan SQL directamente

### SOLID

- **SRP**: Cada app tiene una responsabilidad (integración, credenciales, configuración, reportes)
- **OCP**: Los serializers y ViewSets son extensibles sin modificar código existente
- **DIP**: La configuración se inyecta desde Django settings, no está hardcodeada

---

## 🐳 Docker

### Servicios

| Servicio | Imagen | Puerto | Depende de |
|----------|--------|--------|------------|
| `django` | `python:3.12-slim-bookworm` (build) | 8000 | SQL Server local (1433) |
| `react` | `node:22-alpine` (build) | 3000 | django |

> **SQL Server** corre en tu máquina local (no en Docker). Se conecta vía `host.docker.internal:1433`.

### Archivos Docker

- `Dockerfile.backend`: Instala ODBC Driver 17 para SQL Server + dependencias Python
- `Dockerfile.frontend`: Build multi-stage (instalación + compilación + serve)
- `Dockerfile.dev`: Dev-only para React con hot-reload
- `docker-compose.yml`: Orquesta Django + React con conexión a SQL Server local

### Red

- `thecloe-network` (bridge): Django y React se comunican dentro de la red Docker.

### Volúmenes

- `./backend:/app`: Bind mount para hot-reload del código Django en desarrollo
- `./frontend:/app`: Bind mount para hot-reload del código React en desarrollo
- `/app/node_modules`: Anonymous volume para no sobreescribir node_modules del host

### Conexión a SQL Server local

Django (en Docker) se conecta a SQL Server (en tu máquina) vía `host.docker.internal`:
- `host.docker.internal` es un DNS especial de Docker que resuelve a la IP de la máquina host
- Django usa `DB_HOST=host.docker.internal` en `.env`
- React usa `VITE_DJANGO_URL=http://host.docker.internal:8000` para el proxy de la API
- El puerto 1433 de SQL Server debe estar accesible desde Docker (firewall de Windows permitirlo)

---

## 🔧 Solución de Problemas

### SQL Server no está accesible desde Docker

SQL Server corre en tu máquina local pero Django (en Docker) no puede conectar.

```bash
# 1. Verificar que SQL Server está corriendo en tu máquina
# Abrir SQL Server Configuration Manager o services.ms
# El servicio "SQL Server (SQLEXPRESS)" debe estar "En ejecución"

# 2. Verificar que SQL Server escucha en TCP/IP y puerto 1433
# SQL Server Configuration Manager → Protocolos → TCP/IP → Activado
# Puerto TCP: 1433

# 3. Verificar que la IP de tu máquina es accesible desde Docker
# En PowerShell:
Test-NetConnection -ComputerName host.docker.internal -Port 1433

# 4. Verificar que SA_PASSWORD coincide entre .env y tu instancia SQL Server
# Dentro del container Django:
docker compose exec django python manage.py migrate --run-syncdb

# 5. Verificar que el ODBC Driver 17 está instalado en el container
docker compose exec django bash
apt list --installed | grep msodbcsql
```

### Django no puede conectar a SQL Server

SQL Server corre en tu máquina local pero Django (en Docker) no logra conectar.

```bash
# 1. Verificar que SQL Server está corriendo en tu máquina
# SQL Server Configuration Manager → El servicio debe estar "En ejecución"

# 2. Verificar que el puerto 1433 está accesible desde Docker
# En PowerShell:
Test-NetConnection -ComputerName host.docker.internal -Port 1433

# 3. Verificar que DB_PASSWORD en .env coincide con el password de SA en SQL Server
# Dentro del container Django:
docker compose exec django bash
apt list --installed | grep msodbcsql

# 4. Verificar que el ODBC Driver 17 está instalado en el container
docker compose exec django python -c "import pyodbc; print(pyodbc.drivers())"

# 5. Si todo está bien, forzar migración:
docker compose exec django python manage.py migrate --run-syncdb
```

### Migraciones fallan

```bash
# Ejecutar migraciones manualmente dentro del container
docker compose exec django python manage.py makemigrations
docker compose exec django python manage.py migrate

# Si hay problemas, resetear la BD
docker compose down -v
docker compose up --build
```

### El frontend no conecta con el backend

React (en Docker) accede a Django (en tu máquina local) vía `host.docker.internal`.

```bash
# Verificar que VITE_DJANGO_URL en docker-compose.yml es http://host.docker.internal:8000
# (host.docker.internal resuelve a la IP de tu máquina desde dentro de Docker)

# Verificar que el proxy en vite.config.ts usa VITE_DJANGO_URL
# target: import.meta.env.VITE_DJANGO_URL || 'http://localhost:8000'

# Probar la API directamente desde el navegador
curl http://localhost:8000/api/v1/integraciones/
```

### Puerto 3000 u 8000 ya está en uso

```bash
# Encontrar y matar el proceso
# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :3000
kill -9 <PID>
```

---

## 📁 Estructura de Archivos Clave

```
.env                        # Variables de entorno (NUNCA commitizar secretos)
.env.example                # Template visible al público
docker-compose.yml          # Orquestación de 3 servicios
Dockerfile.backend          # Imagen del backend Django
Dockerfile.frontend         # Imagen del frontend React (producción)
frontend/Dockerfile.dev     # Imagen del frontend React (desarrollo)

backend/
  requirements.txt          # Dependencias Python
  config/settings.py        # Configuración central del proyecto
  core/circuit_breaker.py   # Implementación Circuit Breaker
  integrations/             # Lógica principal de emisión
  credentials/              # Gestión de API Keys
  configurations/           # Configuración de empresa/timbrado
  reports/                  # Dashboard y reportes

frontend/
  package.json              # Dependencias Node
  vite.config.ts            # Configuración del dev server + proxy
  src/
    api/client.ts           # Axios instance
    components/             # Layout, Card, Button
    pages/                  # Dashboard, EmitirBoleta, Consulta, Configuración, Reportes
    App.tsx                 # Routing
```

---

## 🧪 Testing (Próximamente)

- **Django**: Tests unitarios con `python manage.py test` para cada app
- **DRF**: Tests de endpoints con `APITestCase`
- **Circuit Breaker**: Tests del patrón (transiciones CLOSED → OPEN → HALF_OPEN)
- **React**: Tests con Vitest + React Testing Library (por definir)

---

## 📄 Licencia

Proyecto académico - Integración Tributaria The Cloe / SII SimpleAPI

---

## 📝 Historial de Cambios

### v2.0.0 — Reescritura completa
- Migración de FastAPI + SQLite a **Django + DRF + SQL Server**
- Agregado **frontend React** con dashboard completo
- Implementado **Circuit Breaker** como módulo reutilizable
- **Docker Compose** con 3 servicios y healthchecks
- **Migrations automáticas** con Django ORM
- **Admin Django** para gestión de datos

### v1.0.0 — Versión original FastAPI
- Microservicio FastAPI + SQLite
- Circuit Breaker implementado
- Integración con SimpleAPI (mock)
- Sin interfaz web
