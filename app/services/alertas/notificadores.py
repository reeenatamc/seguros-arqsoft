"""
Sistema de Notificaciones Extensible (Patrón Strategy/Plugin).

Este módulo implementa un sistema de notificaciones que permite agregar
nuevos canales (Email, SMS, WhatsApp, Push) sin modificar el código existente.

ARQUITECTURA:
- Notificador: Interfaz base abstracta
- EmailNotifier, SMSNotifier, etc.: Implementaciones concretas
- NotificacionDispatcher: Orquesta el envío por múltiples canales
- Registro de notificadores: Permite agregar nuevos canales dinámicamente

USO:
    from app.services.notificadores import (
        NotificacionDispatcher, EmailNotifier, Alerta
    )
    
    # Crear dispatcher con canales
    dispatcher = NotificacionDispatcher([
        EmailNotifier(),
        # SMSNotifier(api_key='...'),  # Agregar cuando esté listo
    ])
    
    # Crear alerta
    alerta = Alerta(
        tipo='siniestro_nuevo',
        titulo='Nuevo Siniestro Registrado',
        mensaje='Se ha registrado el siniestro SIN-2025-0001',
        destinatarios=['broker@example.com'],
        datos={'siniestro_id': 123, 'numero': 'SIN-2025-0001'},
    )
    
    # Enviar por todos los canales
    resultados = dispatcher.enviar(alerta)

EXTENSIBILIDAD:
    Para agregar un nuevo canal (ej: WhatsApp):
    
    1. Crear clase que herede de Notificador:
       class WhatsAppNotifier(Notificador):
           def enviar(self, alerta: Alerta) -> ResultadoEnvio:
               # Implementación específica de WhatsApp
               ...
    
    2. Registrarlo en el dispatcher:
       dispatcher.registrar_notificador(WhatsAppNotifier(api_key='...'))
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


# ==============================================================================
# DATA CLASSES
# ==============================================================================

class TipoAlerta(str, Enum):
    """Tipos de alertas soportadas."""
    # Siniestros
    SINIESTRO_NUEVO = 'siniestro_nuevo'
    SINIESTRO_BROKER = 'siniestro_broker'
    SINIESTRO_USUARIO = 'siniestro_usuario'
    SINIESTRO_RESPONSABLE = 'siniestro_responsable'
    SINIESTRO_CIERRE = 'siniestro_cierre'
    SINIESTRO_DOCUMENTACION = 'siniestro_documentacion'
    
    # Alertas
    ALERTA_RESPUESTA = 'alerta_respuesta'
    ALERTA_DEPOSITO = 'alerta_deposito'
    
    # Pólizas
    POLIZA_VENCIMIENTO = 'poliza_vencimiento'
    POLIZA_RENOVACION = 'poliza_renovacion'
    
    # Facturas
    FACTURA_VENCIMIENTO = 'factura_vencimiento'
    FACTURA_PAGO = 'factura_pago'
    
    # General
    ALERTA_GENERAL = 'alerta_general'


class CanalNotificacion(str, Enum):
    """Canales de notificación disponibles."""
    EMAIL = 'email'
    SMS = 'sms'
    WHATSAPP = 'whatsapp'
    PUSH = 'push'
    WEBHOOK = 'webhook'


@dataclass
class Alerta:
    """
    Representa una alerta/notificación a enviar.
    Es agnóstica al canal de envío.
    """
    tipo: TipoAlerta
    titulo: str
    mensaje: str
    destinatarios: List[str]  # emails, teléfonos, etc.
    
    # Datos adicionales para templates
    datos: Dict[str, Any] = field(default_factory=dict)
    
    # Opciones de envío
    prioridad: str = 'normal'  # 'alta', 'normal', 'baja'
    cc: List[str] = field(default_factory=list)
    
    # Referencias a entidades (para tracking)
    siniestro_id: Optional[int] = None
    poliza_id: Optional[int] = None
    factura_id: Optional[int] = None
    
    # Metadata
    fecha_creacion: datetime = field(default_factory=timezone.now)
    usuario_id: Optional[int] = None


@dataclass
class ResultadoEnvio:
    """Resultado del envío por un canal específico."""
    canal: CanalNotificacion
    exitoso: bool
    mensaje: str = ""
    error: Optional[str] = None
    id_externo: Optional[str] = None  # ID del mensaje en el servicio externo
    fecha_envio: datetime = field(default_factory=timezone.now)


# ==============================================================================
# INTERFAZ BASE - NOTIFICADOR
# ==============================================================================

class Notificador(ABC):
    """
    Interfaz base para todos los notificadores.
    Implementa el patrón Strategy para diferentes canales de notificación.
    """
    
    @property
    @abstractmethod
    def canal(self) -> CanalNotificacion:
        """Retorna el canal de notificación."""
        pass
    
    @property
    def nombre(self) -> str:
        """Nombre legible del notificador."""
        return self.canal.value.capitalize()
    
    @abstractmethod
    def enviar(self, alerta: Alerta) -> ResultadoEnvio:
        """
        Envía la alerta por este canal.
        
        Args:
            alerta: Alerta a enviar
            
        Returns:
            ResultadoEnvio con el estado del envío
        """
        pass
    
    def soporta_tipo(self, tipo: TipoAlerta) -> bool:
        """
        Indica si este canal soporta un tipo de alerta.
        Por defecto, soporta todos. Override para restringir.
        """
        return True
    
    def validar_destinatario(self, destinatario: str) -> bool:
        """
        Valida si el destinatario es válido para este canal.
        Override en subclases para validación específica.
        """
        return bool(destinatario)


# ==============================================================================
# IMPLEMENTACIÓN - EMAIL NOTIFIER
# ==============================================================================

class EmailNotifier(Notificador):
    """
    Notificador por Email usando Django's email backend.
    """
    
    def __init__(
        self,
        from_email: Optional[str] = None,
        template_html: str = 'emails/base_notificacion.html',
        fail_silently: bool = False,
    ):
        self._from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        self._template_html = template_html
        self._fail_silently = fail_silently
    
    @property
    def canal(self) -> CanalNotificacion:
        return CanalNotificacion.EMAIL
    
    def validar_destinatario(self, destinatario: str) -> bool:
        """Valida formato de email básico."""
        return '@' in destinatario and '.' in destinatario
    
    def enviar(self, alerta: Alerta) -> ResultadoEnvio:
        """Envía la alerta por email."""
        try:
            # Filtrar destinatarios válidos
            destinatarios_validos = [
                d for d in alerta.destinatarios 
                if self.validar_destinatario(d)
            ]
            
            if not destinatarios_validos:
                return ResultadoEnvio(
                    canal=self.canal,
                    exitoso=False,
                    error="No hay destinatarios válidos para email"
                )
            
            # Preparar contenido HTML
            contenido_html = self._renderizar_html(alerta)
            
            # Preparar CC
            cc_validos = [c for c in alerta.cc if self.validar_destinatario(c)]
            
            # Enviar
            if contenido_html:
                email = EmailMultiAlternatives(
                    subject=alerta.titulo,
                    body=alerta.mensaje,
                    from_email=self._from_email,
                    to=destinatarios_validos,
                    cc=cc_validos if cc_validos else None,
                )
                email.attach_alternative(contenido_html, "text/html")
                email.send(fail_silently=self._fail_silently)
            else:
                send_mail(
                    subject=alerta.titulo,
                    message=alerta.mensaje,
                    from_email=self._from_email,
                    recipient_list=destinatarios_validos,
                    fail_silently=self._fail_silently,
                )
            
            return ResultadoEnvio(
                canal=self.canal,
                exitoso=True,
                mensaje=f"Email enviado a {len(destinatarios_validos)} destinatario(s)"
            )
            
        except Exception as e:
            return ResultadoEnvio(
                canal=self.canal,
                exitoso=False,
                error=str(e)
            )
    
    def _renderizar_html(self, alerta: Alerta) -> Optional[str]:
        """Renderiza el contenido HTML usando el template."""
        try:
            # Construir contexto para el template
            context = self._construir_contexto(alerta)
            return render_to_string(self._template_html, context)
        except Exception:
            return None
    
    def _construir_contexto(self, alerta: Alerta) -> Dict[str, Any]:
        """Construye el contexto para el template de email."""
        return {
            'titulo': alerta.titulo,
            'intro': [alerta.mensaje],
            'bloques': alerta.datos.get('bloques', []),
            'cta_text': alerta.datos.get('cta_text'),
            'cta_url': alerta.datos.get('cta_url'),
            'nota': alerta.datos.get('nota'),
            **alerta.datos,
        }


# ==============================================================================
# IMPLEMENTACIÓN - SMS NOTIFIER (PLACEHOLDER)
# ==============================================================================

class SMSNotifier(Notificador):
    """
    Notificador por SMS.
    Placeholder para integración futura con Twilio, AWS SNS, etc.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._from_number = from_number
        self._enabled = bool(api_key and api_secret)
    
    @property
    def canal(self) -> CanalNotificacion:
        return CanalNotificacion.SMS
    
    def validar_destinatario(self, destinatario: str) -> bool:
        """Valida formato de teléfono básico."""
        # Simplificado: verificar que tenga solo dígitos y longitud razonable
        cleaned = ''.join(c for c in destinatario if c.isdigit())
        return 8 <= len(cleaned) <= 15
    
    def soporta_tipo(self, tipo: TipoAlerta) -> bool:
        """SMS solo para alertas de alta prioridad."""
        tipos_sms = {
            TipoAlerta.ALERTA_RESPUESTA,
            TipoAlerta.ALERTA_DEPOSITO,
            TipoAlerta.POLIZA_VENCIMIENTO,
            TipoAlerta.FACTURA_VENCIMIENTO,
        }
        return tipo in tipos_sms
    
    def enviar(self, alerta: Alerta) -> ResultadoEnvio:
        """Envía la alerta por SMS."""
        if not self._enabled:
            return ResultadoEnvio(
                canal=self.canal,
                exitoso=False,
                error="SMS no configurado (falta API key)"
            )
        
        # TODO: Implementar integración real con proveedor SMS
        # Ejemplo con Twilio:
        # from twilio.rest import Client
        # client = Client(self._api_key, self._api_secret)
        # message = client.messages.create(
        #     body=alerta.mensaje[:160],
        #     from_=self._from_number,
        #     to=destinatario
        # )
        
        return ResultadoEnvio(
            canal=self.canal,
            exitoso=False,
            error="SMS no implementado - placeholder"
        )


