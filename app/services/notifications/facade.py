"""
Facade para el sistema de notificaciones.
Proporciona un punto de entrada único manteniendo compatibilidad con código existente.
"""

from .broker import BrokerNotifier
from .user import UserNotifier
from .responsable import ResponsableNotifier
from .poliza import PolizaNotifier
from .alertas import AlertasService


class NotificacionesFacade:
    """
    Facade que agrupa todos los notificadores para acceso conveniente.
    
    USO:
        facade = NotificacionesFacade()
        
        # Acceso por tipo de notificador
        facade.broker.notificar_siniestro(siniestro)
        facade.user.confirmar_registro_siniestro(siniestro, usuario)
        facade.poliza.notificar_vencimiento(poliza)
        
        # Verificar alertas
        facade.alertas.verificar_todas()
    
    NOTA:
        Este facade es opcional. Puedes importar los servicios
        individuales directamente si solo necesitas uno.
    """
    
    def __init__(self):
        self._broker = None
        self._user = None
        self._responsable = None
        self._poliza = None
        self._alertas = None
    
    @property
    def broker(self) -> BrokerNotifier:
        """Notificador para comunicaciones con el broker."""
        if self._broker is None:
            self._broker = BrokerNotifier()
        return self._broker
    
    @property
    def user(self) -> UserNotifier:
        """Notificador para comunicaciones con usuarios internos."""
        if self._user is None:
            self._user = UserNotifier()
        return self._user
    
    @property
    def responsable(self) -> ResponsableNotifier:
        """Notificador para comunicaciones con responsables/custodios."""
        if self._responsable is None:
            self._responsable = ResponsableNotifier()
        return self._responsable
    
    @property
    def poliza(self) -> PolizaNotifier:
        """Notificador para comunicaciones sobre pólizas."""
        if self._poliza is None:
            self._poliza = PolizaNotifier()
        return self._poliza
    
    @property
    def alertas(self) -> AlertasService:
        """Servicio de verificación de alertas automáticas."""
        if self._alertas is None:
            self._alertas = AlertasService()
        return self._alertas
    
    # Métodos de conveniencia para compatibilidad con código existente
    def notificar_siniestro_a_broker(self, siniestro, usuario=None):
        """Alias para compatibilidad con NotificacionesService."""
        return self.broker.notificar_siniestro(siniestro, usuario)
    
    def notificar_siniestro_a_usuario(self, siniestro, usuario=None):
        """Alias para compatibilidad con NotificacionesService."""
        return self.user.confirmar_registro_siniestro(siniestro, usuario)
    
    def notificar_responsable_bien(self, siniestro, usuario=None):
        """Alias para compatibilidad con NotificacionesService."""
        return self.responsable.notificar_siniestro_pendiente(siniestro, usuario)
    
    def notificar_vencimiento_poliza(self, poliza, dias_antes=30, usuario=None):
        """Alias para compatibilidad con NotificacionesService."""
        return self.poliza.notificar_vencimiento(poliza, dias_antes, usuario)
    
    def verificar_alertas_siniestros(self):
        """Alias para compatibilidad con NotificacionesService."""
        return self.alertas.verificar_todas()
