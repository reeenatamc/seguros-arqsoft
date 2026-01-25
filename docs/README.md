# Sistema de Gestión Integral de Pólizas y Siniestros - UTPL

Sistema completo de gestión de pólizas de seguros, siniestros, pagos y generación de reportes para la Universidad Técnica Particular de Loja.

## 📋 Características Principales

### 1. Gestión de Pólizas
- ✅ Registro completo de pólizas con validación de duplicidad
- ✅ Control de vigencias y estados automáticos
- ✅ Gestión de coberturas y sumas aseguradas
- ✅ Relación con compañías aseguradoras y corredores
- ✅ Alertas automáticas para vencimientos

### 2. Gestión de Siniestros
- ✅ Registro detallado de siniestros
- ✅ Seguimiento completo del proceso
- ✅ Gestión documental integrada
- ✅ Alertas por tiempos de gestión
- ✅ Análisis de causas y frecuencias

### 3. Control de Facturación y Pagos
- ✅ Cálculo automático de contribuciones (3.5% + 0.5%)
- ✅ Descuento por pronto pago (5% en 20 días)
- ✅ Control de pagos y saldos
- ✅ Estados automáticos de facturas

### 4. Sistema de Alertas Automáticas
- ✅ Alertas de vencimiento de pólizas (30 días antes)
- ✅ Alertas de pagos pendientes
- ✅ Alertas de documentación pendiente (30 días)
- ✅ Alertas de respuesta de aseguradora (8 días)
- ✅ Notificaciones por correo electrónico

### 5. Reportes Gerenciales
- ✅ Reportes de pólizas (Excel y PDF)
- ✅ Reportes de siniestros con análisis estadístico
- ✅ Análisis por tipo de siniestro
- ✅ Tiempos de resolución
- ✅ Gastos por póliza

## 🚀 Instalación

### Requisitos Previos
- Python 3.10 o superior
- Redis (para Celery)
- pip (gestor de paquetes de Python)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/UTPL/seguros-arqsoft.git
cd seguros-arqsoft
```

### 2. Crear y Activar Entorno Virtual

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

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Copiar el archivo de ejemplo y configurar:

```bash
cp .env.example .env
```

Editar el archivo `.env` con tus configuraciones:

```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Configuración de Email (opcional para desarrollo)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=seguros@utpl.edu.ec

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
```

### 5. Crear Base de Datos y Aplicar Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear Superusuario

```bash
python manage.py createsuperuser
```

### 7. Crear Datos Iniciales (Opcional)

```bash
python manage.py shell

# En la consola de Django:
from app.models import TipoPoliza, TipoSiniestro

# Crear tipos de póliza
TipoPoliza.objects.create(nombre="Todo Riesgo", descripcion="Cobertura completa")
TipoPoliza.objects.create(nombre="Incendio y Líneas Aliadas", descripcion="Protección contra incendios")
TipoPoliza.objects.create(nombre="Robo y Asalto", descripcion="Protección contra robo")

# Crear tipos de siniestro
TipoSiniestro.objects.create(nombre="daño", descripcion="Daño a la propiedad")
TipoSiniestro.objects.create(nombre="robo", descripcion="Robo de bienes")
TipoSiniestro.objects.create(nombre="incendio", descripcion="Daño por incendio")