# ==============================================================================
# IMPLEMENTACIÓN - WHATSAPP NOTIFIER (PLACEHOLDER)
# ==============================================================================

class WhatsAppNotifier(Notificador):
    """
    Notificador por WhatsApp Business API.
    Placeholder para integración futura.
    """
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ):
        self._api_token = api_token
        self._phone_number_id = phone_number_id
        self._enabled = bool(api_token and phone_number_id)
    
    @property
    def canal(self) -> CanalNotificacion:
        return CanalNotificacion.WHATSAPP
    
    def validar_destinatario(self, destinatario: str) -> bool:
        """Valida formato de teléfono para WhatsApp."""
        cleaned = ''.join(c for c in destinatario if c.isdigit())
        return 10 <= len(cleaned) <= 15
    
    def enviar(self, alerta: Alerta) -> ResultadoEnvio:
        """Envía la alerta por WhatsApp."""
        if not self._enabled:
            return ResultadoEnvio(
                canal=self.canal,
                exitoso=False,
                error="WhatsApp no configurado"
            )
        
        # TODO: Implementar integración con WhatsApp Business API
        # import requests
        # response = requests.post(
        #     f"https://graph.facebook.com/v17.0/{self._phone_number_id}/messages",
        #     headers={"Authorization": f"Bearer {self._api_token}"},
        #     json={...}
        # )
        
        return ResultadoEnvio(
            canal=self.canal,
            exitoso=False,
            error="WhatsApp no implementado - placeholder"
        )


