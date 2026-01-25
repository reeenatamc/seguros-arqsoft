"""
Sistema de Alertas y Notificaciones.
"""

from .broker import BrokerNotifier
from .user import UserNotifier
from .responsable import ResponsableNotifier
from .poliza import PolizaNotifier
from .alertas import AlertasService
from .facade import NotificacionesFacade
from .email_service import NotificacionesService
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

__all__ = [
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
]
