from .reportes import ReportesService
from .estadisticas import EstadisticasService
from .exportacion import ExportacionService
from .dashboard_analytics import DashboardAnalyticsService
from .dashboard_filters import DashboardFiltersService, DateRangePresets
from .advanced_analytics import AdvancedAnalyticsService
from .notificaciones import NotificacionesService
from .documentos import DocumentosService
from .reportes_avanzados import ReportesAvanzadosService

# Domain Services (lógica de negocio para entidades)
from .domain_services import (
    FacturaService,
    PagoService,
    PolizaService,
    SiniestroService,
    DocumentoService,
    NotaCreditoService,
    BienAseguradoService,
    ResultadoValidacion,
    ResultadoOperacion,
)

# Sistema de notificaciones extensible (Strategy Pattern)
from .notificadores import (
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

# Validadores de configuración extensibles (Registry Pattern)
from .config_validators import (
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

__all__ = [
    # Servicios de reportes y análisis
    'ReportesService',
    'EstadisticasService',
    'ExportacionService',
    'DashboardAnalyticsService',
    'DashboardFiltersService',
    'DateRangePresets',
    'AdvancedAnalyticsService',
    'NotificacionesService',
    'DocumentosService',
    'ReportesAvanzadosService',
    
    # Domain Services
    'FacturaService',
    'PagoService',
    'PolizaService',
    'SiniestroService',
    'DocumentoService',
    'NotaCreditoService',
    'BienAseguradoService',
    'ResultadoValidacion',
    'ResultadoOperacion',
    
    # Notificadores (Strategy Pattern)
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
    
    # Validadores de configuración (Registry Pattern)
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