exit()
```

### 8. Iniciar el Servidor de Desarrollo

```bash
python manage.py runserver
```

El sistema estará disponible en: http://localhost:8000/admin/

## 📊 Uso del Sistema

### Acceso al Panel de Administración

1. Navegar a: http://localhost:8000/admin/
2. Iniciar sesión con las credenciales del superusuario
3. Interfaz moderna con Unfold Admin

### Gestión de Pólizas

**Crear una nueva póliza:**
1. Ir a "Pólizas" > "Agregar Póliza"
2. Completar todos los campos requeridos
3. El sistema validará automáticamente:
   - No duplicidad de pólizas con fechas superpuestas
   - Fechas de vigencia correctas
   - Estado automático según fechas

**Características automáticas:**
- Estado actualizado diariamente
- Alertas 30 días antes del vencimiento
- Cálculo de días para vencer

### Gestión de Facturas

**Crear una factura:**
1. Ir a "Facturas" > "Agregar Factura"
2. Seleccionar la póliza relacionada
3. Ingresar subtotal y otros datos
4. El sistema calculará automáticamente:
   - Contribución Superintendencia (3.5%)
   - Contribución Seguro Campesino (0.5%)
   - Descuento por pronto pago (si aplica)
   - Monto total

**Descuento por pronto pago:**
- 5% de descuento si se paga dentro de 20 días
- Se calcula automáticamente
- Alerta cuando quedan 5 días para aprovechar el descuento

### Gestión de Siniestros

**Registrar un siniestro:**
1. Ir a "Siniestros" > "Agregar Siniestro"
2. Completar información del bien afectado
3. Describir causa y detalles
4. Adjuntar documentación

**Seguimiento:**
- El sistema genera alertas automáticas:
  - Documentación pendiente > 30 días
  - Respuesta aseguradora > 8 días
- Actualización de estados manualmente
- Registro de fechas clave

### Documentos

**Adjuntar documentos:**
1. Desde cualquier registro (Póliza, Siniestro, Factura)
2. Click en "Documentos" en la parte inferior
3. Agregar nuevo documento con clasificación

**Tipos de documentos:**
- Pólizas de seguro
- Facturas
- Informes técnicos
- Denuncias
- Proformas
- Fotografías

## 🔔 Sistema de Alertas

### Configuración de Celery (Tareas Automáticas)

**1. Instalar Redis:**

**Linux/Mac:**
```bash
# Mac (con Homebrew)
brew install redis
brew services start redis

# Linux (Ubuntu/Debian)
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
Descargar Redis para Windows desde: https://github.com/microsoftarchive/redis/releases

**2. Iniciar Celery Worker:**

En una terminal separada:
```bash
celery -A seguros worker -l info
```

**3. Iniciar Celery Beat (Tareas Periódicas):**

En otra terminal separada:
```bash
celery -A seguros beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Tareas Automáticas Configuradas

| Tarea | Frecuencia | Descripción |
|-------|-----------|-------------|
| Generar Alertas | Diario 8:00 AM | Crea alertas para pólizas, facturas y siniestros |
| Enviar Emails | Diario 8:30 AM y 2:00 PM | Envía alertas pendientes por correo |
| Actualizar Pólizas | Diario 7:00 AM | Actualiza estados de pólizas |
| Actualizar Facturas | Cada 6 horas | Actualiza estados de facturas |

### Generar Alertas Manualmente

```bash
# Generar todas las alertas
python manage.py generar_alertas --tipo=todas

# Solo alertas de pólizas
python manage.py generar_alertas --tipo=polizas

# Solo alertas de facturas
python manage.py generar_alertas --tipo=facturas

# Solo alertas de siniestros
python manage.py generar_alertas --tipo=siniestros
```

### Enviar Alertas por Email

```bash
# Enviar alertas pendientes
python manage.py enviar_alertas_email

# Limitar cantidad
python manage.py enviar_alertas_email --max=50
```

## 📈 Generación de Reportes

### Reportes de Pólizas

```bash
# Generar reporte en ambos formatos (Excel y PDF)
python manage.py generar_reporte_polizas

# Solo Excel
python manage.py generar_reporte_polizas --formato=excel

# Solo PDF
python manage.py generar_reporte_polizas --formato=pdf

# Filtrar por estado
python manage.py generar_reporte_polizas --estado=vigente
python manage.py generar_reporte_polizas --estado=por_vencer
```

**Contenido del reporte:**
- Resumen ejecutivo por estado
- Detalle de todas las pólizas
- Gastos por póliza (facturación)
- Gráficos y estadísticas

### Reportes de Siniestros

```bash
# Reporte mensual (por defecto)
python manage.py generar_reporte_siniestros

# Reportes por período
python manage.py generar_reporte_siniestros --periodo=semanal
python manage.py generar_reporte_siniestros --periodo=mensual
python manage.py generar_reporte_siniestros --periodo=trimestral
python manage.py generar_reporte_siniestros --periodo=anual
python manage.py generar_reporte_siniestros --periodo=todo

# Formato específico
python manage.py generar_reporte_siniestros --formato=excel --periodo=mensual
```

**Contenido del reporte:**
- Estadísticas generales
- Resumen por estado
- Análisis por tipo de siniestro
- Análisis por póliza (top 20)
- Tiempos de resolución
- Causas frecuentes

**Ubicación de reportes:**
- Excel: `media/reportes/polizas/` y `media/reportes/siniestros/`
- PDF: Mismas ubicaciones

## 🔒 Seguridad y Roles

### Configuración de Usuarios

El sistema utiliza el sistema de permisos de Django. Para crear usuarios con diferentes roles:

```bash
python manage.py createsuperuser  # Administrador completo