# ==============================================================================
# IMPLEMENTACIÓN - WEBHOOK NOTIFIER
# ==============================================================================

class WebhookNotifier(Notificador):
    """
    Notificador por Webhook (para integraciones externas).
    Útil para conectar con Slack, Teams, Discord, etc.
    """
    
    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
    ):
        self._webhook_url = webhook_url
        self._headers = headers or {'Content-Type': 'application/json'}
        self._timeout = timeout
    
    @property
    def canal(self) -> CanalNotificacion:
        return CanalNotificacion.WEBHOOK
    
    def validar_destinatario(self, destinatario: str) -> bool:
        """Para webhooks, el destinatario es el URL configurado."""
        return True  # El webhook ya está configurado
    
    def enviar(self, alerta: Alerta) -> ResultadoEnvio:
        """Envía la alerta al webhook."""
        try:
            import requests
            
            payload = {
                'tipo': alerta.tipo.value,
                'titulo': alerta.titulo,
                'mensaje': alerta.mensaje,
                'prioridad': alerta.prioridad,
                'datos': alerta.datos,
                'fecha': alerta.fecha_creacion.isoformat(),
            }
            
            response = requests.post(
                self._webhook_url,
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            )
            
            if response.status_code in (200, 201, 202, 204):
                return ResultadoEnvio(
                    canal=self.canal,
                    exitoso=True,
                    mensaje=f"Webhook respondió con {response.status_code}"
                )
            else:
                return ResultadoEnvio(
                    canal=self.canal,
                    exitoso=False,
                    error=f"Webhook respondió con {response.status_code}: {response.text[:100]}"
                )
                
        except ImportError:
            return ResultadoEnvio(
                canal=self.canal,
                exitoso=False,
                error="Módulo 'requests' no disponible"
            )
        except Exception as e:
            return ResultadoEnvio(
                canal=self.canal,
                exitoso=False,
                error=str(e)
            )


