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

# EXPORTS

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

