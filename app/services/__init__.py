"""
Paquete de Servicios de Dominio - Sistema de Gestión de Seguros.

Este paquete implementa la capa de servicios siguiendo una Arquitectura por Dominios
(Domain-Driven Design simplificado). Cada subpaquete encapsula la lógica de negocio
de una entidad o funcionalidad específica del sistema.

Arquitectura del Paquete:
    services/
    ├── base.py                 # Clases base: BaseService, ResultadoOperacion
    ├── calculations.py         # Funciones puras de cálculo financiero
    │
    ├── factura/               # Dominio Factura
    │   ├── __init__.py
    │   └── service.py         # FacturaService: CRUD, validaciones, cálculos
    │
    ├── pago/                  # Dominio Pago
    │   ├── __init__.py
    │   └── service.py         # PagoService: registro, conciliación
    │
    ├── poliza/                # Dominio Póliza
    │   ├── __init__.py
    │   └── service.py         # PolizaService: renovaciones, vencimientos
    │
    ├── siniestro/             # Dominio Siniestro
    │   ├── __init__.py
    │   └── service.py         # SiniestroService: gestión, checklist
    │
    ├── documento/             # Dominio Documento
    │   ├── __init__.py
    │   ├── service.py         # DocumentoService: CRUD documentos
    │   └── generacion.py      # Generación de PDFs y Word
    │
    ├── nota_credito/          # Dominio Nota de Crédito
    │   ├── __init__.py
    │   └── service.py         # NotaCreditoService: emisión, aplicación
    │
    ├── bien_asegurado/        # Dominio Bien Asegurado
    │   ├── __init__.py
    │   └── service.py         # BienAseguradoService: gestión de bienes
    │
    ├── reportes/              # Generación de reportes
    │   ├── __init__.py
    │   ├── service.py         # ReportesService: reportes básicos
    │   ├── avanzados.py       # Reportes con filtros complejos
    │   ├── pdf.py             # Generación de PDFs
    │   └── exportacion.py     # Export a Excel/CSV
    │
    ├── analytics/             # Estadísticas y dashboard
    │   ├── __init__.py
    │   ├── estadisticas.py    # Métricas y KPIs
    │   ├── dashboard.py       # Datos para dashboard
    │   └── filters.py         # Filtros dinámicos
    │
    ├── alertas/               # Sistema de notificaciones
    │   ├── __init__.py
    │   ├── service.py         # AlertasService
    │   ├── notificadores.py   # Email, SMS, WhatsApp
    │   └── dispatcher.py      # Enrutamiento de alertas
    │
    ├── email/                 # Lectura de emails entrantes
    │   ├── __init__.py
    │   └── reader.py          # EmailReaderService
    │
    └── configuracion/         # Validadores de configuración
        ├── __init__.py
        └── validators.py      # Validadores especializados

Principios de Diseño:
    1. Separación de Responsabilidades: Cada servicio maneja una única entidad
    2. Independencia de Framework: Lógica desacoplada de Django views
    3. Testabilidad: Servicios fácilmente testeables de forma aislada
    4. Result Pattern: Manejo explícito de éxitos y errores

Autor: Equipo de Desarrollo UTPL
Versión: 1.0.0
Última Actualización: Enero 2026

Example:
    Uso típico desde una vista Django::

        from app.services import PolizaService, ResultadoOperacion

        def renovar_poliza_view(request, pk):
            resultado = PolizaService.renovar(pk, request.POST)
            if resultado.exitoso:
                messages.success(request, resultado.mensaje)
                return redirect('poliza_detalle', pk=resultado.objeto.pk)
            return render(request, 'error.html', {'errores': resultado.errores})
"""

# ==============================================================================
# BASE Y TIPOS COMPARTIDOS
# ==============================================================================
from .base import (
    BaseService,
    ResultadoValidacion,
    ResultadoOperacion,
)

# ==============================================================================
# SERVICIOS DE DOMINIO (Entidades de Negocio)
# ==============================================================================
from .factura import FacturaService
from .pago import PagoService
from .poliza import PolizaService
from .siniestro import SiniestroService
from .documento import DocumentoService, DocumentosService
from .nota_credito import NotaCreditoService
from .bien_asegurado import BienAseguradoService

# ==============================================================================
# REPORTES Y EXPORTACIÓN
# ==============================================================================
from .reportes import (
    ReportesService,
    ReportesAvanzadosService,
    PDFReportesService,
    ExportacionService,
)

# ==============================================================================
# ANALYTICS Y ESTADÍSTICAS
# ==============================================================================
from .analytics import (
    EstadisticasService,
    DashboardAnalyticsService,
    DashboardFiltersService,
    DateRangePresets,
    AdvancedAnalyticsService,
)

# ==============================================================================
# ALERTAS Y NOTIFICACIONES
# ==============================================================================
from .alertas import (
    BrokerNotifier,
    UserNotifier,
    ResponsableNotifier,
    PolizaNotifier,
    AlertasService,
    NotificacionesFacade,
    NotificacionesService,
    Notificador,
    EmailNotifier,
    SMSNotifier,
    WhatsAppNotifier,
    WebhookNotifier,
    NotificacionDispatcher,
    Alerta,
    TipoAlerta,
    CanalNotificacion,
    ResultadoEnvio,
    get_dispatcher,
    crear_dispatcher_desde_config,
)

# ==============================================================================
# EMAIL
# ==============================================================================
from .email import EmailReaderService

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
from .configuracion import (
    ValidadorConfig,
    PorcentajeValidator,
    RangoNumericoValidator,
    JsonValidator,
    EmailValidator,
    UrlValidator,
    ListaValoresValidator,
    TablaTasasValidator,
    registro_validadores,
    validar_configuracion,
)

# ==============================================================================
# EXPORTS - Lista pública de símbolos del paquete
# ==============================================================================
__all__ = [
    # Base
    'BaseService',
    'ResultadoValidacion',
    'ResultadoOperacion',

    # Dominio
    'FacturaService',
    'PagoService',
    'PolizaService',
    'SiniestroService',
    'DocumentoService',
    'DocumentosService',
    'NotaCreditoService',
    'BienAseguradoService',

    # Reportes
    'ReportesService',
    'ReportesAvanzadosService',
    'PDFReportesService',
    'ExportacionService',

    # Analytics
    'EstadisticasService',
    'DashboardAnalyticsService',
    'DashboardFiltersService',
    'DateRangePresets',
    'AdvancedAnalyticsService',

    # Alertas
    'BrokerNotifier',
    'UserNotifier',
    'ResponsableNotifier',
    'PolizaNotifier',
    'AlertasService',
    'NotificacionesFacade',
    'NotificacionesService',
    'Notificador',
    'EmailNotifier',
    'SMSNotifier',
    'WhatsAppNotifier',
    'WebhookNotifier',
    'NotificacionDispatcher',
    'Alerta',
    'TipoAlerta',
    'CanalNotificacion',
    'ResultadoEnvio',
    'get_dispatcher',
    'crear_dispatcher_desde_config',

    # Email
    'EmailReaderService',

    # Configuración
    'ValidadorConfig',
    'PorcentajeValidator',
    'RangoNumericoValidator',
    'JsonValidator',
    'EmailValidator',
    'UrlValidator',
    'ListaValoresValidator',
    'TablaTasasValidator',
    'registro_validadores',
    'validar_configuracion',
]