# ==============================================================================
# DISPATCHER - ORQUESTADOR DE NOTIFICACIONES
# ==============================================================================

class NotificacionDispatcher:
    """
    Orquesta el envío de notificaciones por múltiples canales.
    Implementa el patrón Composite para manejar varios notificadores.
    """
    
    def __init__(self, notificadores: Optional[List[Notificador]] = None):
        self._notificadores: List[Notificador] = notificadores or []
    
    def registrar_notificador(self, notificador: Notificador) -> 'NotificacionDispatcher':
        """
        Registra un nuevo notificador.
        Retorna self para permitir encadenamiento.
        """
        self._notificadores.append(notificador)
        return self
    
    def remover_notificador(self, canal: CanalNotificacion) -> bool:
        """Remueve un notificador por su canal."""
        original_len = len(self._notificadores)
        self._notificadores = [
            n for n in self._notificadores 
            if n.canal != canal
        ]
        return len(self._notificadores) < original_len
    
    @property
    def canales_activos(self) -> List[CanalNotificacion]:
        """Lista de canales activos."""
        return [n.canal for n in self._notificadores]
    
    def enviar(
        self,
        alerta: Alerta,
        canales: Optional[List[CanalNotificacion]] = None,
    ) -> List[ResultadoEnvio]:
        """
        Envía una alerta por todos los canales configurados (o los especificados).
        
        Args:
            alerta: Alerta a enviar
            canales: Lista opcional de canales específicos a usar
            
        Returns:
            Lista de ResultadoEnvio por cada canal
        """
        resultados = []
        
        for notificador in self._notificadores:
            # Filtrar por canales si se especificaron
            if canales and notificador.canal not in canales:
                continue
            
            # Verificar si el notificador soporta este tipo de alerta
            if not notificador.soporta_tipo(alerta.tipo):
                continue
            
            # Enviar
            resultado = notificador.enviar(alerta)
            resultados.append(resultado)
        
        return resultados
    
    def enviar_con_persistencia(
        self,
        alerta: Alerta,
        canales: Optional[List[CanalNotificacion]] = None,
    ) -> List[ResultadoEnvio]:
        """
        Envía una alerta y persiste el resultado en la base de datos.
        """
        from app.models import NotificacionEmail
        
        resultados = self.enviar(alerta, canales)
        
        # Persistir cada resultado
        for resultado in resultados:
            if resultado.canal == CanalNotificacion.EMAIL:
                NotificacionEmail.objects.create(
                    tipo=alerta.tipo.value,
                    destinatario=', '.join(alerta.destinatarios),
                    cc=', '.join(alerta.cc),
                    asunto=alerta.titulo,
                    contenido=alerta.mensaje,
                    siniestro_id=alerta.siniestro_id,
                    poliza_id=alerta.poliza_id,
                    factura_id=alerta.factura_id,
                    estado='enviado' if resultado.exitoso else 'fallido',
                    fecha_envio=resultado.fecha_envio if resultado.exitoso else None,
                    mensaje_error=resultado.error,
                )
        
        return resultados


