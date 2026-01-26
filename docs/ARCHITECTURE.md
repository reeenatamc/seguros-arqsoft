# Arquitectura del Sistema

## 📐 Visión General

El Sistema de Gestión Integral de Pólizas y Siniestros está diseñado siguiendo el patrón **MVC (Model-View-Controller)** de Django, con una arquitectura modular y escalable.

## 🏗️ Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│                    Django Admin (Unfold)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                      │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌─────────────┐ │
│  │  Models  │  │  Admin   │  │  Views  │  │  Commands   │ │
│  └──────────┘  └──────────┘  └─────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Validaciones │  │  Cálculos    │  │  Notificaciones │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│   DATABASE   │    │    CELERY    │    │  FILE STORAGE    │
│  PostgreSQL  │    │ (Redis Broker)│   │     (Media)      │
└──────────────┘    └──────────────┘    └──────────────────┘
```

## 📊 Modelo de Datos

### Diagrama de Entidad-Relación

```
┌─────────────────────┐
│ CompaniaAseguradora │
└──────────┬──────────┘
           │ 1
           │
           │ N
┌──────────▼──────────┐         ┌─────────────────┐
│      Poliza         │────N────│   TipoPoliza    │
└──────────┬──────────┘    1    └─────────────────┘
           │ 1
           │
     ┌─────┼─────┬──────────┐
     │           │          │
     │ N         │ N        │ N
┌────▼────┐  ┌──▼──────┐  ┌▼──────────┐
│ Factura │  │Siniestro│  │ Documento │
└────┬────┘  └───┬─────┘  └───────────┘
     │ 1         │ N
     │           │ 1
     │ N         │
┌────▼────┐  ┌──▼──────────┐
│  Pago   │  │TipoSiniestro│
└─────────┘  └─────────────┘

┌─────────────────┐
│ CorredorSeguros │
└──────────┬──────┘
           │ 1
           │
           │ N
      ┌────▼────┐
      │ Poliza  │
      └─────────┘

┌─────────┐
│  Alerta │
└────┬────┘
     │ N
     │ N
     │ N
     └──► Poliza, Factura, Siniestro
```

### Modelos Principales

#### 1. **CompaniaAseguradora**
- Almacena información de las compañías de seguros
- Relación 1:N con Pólizas

#### 2. **CorredorSeguros**
- Información de corredores de seguros
- Relación 1:N con Pólizas

#### 3. **TipoPoliza**
- Catálogo de tipos de pólizas
- Relación 1:N con Pólizas

#### 4. **Poliza** (Modelo Central)
- Información completa de cada póliza
- Validaciones de duplicidad
- Actualización automática de estado
- Relaciones:
  - N:1 con CompaniaAseguradora
  - N:1 con CorredorSeguros
  - N:1 con TipoPoliza
  - 1:N con Facturas
  - 1:N con Siniestros
  - 1:N con Documentos

#### 5. **Factura**
- Control de facturación
- Cálculos automáticos
- Relaciones:
  - N:1 con Poliza
  - 1:N con Pagos
  - 1:N con Documentos

#### 6. **Pago**
- Registro de pagos realizados
- Actualización automática de estado de factura
- Relación N:1 con Factura

#### 7. **TipoSiniestro**
- Catálogo de tipos de siniestros
- Relación 1:N con Siniestros

#### 8. **Siniestro**
- Registro y seguimiento de siniestros
- Alertas automáticas
- Relaciones:
  - N:1 con Poliza
  - N:1 con TipoSiniestro
  - 1:N con Documentos

#### 9. **Documento**
- Almacenamiento de archivos
- Relaciones opcionales con Poliza, Factura, Siniestro

#### 10. **Alerta**
- Sistema de notificaciones
- Relaciones N:N con Users (destinatarios)
- Relaciones opcionales con Poliza, Factura, Siniestro

## 🔄 Flujo de Datos

### 1. Flujo de Pólizas

```
Usuario crea Póliza
    ↓
Validación de duplicidad
    ↓
Cálculo de estado inicial
    ↓
Guardado en BD
    ↓
Tarea periódica actualiza estado diariamente
    ↓
Si vence en 30 días → Genera Alerta
    ↓
Alerta enviada por email
```

### 2. Flujo de Facturas

```
Usuario crea Factura
    ↓
