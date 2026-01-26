"""

Clase base para notificadores específicos.

Contiene la lógica compartida de persistencia y envío.

"""

from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string


class BaseNotifier:
    """

    Clase base con funcionalidad compartida para todos los notificadores.

    No debe usarse directamente - usar las subclases específicas.

    """

    def _crear_notificacion(
        self,
        tipo: str,
        destinatario: str,
        asunto: str,
        contenido: str,
        siniestro=None,
        poliza=None,
        factura=None,
        cc: str = "",
        contenido_html: str = "",
        usuario=None,
    ):
        """Crea un registro de notificación en la base de datos."""

        from app.models import NotificacionEmail

        return NotificacionEmail.objects.create(
            tipo=tipo,
            destinatario=destinatario,
            cc=cc,
            asunto=asunto,
            contenido=contenido,
            contenido_html=contenido_html,
            siniestro=siniestro,
            poliza=poliza,
            factura=factura,
            creado_por=usuario,
        )

    def _enviar_email(self, notificacion) -> bool:
        """Envía el email y actualiza el estado de la notificación."""

        try:

            cc_list = [e.strip() for e in notificacion.cc.split(",") if e.strip()]

            if notificacion.contenido_html:

                email = EmailMultiAlternatives(
                    subject=notificacion.asunto,
                    body=notificacion.contenido,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[notificacion.destinatario],
                    cc=cc_list if cc_list else None,
                )

                email.attach_alternative(notificacion.contenido_html, "text/html")

                email.send(fail_silently=False)

            else:

                send_mail(
                    subject=notificacion.asunto,
                    message=notificacion.contenido,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[notificacion.destinatario],
                    fail_silently=False,
                )

            notificacion.marcar_como_enviado()

            return True

        except Exception as e:

            notificacion.registrar_error(str(e))

            return False

    def _renderizar_email(
        self,
        titulo: str,
        intro: List[str],
        bloques: List[Dict[str, Any]],
        cta_text: Optional[str] = None,
        cta_url: Optional[str] = None,
        nota: Optional[str] = None,
    ) -> str:
        """Renderiza el contenido HTML usando el template base."""

        context = {
            "titulo": titulo,
            "intro": intro,
            "bloques": bloques,
            "cta_text": cta_text,
            "cta_url": cta_url,
            "nota": nota,
        }

        return render_to_string("emails/base_notificacion.html", context)

    def _get_site_url(self) -> str:
        """Obtiene la URL base del sitio."""

        return getattr(settings, "SITE_URL", "")
