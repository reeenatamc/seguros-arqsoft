"""
Servicios de Notificación Segregados (ISP - Interface Segregation Principle).

En lugar de una clase "Dios" NotificacionesService con 15+ métodos,
tenemos servicios pequeños y enfocados que los clientes pueden usar
individualmente según sus necesidades.

ANTES (violación de ISP):
    class NotificacionesService:
        def notificar_siniestro_a_broker(...)  # Broker
        def notificar_siniestro_a_usuario(...)  # Usuario
        def notificar_responsable_bien(...)  # Responsable
        def notificar_cierre_siniestro(...)  # Varios
        def notificar_vencimiento_poliza(...)  # Pólizas
        def verificar_alertas_siniestros(...)  # Alertas
        # ... cliente que solo quiere notificar al broker
        # depende de TODO lo demás

AHORA (ISP aplicado):
    from app.services.notifications import (
        BrokerNotifier,      # Solo notificaciones al broker
        UserNotifier,        # Solo notificaciones al usuario
        AlertasService,      # Solo verificación de alertas
        PolizaNotifier,      # Solo notificaciones de pólizas
    )
    
    # Cliente usa SOLO lo que necesita
    notifier = BrokerNotifier()
    notifier.notificar_siniestro(siniestro)

USO:
    # Opción 1: Importar servicio específico
    from app.services.notifications import BrokerNotifier
    BrokerNotifier().notificar_siniestro(siniestro)
    
    # Opción 2: Usar facade para compatibilidad
    from app.services.notifications import NotificacionesFacade
    facade = NotificacionesFacade()
    facade.broker.notificar_siniestro(siniestro)
"""

from .broker import BrokerNotifier
from .user import UserNotifier
from .responsable import ResponsableNotifier
from .poliza import PolizaNotifier
from .alertas import AlertasService
from .facade import NotificacionesFacade

__all__ = [
    'BrokerNotifier',
    'UserNotifier', 
    'ResponsableNotifier',
    'PolizaNotifier',
    'AlertasService',
    'NotificacionesFacade',
]