Cálculo automático de:
  - Contribución Superintendencia (3.5%)
  - Contribución Seguro Campesino (0.5%)
  - Descuento pronto pago (si aplica)
    ↓
Guardado en BD
    ↓
Usuario registra Pago(s)
    ↓
Actualización automática de estado
    ↓
Si está pendiente y vence pronto → Genera Alerta
```

### 3. Flujo de Siniestros

```
Usuario registra Siniestro
    ↓
Estado inicial: "registrado"
    ↓
Usuario actualiza estado según proceso
    ↓
Tarea periódica verifica:
  - ¿Documentación pendiente > 30 días? → Alerta cada 8 días
  - ¿Enviado sin respuesta > 8 días? → Alerta
    ↓
Liquidación y cierre
```

## ⚙️ Lógica de Negocio

### Cálculos Automáticos

#### Facturas
```python
# Contribuciones
contribucion_superintendencia = subtotal * 0.035  # 3.5%
contribucion_seguro_campesino = subtotal * 0.005  # 0.5%

# Descuento por pronto pago
if dias_desde_emision <= 20:
    descuento = subtotal * 0.05  # 5%

# Monto total
monto_total = (
    subtotal + 
    iva + 
    contribucion_superintendencia + 
    contribucion_seguro_campesino - 
    retenciones - 
    descuento
)
```

#### Estados de Póliza
```python
hoy = datetime.now().date()

if fecha_fin < hoy:
    estado = 'vencida'
elif fecha_fin <= hoy + timedelta(days=30):
    estado = 'por_vencer'
elif fecha_inicio <= hoy <= fecha_fin:
    estado = 'vigente'
```

### Validaciones

#### Duplicidad de Pólizas
```python
# Verificar que no exista otra póliza con el mismo número
# y fechas de vigencia superpuestas
polizas_superpuestas = Poliza.objects.filter(
    numero_poliza=numero_poliza
).exclude(pk=poliza_actual.pk)

for poliza in polizas_superpuestas:
    if (fecha_inicio <= poliza.fecha_fin and 
        fecha_fin >= poliza.fecha_inicio):
        raise ValidationError("Póliza duplicada con fechas superpuestas")
```

## 🔔 Sistema de Alertas

### Tipos de Alertas

| Tipo | Condición | Frecuencia |
|------|-----------|------------|
| Vencimiento Póliza | Vence en ≤ 30 días | Una vez |
| Pago Pendiente | Factura vence en ≤ 7 días | Una vez |
| Pronto Pago | Quedan ≤ 5 días para descuento | Una vez |
| Documentación | Pendiente > 30 días | Cada 8 días |
| Respuesta Aseguradora | Sin respuesta > 8 días | Cada 8 días |

### Arquitectura de Celery

```
┌──────────────┐
│ Django App   │
│   (Web)      │
└──────┬───────┘
       │
       │ Programa tareas
       ▼
┌──────────────┐         ┌──────────────┐
│ Celery Beat  │────────▶│ Redis Broker │
│  (Scheduler) │         │   (Queue)    │
└──────────────┘         └──────┬───────┘
                                │
                                │ Distribuye tareas
                                ▼
                         ┌──────────────┐
                         │Celery Worker │
                         │  (Executor)  │
                         └──────┬───────┘
                                │
                                │ Ejecuta
                                ▼
                         ┌──────────────┐
                         │  Commands    │
                         │  & Tasks     │
                         └──────────────┘
```

### Tareas Periódicas

```python
# Configuración en celery.py
beat_schedule = {
    'generar-alertas-diarias': {
        'task': 'app.tasks.generar_alertas_automaticas',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM
    },
    'enviar-alertas-email': {
        'task': 'app.tasks.enviar_alertas_email',
        'schedule': crontab(hour=8, minute=30),  # 8:30 AM
    },
    'actualizar-estados-polizas': {
        'task': 'app.tasks.actualizar_estados_polizas',
        'schedule': crontab(hour=7, minute=0),  # 7:00 AM
    },
}
```

## 📝 Generación de Reportes

### Arquitectura de Reportes

```
Usuario ejecuta comando
    ↓
Management Command
    ↓
Consulta datos de BD
    ↓
Procesa y agrupa datos
    ↓
