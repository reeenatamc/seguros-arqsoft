"""
Servicio de notificaciones relacionadas con Pólizas.
Responsabilidad única: notificaciones sobre pólizas (vencimiento, renovación).
"""

from .base import BaseNotifier


class PolizaNotifier(BaseNotifier):
    """
    Notificador especializado para comunicaciones sobre pólizas.
    
    USO:
        notifier = PolizaNotifier()
        notifier.notificar_vencimiento(poliza, dias_antes=30)
    """
    
    def notificar_vencimiento(self, poliza, dias_antes: int = 30, usuario=None):
        """
        Notifica sobre el próximo vencimiento de una póliza.
        
        Args:
            poliza: Instancia del modelo Poliza
            dias_antes: Días de anticipación para la notificación
            usuario: Usuario que realiza la acción
            
        Returns:
            NotificacionEmail o None si no hay broker
        """
        email_broker = None
        if poliza.corredor_seguros:
            email_broker = poliza.corredor_seguros.email

        if not email_broker:
            return None

        asunto = f"Aviso de Vencimiento - Póliza {poliza.numero_poliza}"

        bloques = [
            {
                'titulo': 'Información de la Póliza',
                'filas': [
                    {'label': 'Número', 'valor': poliza.numero_poliza},
                    {'label': 'Aseguradora', 'valor': poliza.compania_aseguradora.nombre},
                    {'label': 'Tipo', 'valor': poliza.tipo_poliza.nombre if poliza.tipo_poliza else 'N/A'},
                    {'label': 'Suma Asegurada', 'valor': f"${poliza.suma_asegurada:,.2f}"},
                ],
            },
            {
                'titulo': 'Vigencia',
                'filas': [
                    {'label': 'Fecha de Inicio', 'valor': poliza.fecha_inicio.strftime('%d/%m/%Y')},
                    {'label': 'Fecha de Vencimiento', 'valor': poliza.fecha_fin.strftime('%d/%m/%Y')},
                    {'label': 'Días para vencer', 'valor': poliza.dias_para_vencer},
                ],
            },
        ]

        contenido_html = self._renderizar_email(
            titulo=asunto,
            intro=['La siguiente póliza está próxima a vencer.'],
            bloques=bloques,
            nota='Por favor, iniciar el proceso de renovación con la debida anticipación.',
        )

        contenido_texto = (
            f"{asunto}\n\n"
            f"Número: {poliza.numero_poliza}\n"
            f"Aseguradora: {poliza.compania_aseguradora.nombre}\n"
            f"Fecha de Vencimiento: {poliza.fecha_fin.strftime('%d/%m/%Y')}\n"
            f"Días para vencer: {poliza.dias_para_vencer}\n"
        )

        notificacion = self._crear_notificacion(
            tipo='poliza_vencimiento',
            destinatario=email_broker,
            asunto=asunto,
            contenido=contenido_texto,
            contenido_html=contenido_html,
            poliza=poliza,
            usuario=usuario,
        )

        self._enviar_email(notificacion)
        return notificacion

    def notificar_renovacion(self, poliza_anterior, poliza_nueva, usuario=None):
        """
        Notifica sobre la renovación exitosa de una póliza.
        
        Args:
            poliza_anterior: Póliza que venció
            poliza_nueva: Nueva póliza emitida
            usuario: Usuario que realiza la acción
            
        Returns:
            NotificacionEmail o None
        """
        email_broker = None
        if poliza_nueva.corredor_seguros:
            email_broker = poliza_nueva.corredor_seguros.email

        if not email_broker:
            return None

        asunto = f"Renovación de Póliza - {poliza_nueva.numero_poliza}"

        bloques = [
            {
                'titulo': 'Póliza Anterior',
                'filas': [
                    {'label': 'Número', 'valor': poliza_anterior.numero_poliza},
                    {'label': 'Vigencia', 'valor': f"{poliza_anterior.fecha_inicio.strftime('%d/%m/%Y')} - {poliza_anterior.fecha_fin.strftime('%d/%m/%Y')}"},
                ],
            },
            {
                'titulo': 'Nueva Póliza',
                'filas': [
                    {'label': 'Número', 'valor': poliza_nueva.numero_poliza},
                    {'label': 'Aseguradora', 'valor': poliza_nueva.compania_aseguradora.nombre},
                    {'label': 'Vigencia', 'valor': f"{poliza_nueva.fecha_inicio.strftime('%d/%m/%Y')} - {poliza_nueva.fecha_fin.strftime('%d/%m/%Y')}"},
                    {'label': 'Suma Asegurada', 'valor': f"${poliza_nueva.suma_asegurada:,.2f}"},
                ],
            },
        ]

        contenido_html = self._renderizar_email(
            titulo=asunto,
            intro=['Se ha realizado exitosamente la renovación de la siguiente póliza.'],
            bloques=bloques,
            nota='La nueva póliza ya está vigente.',
        )

        contenido_texto = (
            f"{asunto}\n\n"
            f"Póliza anterior: {poliza_anterior.numero_poliza}\n"
            f"Nueva póliza: {poliza_nueva.numero_poliza}\n"
            f"Nueva vigencia: {poliza_nueva.fecha_inicio.strftime('%d/%m/%Y')} - {poliza_nueva.fecha_fin.strftime('%d/%m/%Y')}\n"
        )

        notificacion = self._crear_notificacion(
            tipo='poliza_renovacion',
            destinatario=email_broker,
            asunto=asunto,
            contenido=contenido_texto,
            contenido_html=contenido_html,
            poliza=poliza_nueva,
            usuario=usuario,
        )

        self._enviar_email(notificacion)
        return notificacion
