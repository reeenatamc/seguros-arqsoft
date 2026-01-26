"""

Sistema de Alertas y Notificaciones.

"""

from .alertas import AlertasService
from .broker import BrokerNotifier
from .email_service import NotificacionesService
from .facade import NotificacionesFacade
from .notificadores import (
    Alerta,
    CanalNotificacion,
    EmailNotifier,
    NotificacionDispatcher,
    Notificador,
    ResultadoEnvio,
    SMSNotifier,
    TipoAlerta,
    WebhookNotifier,
    WhatsAppNotifier,
    crear_dispatcher_desde_config,
    get_dispatcher,
)
from .poliza import PolizaNotifier
from .responsable import ResponsableNotifier
from .user import UserNotifier

__all__ = [
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
]