┌──────────┬──────────┐
│          │          │
▼          ▼          ▼
Excel    PDF    (Futuro: Web)
(openpyxl) (reportlab)
    │          │
    └────┬─────┘
         ▼
  media/reportes/
```

### Tipos de Reportes

#### 1. Reportes de Pólizas
- **Formato**: Excel (múltiples hojas), PDF
- **Contenido**:
  - Resumen ejecutivo por estado
  - Detalle completo de pólizas
  - Gastos por póliza (facturación)
- **Filtros**: Estado de póliza

#### 2. Reportes de Siniestros
- **Formato**: Excel (múltiples hojas), PDF
- **Contenido**:
  - Estadísticas generales
  - Análisis por tipo de siniestro
  - Análisis por póliza (top 20)
  - Tiempos de resolución
  - Causas frecuentes
- **Filtros**: Período (semanal, mensual, trimestral, anual)

## 🔐 Seguridad

### Autenticación y Autorización

```
┌──────────┐
│  Usuario │
└────┬─────┘
     │
     │ Login
     ▼
┌────────────────┐
│ Django Auth    │
│  - User Model  │
│  - Permissions │
│  - Groups      │
└────┬───────────┘
     │
     │ Verifica permisos
     ▼
┌────────────────┐
│  Admin Views   │
│  - ModelAdmin  │
│  - Permissions │
└────────────────┘
```

### Niveles de Acceso

| Rol | Permisos |
|-----|----------|
| Superadmin | Todos los permisos |
| Administrador | CRUD en todos los modelos |
| Operador | CRUD en Pólizas, Siniestros, Facturas |
| Consulta | Solo lectura |

### Protección de Datos

1. **Validación en Modelos**: Clean methods
2. **Validación en Forms**: Django Forms
3. **Validación en Admin**: ModelAdmin hooks
4. **CSRF Protection**: Django middleware
5. **SQL Injection**: Django ORM
6. **XSS Protection**: Template escaping

## 📈 Escalabilidad

### Optimizaciones Implementadas

1. **Database Indexes**
```python
class Meta:
    indexes = [
        models.Index(fields=['numero_poliza']),
        models.Index(fields=['estado', 'fecha_fin']),
    ]
```

2. **Select Related / Prefetch Related**
```python
Poliza.objects.select_related(
    'compania_aseguradora',
    'corredor_seguros',
    'tipo_poliza'
)
```

3. **Caching** (Opcional)
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Capacidad del Sistema

- **Usuarios concurrentes**: 100+
- **Registros soportados**: 50,000+
- **Tiempo de respuesta**: < 2 segundos
- **Disponibilidad**: 99.5%

## 🔄 CI/CD (Recomendado)

### Pipeline Sugerido

```
┌─────────────┐
│   Commit    │
│  (GitHub)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Tests     │
│  (pytest)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Build     │
│ (Docker)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Deploy    │
│ (Staging)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Deploy    │
│ (Production)│
└─────────────┘
```

## 📊 Monitoreo

### Métricas Clave

1. **Aplicación**
   - Tiempo de respuesta de requests
   - Tasa de errores
   - Uso de CPU/RAM

2. **Base de Datos**
   - Consultas lentas
   - Conexiones activas
   - Tamaño de BD

3. **Celery**
   - Tareas en cola
   - Tareas fallidas
   - Tiempo de ejecución

4. **Sistema**
   - Uso de disco
   - Red
   - Logs de errores

### Herramientas Recomendadas

- **APM**: New Relic, DataDog
- **Logs**: ELK Stack, Papertrail
- **Uptime**: UptimeRobot, Pingdom
- **Errors**: Sentry

## 🔮 Mejoras Futuras

### Corto Plazo
- [ ] API REST con Django REST Framework
- [ ] Dashboard de métricas
- [ ] Notificaciones push
- [ ] Exportación a más formatos

### Mediano Plazo
- [ ] Aplicación móvil
- [ ] Integración con sistemas externos
- [ ] Reportes más avanzados
- [ ] Machine Learning para predicciones

### Largo Plazo
- [ ] Microservicios
- [ ] Arquitectura serverless
- [ ] IA para procesamiento de documentos
- [ ] Blockchain para auditoría

---

**Universidad Técnica Particular de Loja**  
Documentación de Arquitectura - Sistema de Gestión de Seguros
