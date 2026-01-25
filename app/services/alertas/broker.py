"""
Servicio de notificaciones al Broker/Corredor.
Responsabilidad única: notificar al corredor de seguros.
"""

from datetime import timedelta
from django.utils import timezone
from typing import Optional

from .base import BaseNotifier


class BrokerNotifier(BaseNotifier):
    """
    Notificador especializado para comunicaciones con el broker.
    
    USO:
        notifier = BrokerNotifier()
        notifier.notificar_siniestro(siniestro, usuario=request.user)
    """
    
    def notificar_siniestro(self, siniestro, usuario=None):
        """
        Notifica un nuevo siniestro al broker.
        
        Args:
            siniestro: Instancia del modelo Siniestro
            usuario: Usuario que realiza la acción
            
        Returns:
            NotificacionEmail creada
            
        Raises:
            ValueError: Si no hay email del broker
        """
        email_broker = self._obtener_email_broker(siniestro)
        
        if not email_broker:
            raise ValueError("No se encontró email del broker para notificar")

        asunto = f"Notificación de Siniestro - {siniestro.numero_siniestro}"
        
        bloques = [
            {
                'titulo': 'Información del Siniestro',
                'filas': [
                    {'label': 'Número de Siniestro', 'valor': siniestro.numero_siniestro},
                    {'label': 'Tipo', 'valor': self._get_tipo_display(siniestro)},
                    {'label': 'Fecha del Siniestro', 'valor': siniestro.fecha_siniestro.strftime('%d/%m/%Y %H:%M')},
                    {'label': 'Ubicación', 'valor': siniestro.ubicacion},
                ],
            },
            {
                'titulo': 'Bien Afectado',
                'filas': [
                    {'label': 'Nombre', 'valor': siniestro.bien_nombre},
                    {'label': 'Marca', 'valor': siniestro.bien_marca or 'N/A'},
                    {'label': 'Modelo', 'valor': siniestro.bien_modelo or 'N/A'},
                    {'label': 'Serie', 'valor': siniestro.bien_serie or 'N/A'},
                    {'label': 'Código de Activo', 'valor': siniestro.bien_codigo_activo or 'N/A'},
                ],
            },
            {
                'titulo': 'Póliza Asociada',
                'filas': [
                    {'label': 'Número de Póliza', 'valor': siniestro.poliza.numero_poliza},
                    {'label': 'Aseguradora', 'valor': siniestro.poliza.compania_aseguradora.nombre},
                    {'label': 'Vigencia', 'valor': f"{siniestro.poliza.fecha_inicio.strftime('%d/%m/%Y')} - {siniestro.poliza.fecha_fin.strftime('%d/%m/%Y')}"},
                ],
            },
        ]

        contenido_html = self._renderizar_email(
            titulo=asunto,
            intro=['Se ha registrado un nuevo siniestro que requiere su gestión ante la aseguradora.'],
            bloques=bloques,
            cta_text='Ver siniestro en el sistema',
            cta_url=f"{self._get_site_url()}/siniestros/{siniestro.id}/detalle/",
            nota='Este correo es informativo. Por favor, continúe la gestión según los procedimientos internos.',
        )

        contenido_texto = self._generar_texto_plano(siniestro)

        notificacion = self._crear_notificacion(
            tipo='siniestro_broker',
            destinatario=email_broker,
            asunto=asunto,
            contenido=contenido_texto,
            contenido_html=contenido_html,
            siniestro=siniestro,
            usuario=usuario,
        )

        # Actualizar fechas en el siniestro
        siniestro.fecha_notificacion_broker = timezone.now()
        siniestro.fecha_respuesta_esperada = timezone.now().date() + timedelta(days=7)
        siniestro.save(update_fields=['fecha_notificacion_broker', 'fecha_respuesta_esperada'])

        self._enviar_email(notificacion)
        return notificacion

    def crear_alerta_respuesta(self, siniestro):
        """
        Crea una alerta por respuesta pendiente de la aseguradora.
        
        Args:
            siniestro: Siniestro con respuesta pendiente
            
        Returns:
            NotificacionEmail o None si ya hay alerta reciente
        """
        from app.models import NotificacionEmail
        
        # Verificar si ya hay alerta reciente
        alerta_reciente = NotificacionEmail.objects.filter(
            tipo='alerta_respuesta',
            siniestro=siniestro,
            fecha_creacion__gte=timezone.now() - timedelta(days=2)
        ).exists()

        if alerta_reciente:
            return None

        email_broker = self._obtener_email_broker(siniestro)
        if not email_broker:
            return None

        asunto = f"ALERTA: Respuesta Pendiente - Siniestro {siniestro.numero_siniestro}"
        dias_espera = siniestro.dias_espera_respuesta

        bloques = [
            {
                'titulo': 'Detalle de la Alerta',
                'filas': [
                    {'label': 'Número de Siniestro', 'valor': siniestro.numero_siniestro},
                    {'label': 'Fecha de Envío a Aseguradora', 'valor': siniestro.fecha_envio_aseguradora.strftime('%d/%m/%Y')},
                    {'label': 'Días transcurridos desde envío', 'valor': dias_espera},
                ],
            },
        ]

        contenido_html = self._renderizar_email(
            titulo=asunto,
            intro=['El siguiente siniestro ha excedido el tiempo de espera para respuesta de la aseguradora.'],
            bloques=bloques,
            nota='Por favor, dar seguimiento urgente con la aseguradora.',
        )

        contenido_texto = (
            f"{asunto}\n\n"
            f"Número de Siniestro: {siniestro.numero_siniestro}\n"
            f"Días transcurridos desde envío: {dias_espera}\n"
        )

        notificacion = self._crear_notificacion(
            tipo='alerta_respuesta',
            destinatario=email_broker,
            asunto=asunto,
            contenido=contenido_texto,
            contenido_html=contenido_html,
            siniestro=siniestro,
        )

        self._enviar_email(notificacion)
        return notificacion

    def crear_alerta_deposito(self, siniestro):
        """
        Crea una alerta por depósito de indemnización pendiente.
        
        Args:
            siniestro: Siniestro con depósito pendiente
            
        Returns:
            NotificacionEmail o None si ya hay alerta reciente
        """
        from app.models import NotificacionEmail
        
        alerta_reciente = NotificacionEmail.objects.filter(
            tipo='alerta_deposito',
            siniestro=siniestro,
            fecha_creacion__gte=timezone.now() - timedelta(days=1)
        ).exists()

        if alerta_reciente:
            return None

        email_broker = self._obtener_email_broker(siniestro)
        if not email_broker:
            return None

        asunto = f"ALERTA: Depósito Pendiente - Siniestro {siniestro.numero_siniestro}"
        horas_transcurridas = int(
            (timezone.now() - siniestro.fecha_firma_indemnizacion).total_seconds() / 3600
        )

        bloques = [
            {
                'titulo': 'Detalle de la Alerta',
                'filas': [
                    {'label': 'Número de Siniestro', 'valor': siniestro.numero_siniestro},
                    {'label': 'Fecha de firma', 'valor': siniestro.fecha_firma_indemnizacion.strftime('%d/%m/%Y %H:%M')},
                    {'label': 'Horas transcurridas desde firma', 'valor': horas_transcurridas},
                    {'label': 'Límite de depósito (horas)', 'valor': 72},
                ],
            },
        ]

        contenido_html = self._renderizar_email(
            titulo=asunto,
            intro=['El siniestro tiene el recibo de indemnización firmado pero aún no se ha registrado el depósito.'],
            bloques=bloques,
            nota='Por favor, dar seguimiento al depósito de la indemnización.',
        )

        contenido_texto = (
            f"{asunto}\n\n"
            f"Número de Siniestro: {siniestro.numero_siniestro}\n"
            f"Horas transcurridas desde firma: {horas_transcurridas}\n"
        )

        notificacion = self._crear_notificacion(
            tipo='alerta_deposito',
            destinatario=email_broker,
            asunto=asunto,
            contenido=contenido_texto,
            contenido_html=contenido_html,
            siniestro=siniestro,
        )

        self._enviar_email(notificacion)
        return notificacion

    def _obtener_email_broker(self, siniestro) -> Optional[str]:
        """Obtiene el email del broker desde el siniestro o la póliza."""
        email = getattr(siniestro, 'email_broker', None)
        if not email and siniestro.poliza and siniestro.poliza.corredor_seguros:
            email = siniestro.poliza.corredor_seguros.email
        return email

    def _get_tipo_display(self, siniestro) -> str:
        """Obtiene el display del tipo de siniestro."""
        if siniestro.tipo_siniestro:
            return siniestro.tipo_siniestro.get_nombre_display()
        return 'N/A'

    def _generar_texto_plano(self, siniestro) -> str:
        """Genera versión texto plano del email."""
        return (
            f"Notificación de Siniestro - {siniestro.numero_siniestro}\n\n"
            f"Número de Siniestro: {siniestro.numero_siniestro}\n"
            f"Tipo: {self._get_tipo_display(siniestro)}\n"
            f"Fecha del Siniestro: {siniestro.fecha_siniestro.strftime('%d/%m/%Y %H:%M')}\n"
            f"Ubicación: {siniestro.ubicacion}\n"
        )