# Luego desde el admin:
# 1. Crear grupos (Staff, Operadores, Gerencia)
# 2. Asignar permisos específicos
# 3. Agregar usuarios a grupos
```

### Permisos Recomendados por Rol

**Administrador:**
- Todos los permisos

**Operador:**
- Ver/Agregar/Modificar Pólizas
- Ver/Agregar/Modificar Siniestros
- Ver/Agregar/Modificar Facturas y Pagos
- Ver/Agregar Documentos

**Gerencia:**
- Ver todos los módulos
- Ver Reportes
- Ver Alertas

## 📧 Configuración de Email

### Desarrollo (Console Backend)

Por defecto, los emails se muestran en la consola:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Producción (SMTP)

Para enviar emails reales, configurar en `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-password-de-aplicacion
DEFAULT_FROM_EMAIL=seguros@utpl.edu.ec
```

**Nota para Gmail:** Usar contraseñas de aplicación, no la contraseña normal.

## 🛠️ Mantenimiento

### Backup de Base de Datos

```bash
# Backup
python manage.py dumpdata > backup.json

# Restaurar
python manage.py loaddata backup.json
```

### Limpiar Alertas Antiguas

```bash
python manage.py shell

from app.tasks import limpiar_alertas_antiguas
limpiar_alertas_antiguas.delay(dias=90)  # Eliminar alertas de más de 90 días
```

### Logs

Los logs se guardan en `logs/django.log` con rotación automática (10 MB, 5 archivos).

## 📦 Estructura del Proyecto

```
seguros-arqsoft/
├── app/                          # Aplicación principal
│   ├── models.py                 # Modelos de datos
│   ├── admin.py                  # Configuración del admin
│   ├── tasks.py                  # Tareas de Celery
│   └── management/
│       └── commands/             # Comandos personalizados
│           ├── generar_alertas.py
│           ├── enviar_alertas_email.py
│           ├── generar_reporte_polizas.py
│           └── generar_reporte_siniestros.py
├── seguros/                      # Configuración del proyecto
│   ├── settings.py               # Configuración
│   ├── celery.py                 # Configuración de Celery
│   └── urls.py                   # URLs
├── media/                        # Archivos subidos
│   ├── documentos/               # Documentos
│   └── reportes/                 # Reportes generados
├── logs/                         # Archivos de log
├── requirements.txt              # Dependencias
├── .env.example                  # Ejemplo de configuración
└── README.md                     # Este archivo
```

## 🎯 Flujo de Trabajo Recomendado

### 1. Configuración Inicial
1. Crear Compañías Aseguradoras
2. Crear Corredores de Seguros
3. Crear Tipos de Póliza
4. Crear Tipos de Siniestro

### 2. Operación Diaria
1. Registrar nuevas pólizas
2. Registrar facturas recibidas
3. Registrar pagos realizados
4. Registrar siniestros
5. Actualizar estado de siniestros
6. Revisar alertas generadas

### 3. Reportes Gerenciales
1. Generar reportes mensuales
2. Analizar estadísticas
3. Revisar tiempos de resolución
4. Identificar áreas de mejora

## 🐛 Solución de Problemas

### Error: ModuleNotFoundError

```bash
# Asegurarse de que el entorno virtual está activado
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: Redis connection refused

```bash
# Verificar que Redis está corriendo
redis-cli ping  # Debe responder "PONG"

# Si no está corriendo:
redis-server  # Linux
brew services start redis  # Mac
```

### Celery no ejecuta tareas

```bash
# Verificar que Celery worker está corriendo
celery -A seguros worker -l info

# Verificar que Celery beat está corriendo
celery -A seguros beat -l info
```

## 📚 Tecnologías Utilizadas

- **Django 5.2.8**: Framework web
- **Unfold 0.72.0**: Interfaz de administración moderna
- **Celery 5.4.0**: Tareas asíncronas
- **Redis**: Message broker para Celery
- **OpenPyXL**: Generación de reportes Excel
- **ReportLab**: Generación de reportes PDF
- **PostgreSQL/SQLite**: Base de datos

## 👥 Soporte

Para soporte técnico o preguntas:
- Email: soporte-ti@utpl.edu.ec
- Issues: GitHub Issues del proyecto

## 📄 Licencia

Este proyecto es propiedad de la Universidad Técnica Particular de Loja (UTPL).
Todos los derechos reservados.

---

**Universidad Técnica Particular de Loja**  
Sistema de Gestión de Seguros - 2024
