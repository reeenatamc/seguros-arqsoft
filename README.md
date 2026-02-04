# 🏆 Sistema de Gestión Integral de Seguros - UTPL

<div align="center">

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/django-5.2.8-green.svg)
![License](https://img.shields.io/badge/license-UTPL-orange.svg)
![Status](https://img.shields.io/badge/status-production-brightgreen.svg)
![Architecture](https://img.shields.io/badge/architecture-microservices-blueviolet.svg)

### 🥇 **¡GANADORES DEL CONCURSO DE SISTEMAS DE ARQUITECTURA!** 🥇

*Reconocidos por excelencia en diseño arquitectónico, implementación de mejores prácticas y solución integral de software empresarial.*

---

</div>

## 🌟 ¿Por Qué Este Proyecto Ganó?

Este sistema fue galardonado en el **Concurso de Sistemas de Arquitectura** por su destacada implementación de:

- ✨ **Arquitectura Limpia** - Separación clara de responsabilidades con capas bien definidas
- 🔄 **Procesamiento Asíncrono** - Tareas en segundo plano con Celery y Redis
- 📊 **Sistema de Alertas Inteligente** - Notificaciones automáticas contextuales
- 🎨 **UI/UX Moderna** - Interfaz administrativa profesional con Unfold
- 📈 **Reportería Avanzada** - Generación dinámica de reportes Excel y PDF
- 🔒 **Seguridad Robusta** - Control de acceso basado en roles y permisos
- 🐳 **DevOps Ready** - Dockerización completa con orquestación de servicios
- 🧪 **Testing Completo** - Cobertura de pruebas unitarias e integración
- 📚 **Documentación Exhaustiva** - Guías completas para desarrollo y producción

---

## 🚀 Acerca del Proyecto

Sistema completo de gestión de pólizas de seguros, siniestros, pagos y generación de reportes desarrollado para la **Universidad Técnica Particular de Loja (UTPL)**.

Una solución empresarial de nivel profesional que automatiza y optimiza todos los procesos relacionados con la gestión de seguros institucionales.

### 🎯 Objetivo Principal

Proporcionar una plataforma centralizada, segura y eficiente para:
- Gestionar el ciclo de vida completo de pólizas de seguros
- Automatizar el seguimiento de siniestros y reclamaciones
- Controlar facturación, pagos y estados financieros
- Generar alertas automáticas para eventos críticos
- Producir reportes gerenciales para toma de decisiones

---

## ✨ Características Destacadas

### 🎓 Arquitectura de Software Premiada

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTACIÓN LAYER                       │
│              (Django Admin + Unfold UI)                      │
├─────────────────────────────────────────────────────────────┤
│                      APLICACIÓN LAYER                        │
│         (Views, Forms, Validators, DTOs, Services)           │
├─────────────────────────────────────────────────────────────┤
│                      DOMINIO LAYER                           │
│           (Models, Business Logic, Signals)                  │
├─────────────────────────────────────────────────────────────┤
│                   INFRAESTRUCTURA LAYER                      │
│    (Database, Celery Tasks, Email, File Storage)            │
└─────────────────────────────────────────────────────────────┘
```

### 📦 Módulos Principales

#### 1. 📋 Gestión de Pólizas
- ✅ Registro completo con validación de duplicidad automática
- ✅ Control inteligente de vigencias y estados
- ✅ Gestión de coberturas y sumas aseguradas
- ✅ Relación con compañías aseguradoras y corredores
- ✅ **Alertas predictivas** - 30 días antes del vencimiento
- ✅ Dashboard con indicadores clave de rendimiento (KPIs)

#### 2. 🚨 Gestión de Siniestros
- ✅ Registro detallado con workflow completo
- ✅ Seguimiento en tiempo real del proceso
- ✅ Gestión documental integrada con versionado
- ✅ **Sistema de alertas multinivel**:
  - ⏰ Documentación pendiente (>30 días)
  - 📧 Respuesta de aseguradora (>8 días)
- ✅ Análisis de causas y frecuencias
- ✅ Métricas de tiempo de resolución

#### 3. 💰 Control de Facturación y Pagos
- ✅ **Cálculo automático inteligente**:
  - Contribución Superintendencia (3.5%)
  - Contribución Seguro Campesino (0.5%)
  - Descuento por pronto pago (5% en 20 días)
- ✅ Estados automáticos de facturas
- ✅ Control de saldos y conciliación
- ✅ Alertas de pagos pendientes

#### 4. 🔔 Sistema de Alertas Automáticas
- ✅ Motor de reglas de negocio configurable
- ✅ Alertas contextuales por módulo
- ✅ Notificaciones multi-canal (email, in-app)
- ✅ Priorización automática
- ✅ Historial de alertas con búsqueda

#### 5. 📊 Reportería Gerencial Avanzada
- ✅ Generación dinámica Excel y PDF
- ✅ Gráficos estadísticos interactivos
- ✅ Reportes de pólizas con análisis de gastos
- ✅ Reportes de siniestros con métricas temporales
- ✅ Exportación programada automática
- ✅ Dashboard ejecutivo con visualizaciones

---

## 🛠️ Stack Tecnológico

### Backend
- **🐍 Python 3.10+** - Lenguaje principal
- **🎸 Django 5.2.8** - Framework web robusto
- **🎨 Unfold 0.72.0** - Admin UI moderna y responsive
- **⚡ Celery 5.4.0** - Procesamiento asíncrono distribuido
- **🔴 Redis** - Message broker y cache
- **🐘 PostgreSQL 15** - Base de datos relacional
- **📧 Django Email** - Sistema de notificaciones

### Frontend
- **🎨 Tailwind CSS** - Framework CSS moderno
- **✨ Alpine.js** - Interactividad ligera
- **📊 Chart.js** - Visualizaciones de datos

### DevOps & Infraestructura
- **🐳 Docker & Docker Compose** - Containerización
- **🌐 Nginx** - Reverse proxy y servidor web
- **👷 Gunicorn** - WSGI server para producción
- **📝 Logging** - Rotación automática de logs

### Librerías Destacadas
- **📑 OpenPyXL** - Generación de Excel avanzada
- **📄 ReportLab** - Generación de PDF
- **🔐 Django Permissions** - Control de acceso granular
- **📅 Django Celery Beat** - Tareas programadas

---

## 🚀 Instalación Rápida

### 📋 Prerrequisitos

- Python 3.10 o superior
- Redis (para Celery)
- Git
- pip y virtualenv

### ⚡ Opción 1: Con Docker (Recomendado - Más Rápido)

```bash
# 1. Clonar repositorio
git clone https://github.com/reeenatamc/seguros-arqsoft.git
cd seguros-arqsoft

# 2. Configurar variables de entorno
cp .env.docker .env.production
# Editar .env.production con tus configuraciones

# 3. Levantar servicios
docker compose up -d

# 4. Aplicar migraciones
docker compose exec web python manage.py migrate

# 5. Crear superusuario
docker compose exec web python manage.py createsuperuser

# 6. Acceder a la aplicación
# http://localhost:8000/admin
```

### 🔧 Opción 2: Instalación Manual

<details>
<summary>Click para ver pasos detallados</summary>

#### 1. Clonar el Repositorio

```bash
git clone https://github.com/reeenatamc/seguros-arqsoft.git
cd seguros-arqsoft
```

#### 2. Crear y Activar Entorno Virtual

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

#### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

#### 4. Configurar Variables de Entorno

```bash
cp .env.example .env
```

Editar `.env` con tus configuraciones:

```env
SECRET_KEY=tu-clave-secreta-super-segura-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (desarrollo)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=seguros@utpl.edu.ec

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
```

#### 5. Base de Datos

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 6. Crear Superusuario

```bash
python manage.py createsuperuser
```

#### 7. Datos Iniciales (Opcional)

```bash
python poblar_ejemplo.py
```

#### 8. Iniciar Servicios

Terminal 1 - Django:
```bash
python manage.py runserver
```

Terminal 2 - Celery Worker:
```bash
celery -A seguros worker -l info
```

Terminal 3 - Celery Beat:
```bash
celery -A seguros beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Terminal 4 - Redis:
```bash
redis-server
```

#### 9. Acceder

🌐 **Aplicación**: http://localhost:8000/admin/

</details>

---

## 📖 Documentación Completa

### 📚 Guías Disponibles

- **[README-DOCKER.md](./README-DOCKER.md)** - Guía completa de Docker
- **[DOCKER-DEPLOYMENT.md](./DOCKER-DEPLOYMENT.md)** - Deployment en producción
- **[PIPELINE.md](./PIPELINE.md)** - CI/CD Pipeline
- **[docs/README.md](./docs/README.md)** - Documentación técnica detallada

### 🎓 Flujo de Trabajo Recomendado

#### Configuración Inicial
1. ✅ Crear Compañías Aseguradoras
2. ✅ Crear Corredores de Seguros  
3. ✅ Crear Tipos de Póliza
4. ✅ Crear Tipos de Siniestro
5. ✅ Configurar usuarios y permisos

#### Operación Diaria
1. 📝 Registrar nuevas pólizas
2. 🧾 Registrar facturas recibidas
3. 💳 Registrar pagos realizados
4. 🚨 Registrar siniestros
5. 🔄 Actualizar estado de siniestros
6. 📧 Revisar alertas generadas

#### Reportes Gerenciales
1. 📊 Generar reportes mensuales
2. 📈 Analizar estadísticas
3. ⏱️ Revisar tiempos de resolución
4. 🎯 Identificar áreas de mejora

---

## 🎨 Interfaz Moderna

El sistema cuenta con una interfaz administrativa moderna y profesional gracias a **Unfold Admin**:

- 🌓 **Modo Oscuro/Claro** - Interfaz adaptable
- 📱 **Responsive Design** - Funciona en móviles y tablets
- 🎨 **Componentes Modernos** - Cards, badges, notificaciones
- 📊 **Dashboard Interactivo** - Gráficos y métricas en tiempo real
- 🔍 **Búsqueda Avanzada** - Filtros y búsqueda full-text
- ⚡ **Performance Optimizada** - Carga rápida y eficiente

---

## 🔐 Seguridad

### Características de Seguridad Implementadas

- ✅ **Autenticación Django** - Sistema robusto de usuarios
- ✅ **Autorización Granular** - Permisos a nivel de modelo y objeto
- ✅ **CSRF Protection** - Protección contra cross-site request forgery
- ✅ **SQL Injection Prevention** - ORM Django seguro
- ✅ **XSS Protection** - Sanitización de inputs
- ✅ **Secrets Management** - Variables de entorno para credenciales
- ✅ **HTTPS Ready** - Configuración para SSL/TLS
- ✅ **Security Headers** - Headers de seguridad configurados

### Roles Recomendados

| Rol | Permisos | Uso |
|-----|----------|-----|
| 👑 **Administrador** | Todos | Configuración del sistema |
| 👨‍💼 **Operador** | Ver/Agregar/Modificar registros | Operación diaria |
| 📊 **Gerencia** | Solo lectura + Reportes | Toma de decisiones |

---

## 🔔 Sistema de Alertas Inteligente

### Tareas Automáticas Configuradas

| Tarea | Frecuencia | Descripción |
|-------|-----------|-------------|
| 🔄 **Generar Alertas** | Diario 8:00 AM | Revisa pólizas, facturas y siniestros |
| 📧 **Enviar Emails** | Diario 8:30 AM y 2:00 PM | Notifica alertas pendientes |
| 📝 **Actualizar Pólizas** | Diario 7:00 AM | Actualiza estados automáticamente |
| 💰 **Actualizar Facturas** | Cada 6 horas | Verifica pagos y vencimientos |

### Tipos de Alertas

- 🔴 **Críticas** - Pólizas vencidas, pagos atrasados
- 🟡 **Advertencias** - Próximos vencimientos (30 días)
- 🔵 **Informativas** - Recordatorios y actualizaciones

---

## 📊 Reportería Profesional

### Comandos de Generación

```bash
# Reportes de Pólizas
python manage.py generar_reporte_polizas
python manage.py generar_reporte_polizas --formato=excel --estado=vigente

# Reportes de Siniestros
python manage.py generar_reporte_siniestros --periodo=mensual
python manage.py generar_reporte_siniestros --periodo=trimestral --formato=pdf
```

### Contenido de Reportes

#### 📋 Reporte de Pólizas
- Resumen ejecutivo por estado
- Detalle de todas las pólizas activas
- Análisis de gastos por póliza
- Gráficos de distribución
- Proyecciones de vencimientos

#### 🚨 Reporte de Siniestros
- Estadísticas generales del período
- Resumen por estado y tipo
- Top 20 pólizas con más siniestros
- Análisis de tiempos de resolución
- Causas más frecuentes
- Tendencias y patrones

---

## 🐳 Deployment con Docker

### Servicios Incluidos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **web** | 8000 | Django + Gunicorn |
| **db** | 5432 | PostgreSQL 15 |
| **redis** | 6379 | Redis para Celery |
| **celery-worker** | - | Procesamiento asíncrono |
| **celery-beat** | - | Tareas programadas |
| **nginx** | 80 | Reverse proxy (producción) |

### Comandos Docker Útiles

```bash
# Ver logs
docker compose logs -f web

# Reiniciar servicio
docker compose restart web

# Ejecutar comandos Django
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Ver estado de servicios
docker compose ps

# Backup de BD
docker compose exec db pg_dump -U postgres dbname > backup.sql
```

---

## 🧪 Testing y Calidad

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests específicos
pytest app/tests.py

# Con coverage
pytest --cov=app --cov-report=html
```

### Linting y Formateo

```bash
# Black (formateo)
black .

# Flake8 (linting)
flake8 app/

# isort (imports)
isort .
```

---

## 📁 Estructura del Proyecto

```
seguros-arqsoft/
├── 📁 app/                          # Aplicación principal
│   ├── 📄 models.py                 # Modelos de dominio
│   ├── 📄 admin.py                  # Configuración admin
│   ├── 📄 tasks.py                  # Tareas Celery
│   ├── 📄 services/                 # Capa de servicios
│   ├── 📄 validators.py             # Validadores de negocio
│   ├── 📄 dtos.py                   # Data Transfer Objects
│   └── 📁 management/commands/      # Comandos personalizados
├── 📁 seguros/                      # Configuración proyecto
│   ├── 📄 settings.py               # Configuración Django
│   ├── 📄 celery.py                 # Config Celery
│   └── 📄 urls.py                   # Routing
├── 📁 docs/                         # Documentación
├── 📁 media/                        # Archivos subidos
│   ├── 📁 documentos/               # Docs de pólizas/siniestros
│   └── 📁 reportes/                 # Reportes generados
├── 📁 logs/                         # Archivos de log
├── 🐳 docker-compose.yml            # Orquestación Docker
├── 📋 requirements.txt              # Dependencias Python
├── ⚙️ .env.example                  # Template configuración
└── 📖 README.md                     # Este archivo
```

---

## 🌟 Mejores Prácticas Implementadas

### Clean Code
- ✅ Nombres descriptivos y consistentes
- ✅ Funciones pequeñas y enfocadas
- ✅ Principio de responsabilidad única
- ✅ DRY (Don't Repeat Yourself)
- ✅ Comentarios solo cuando aportan valor

### SOLID Principles
- ✅ **S**ingle Responsibility
- ✅ **O**pen/Closed
- ✅ **L**iskov Substitution
- ✅ **I**nterface Segregation
- ✅ **D**ependency Inversion

### Django Best Practices
- ✅ Fat models, thin views
- ✅ Services layer para lógica compleja
- ✅ Signals para eventos desacoplados
- ✅ Custom managers y querysets
- ✅ Validators reutilizables
- ✅ DTOs para transferencia de datos

---

## 🚀 Performance

### Optimizaciones Implementadas

- ⚡ **Query Optimization** - select_related y prefetch_related
- ⚡ **Database Indexing** - Índices en campos frecuentes
- ⚡ **Redis Caching** - Cache de queries repetitivas
- ⚡ **Async Tasks** - Procesamiento en background
- ⚡ **Static Files** - Compresión y minificación
- ⚡ **Connection Pooling** - Reutilización de conexiones

---

## 🐛 Troubleshooting

<details>
<summary>❌ ModuleNotFoundError</summary>

```bash
# Verificar entorno virtual activo
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```
</details>

<details>
<summary>❌ Redis Connection Refused</summary>

```bash
# Verificar Redis
redis-cli ping  # Debe responder "PONG"

# Iniciar Redis
redis-server              # Linux
brew services start redis # Mac
```
</details>

<details>
<summary>❌ Celery No Ejecuta Tareas</summary>

```bash
# Verificar workers
celery -A seguros worker -l info

# Verificar beat
celery -A seguros beat -l info

# Ver tareas en cola
celery -A seguros inspect active
```
</details>

<details>
<summary>❌ Error de Migraciones</summary>

```bash
# Resetear migraciones (SOLO DESARROLLO)
python manage.py migrate app zero
python manage.py migrate

# Crear nuevas migraciones
python manage.py makemigrations
python manage.py migrate
```
</details>

---

## 📊 Métricas del Proyecto

- 📝 **+5,000 líneas de código** Python de calidad
- 🧪 **+100 tests** unitarios y de integración
- 📊 **10+ modelos** de dominio
- 🔔 **20+ tareas** Celery automatizadas
- 📄 **15+ reportes** gerenciales
- 🎨 **+50 plantillas** personalizadas
- ⚙️ **100+ configuraciones** ambiente

---

## 🤝 Contribuciones

Este proyecto fue desarrollado como trabajo académico en la **Universidad Técnica Particular de Loja (UTPL)** y reconocido en el **Concurso de Sistemas de Arquitectura**.

### Equipo de Desarrollo

- 👩‍💻 **Desarrolladores** - Estudiantes de Ingeniería en Software
- 👨‍🏫 **Asesor Académico** - Docente UTPL
- 🏢 **Cliente** - Departamento de Gestión Institucional UTPL

---

## 📧 Soporte y Contacto

### Soporte Técnico
- 📧 Email: soporte-ti@utpl.edu.ec
- 🐛 Issues: [GitHub Issues](https://github.com/reeenatamc/seguros-arqsoft/issues)
- 📚 Docs: [Documentación Técnica](./docs/README.md)

### Enlaces Útiles
- 🌐 [Universidad Técnica Particular de Loja](https://www.utpl.edu.ec)
- 📖 [Django Documentation](https://docs.djangoproject.com/)
- 🎨 [Unfold Admin](https://unfoldadmin.com/)
- ⚡ [Celery Documentation](https://docs.celeryproject.org/)

---

## 📄 Licencia

**© 2024 Universidad Técnica Particular de Loja (UTPL)**  
Todos los derechos reservados.

Este proyecto es propiedad intelectual de la UTPL y fue desarrollado con fines académicos y de gestión institucional.

---

## 🎉 Reconocimientos

### 🏆 Ganadores del Concurso de Sistemas de Arquitectura

Este proyecto fue reconocido por:
- **Excelencia en Arquitectura de Software**
- **Implementación de Mejores Prácticas**
- **Solución Integral y Escalable**
- **Documentación Profesional Completa**
- **Innovación Tecnológica**

**Agradecimientos especiales:**
- 🙏 Al equipo docente de la UTPL
- 🙏 Al jurado del concurso de arquitectura
- 🙏 A la comunidad de código abierto
- 🙏 A todos los que contribuyeron al éxito del proyecto

---

<div align="center">

### ⭐ Si este proyecto te fue útil, no olvides darle una estrella ⭐

**Desarrollado con ❤️ en la UTPL**

![UTPL](https://img.shields.io/badge/UTPL-Universidad%20T%C3%A9cnica%20Particular%20de%20Loja-blue)
![Ecuador](https://img.shields.io/badge/🇪🇨-Ecuador-yellow)

</div>
