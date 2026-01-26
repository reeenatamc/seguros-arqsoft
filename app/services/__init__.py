"""

Servicios de la Aplicación - Arquitectura por Dominios.

Estructura:

    services/

    ├── base.py                 # Clases base compartidas

    ├── calculations.py         # Cálculos puros

    │

    ├── factura/               # Dominio Factura

    ├── pago/                  # Dominio Pago

    ├── poliza/                # Dominio Póliza

    ├── siniestro/             # Dominio Siniestro

    ├── documento/             # Dominio Documento

    ├── nota_credito/          # Dominio Nota de Crédito

    ├── bien_asegurado/        # Dominio Bien Asegurado

    │

    ├── reportes/              # Generación de reportes y exportación

    ├── analytics/             # Estadísticas y dashboard

    ├── alertas/               # Notificaciones y alertas

    ├── email/                 # Lectura de emails

    └── configuracion/         # Validadores de configuración

"""

# ==============================================================================

# BASE Y TIPOS COMPARTIDOS

# ==============================================================================

from .alertas import (
    Alerta,
    AlertasService,
    BrokerNotifier,
    CanalNotificacion,
    EmailNotifier,
    NotificacionDispatcher,
    NotificacionesFacade,
    NotificacionesService,
    Notificador,
    PolizaNotifier,
    ResponsableNotifier,
    ResultadoEnvio,
    SMSNotifier,
    TipoAlerta,
    UserNotifier,
    WebhookNotifier,
    WhatsAppNotifier,
    crear_dispatcher_desde_config,
    get_dispatcher,
)
from .analytics import (
    AdvancedAnalyticsService,
    DashboardAnalyticsService,
    DashboardFiltersService,
    DateRangePresets,
    EstadisticasService,
)
from .base import BaseService, ResultadoOperacion, ResultadoValidacion
from .bien_asegurado import BienAseguradoService
from .configuracion import (
    EmailValidator,
    JsonValidator,
    ListaValoresValidator,
    PorcentajeValidator,
    RangoNumericoValidator,
    TablaTasasValidator,
    UrlValidator,
    ValidadorConfig,
    registro_validadores,
    validar_configuracion,
)
from .documento import DocumentoService, DocumentosService
from .email import EmailReaderService
from .factura import FacturaService
from .nota_credito import NotaCreditoService
from .pago import PagoService
from .poliza import PolizaService
from .reportes import ExportacionService, PDFReportesService, ReportesAvanzadosService, ReportesService
from .siniestro import SiniestroService

# ==============================================================================

# SERVICIOS DE DOMINIO (Entidades de Negocio)

# ==============================================================================


# ==============================================================================

# REPORTES Y EXPORTACIÓN

# ==============================================================================


# ==============================================================================

# ANALYTICS Y ESTADÍSTICAS

# ==============================================================================


# ==============================================================================

# ALERTAS Y NOTIFICACIONES

# ==============================================================================


# ==============================================================================

# EMAIL

# ==============================================================================


# ==============================================================================

# CONFIGURACIÓN

# ==============================================================================


# ==============================================================================

# EXPORTS

# ==============================================================================

__all__ = [
    # Base
    "BaseService",
    "ResultadoValidacion",
    "ResultadoOperacion",
    # Dominio
    "FacturaService",
    "PagoService",
    "PolizaService",
    "SiniestroService",
    "DocumentoService",
    "DocumentosService",
    "NotaCreditoService",
    "BienAseguradoService",
    # Reportes
    "ReportesService",
    "ReportesAvanzadosService",
    "PDFReportesService",
    "ExportacionService",
    # Analytics
    "EstadisticasService",
    "DashboardAnalyticsService",
    "DashboardFiltersService",
    "DateRangePresets",
    "AdvancedAnalyticsService",
    # Alertas
    "BrokerNotifier",
    "UserNotifier",
    "ResponsableNotifier",
    "PolizaNotifier",
    "AlertasService",
    "NotificacionesFacade",
    "NotificacionesService",
    "Notificador",
    "EmailNotifier",
    "SMSNotifier",
    "WhatsAppNotifier",
    "WebhookNotifier",
    "NotificacionDispatcher",
    "Alerta",
    "TipoAlerta",
    "CanalNotificacion",
    "ResultadoEnvio",
    "get_dispatcher",
    "crear_dispatcher_desde_config",
    # Email
    "EmailReaderService",
    # Configuración
    "ValidadorConfig",
    "PorcentajeValidator",
    "RangoNumericoValidator",
    "JsonValidator",
    "EmailValidator",
    "UrlValidator",
    "ListaValoresValidator",
    "TablaTasasValidator",
    "registro_validadores",
    "validar_configuracion",
]
