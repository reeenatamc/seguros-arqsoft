"""

Servicio de notificaciones al Usuario/Reportante.

Responsabilidad única: notificar al usuario que registró algo.

"""

from .base import BaseNotifier


class UserNotifier(BaseNotifier):
    """

    Notificador especializado para comunicaciones con usuarios internos.

    USO:

        notifier = UserNotifier()

        notifier.confirmar_registro_siniestro(siniestro, usuario=request.user)

    """

    def confirmar_registro_siniestro(self, siniestro, usuario):
        """

        Envía confirmación de registro de siniestro al usuario.

        Args:

            siniestro: Instancia del modelo Siniestro

            usuario: Usuario que registró el siniestro

        Returns:

            NotificacionEmail o None si no hay email

        """

        if not usuario or not usuario.email:

            return None

        asunto = f"Confirmación de Registro de Siniestro - {siniestro.numero_siniestro}"

        nombre_usuario = usuario.get_full_name() or usuario.username

        bloques = [
            {
                "titulo": "Información del Siniestro",
                "filas": [
                    {"label": "Número", "valor": siniestro.numero_siniestro},
                    {"label": "Tipo", "valor": self._get_tipo_display(siniestro)},
                    {"label": "Fecha del Siniestro", "valor": siniestro.fecha_siniestro.strftime("%d/%m/%Y %H:%M")},
                    {"label": "Bien Afectado", "valor": siniestro.bien_nombre},
                ],
            },
            {
                "titulo": "Información de la Póliza",
                "filas": [
                    {"label": "Número de Póliza", "valor": siniestro.poliza.numero_poliza},
                    {"label": "Aseguradora", "valor": siniestro.poliza.compania_aseguradora.nombre},
                ],
            },
        ]

        contenido_html = self._renderizar_email(
            titulo=asunto,
            intro=[
                f"Estimado(a) {nombre_usuario},",
                "hemos registrado correctamente su reporte de siniestro. A continuación, el resumen:",
            ],
            bloques=bloques,
            cta_text="Ver siniestro en el sistema",
            cta_url=f"{self._get_site_url()}/siniestros/{siniestro.id}/detalle/",
            nota="Nuestro equipo de gestión de seguros dará seguimiento a su caso.",
        )

        contenido_texto = (
            f"{asunto}\n\n"
            f"Número: {siniestro.numero_siniestro}\n"
            f"Tipo: {self._get_tipo_display(siniestro)}\n"
            f"Fecha del Siniestro: {siniestro.fecha_siniestro.strftime('%d/%m/%Y %H:%M')}\n"
            f"Bien Afectado: {siniestro.bien_nombre}\n"
        )

        notificacion = self._crear_notificacion(
            tipo="siniestro_usuario",
            destinatario=usuario.email,
            asunto=asunto,
            contenido=contenido_texto,
            contenido_html=contenido_html,
            siniestro=siniestro,
            usuario=usuario,
        )

        self._enviar_email(notificacion)

        return notificacion

    def _get_tipo_display(self, siniestro) -> str:

        if siniestro.tipo_siniestro:

            return siniestro.tipo_siniestro.get_nombre_display()

        return "N/A"