# ==============================================================================
# FACTORY - CREAR DISPATCHER CON CONFIGURACIÓN
# ==============================================================================

def crear_dispatcher_desde_config() -> NotificacionDispatcher:
    """
    Crea un NotificacionDispatcher configurado desde ConfiguracionSistema.
    Lee las configuraciones de cada canal y los inicializa si están habilitados.
    """
    from app.models import ConfiguracionSistema
    
    dispatcher = NotificacionDispatcher()
    
    # Email siempre habilitado
    dispatcher.registrar_notificador(EmailNotifier())
    
    # SMS (si está configurado)
    sms_api_key = ConfiguracionSistema.get_config('SMS_API_KEY', None)
    sms_api_secret = ConfiguracionSistema.get_config('SMS_API_SECRET', None)
    if sms_api_key and sms_api_secret:
        dispatcher.registrar_notificador(SMSNotifier(
            api_key=sms_api_key,
            api_secret=sms_api_secret,
            from_number=ConfiguracionSistema.get_config('SMS_FROM_NUMBER', None),
        ))
    
    # WhatsApp (si está configurado)
    wa_token = ConfiguracionSistema.get_config('WHATSAPP_API_TOKEN', None)
    wa_phone_id = ConfiguracionSistema.get_config('WHATSAPP_PHONE_NUMBER_ID', None)
    if wa_token and wa_phone_id:
        dispatcher.registrar_notificador(WhatsAppNotifier(
            api_token=wa_token,
            phone_number_id=wa_phone_id,
        ))
    
    # Webhook (si está configurado)
    webhook_url = ConfiguracionSistema.get_config('NOTIFICACIONES_WEBHOOK_URL', None)
    if webhook_url:
        dispatcher.registrar_notificador(WebhookNotifier(webhook_url=webhook_url))
    
    return dispatcher


# ==============================================================================
# SINGLETON - DISPATCHER GLOBAL
# ==============================================================================

_dispatcher_global: Optional[NotificacionDispatcher] = None


def get_dispatcher() -> NotificacionDispatcher:
    """Obtiene el dispatcher global (singleton lazy)."""
    global _dispatcher_global
    if _dispatcher_global is None:
        _dispatcher_global = crear_dispatcher_desde_config()
    return _dispatcher_global


def reset_dispatcher() -> None:
    """Resetea el dispatcher global (útil para tests)."""
    global _dispatcher_global
    _dispatcher_global = None
