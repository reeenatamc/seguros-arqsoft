from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from app.models import Alerta


class Command(BaseCommand):

    help = "Envía alertas pendientes por correo electrónico"

    def add_arguments(self, parser):
        parser.add_argument("--max", type=int, help="Número máximo de alertas a enviar", default=100)

    def handle(self, *args, **options):
        max_alertas = options["max"]

        self.stdout.write(self.style.SUCCESS("Enviando alertas por correo electrónico..."))

        # Obtener alertas pendientes
        alertas_pendientes = Alerta.objects.filter(estado="pendiente").prefetch_related("destinatarios")[:max_alertas]

        if not alertas_pendientes:
            self.stdout.write(self.style.WARNING("No hay alertas pendientes para enviar"))
            return

        emails_enviados = 0
        emails_fallidos = 0

        for alerta in alertas_pendientes:
            try:
                # Obtener destinatarios
                destinatarios = [user.email for user in alerta.destinatarios.all() if user.email]

                if not destinatarios:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Alerta {alerta.id} sin destinatarios con email"))
                    continue

                # Preparar contexto y enviar según tipo de alerta
                asunto = f"[Sistema de Seguros UTPL] {alerta.titulo}"
                contexto = self.construir_contexto(alerta)

                # Renderizar plantilla HTML
                html_content = render_to_string("emails/alerta_urgente.html", contexto)
                texto_plano = self.construir_texto_plano(alerta)

                # Crear email con HTML
                email = EmailMultiAlternatives(
                    subject=asunto, body=texto_plano, from_email=settings.DEFAULT_FROM_EMAIL, to=destinatarios
                )
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=False)

                # Marcar como enviada
                alerta.marcar_como_enviada()

                emails_enviados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Alerta {alerta.id} ({alerta.tipo_alerta}) enviada a {len(destinatarios)} destinatario(s)"
                    )
                )

            except Exception as e:
                emails_fallidos += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Error al enviar alerta {alerta.id}: {str(e)}"))

        # Resumen
        self.stdout.write(self.style.SUCCESS("\n✓ Proceso completado:"))
        self.stdout.write(f"  - Emails enviados: {emails_enviados}")
        self.stdout.write(f"  - Emails fallidos: {emails_fallidos}")

    def construir_contexto(self, alerta):
        """Construye el contexto para la plantilla HTML según el tipo de alerta"""

        contexto = {
            "titulo": alerta.titulo,
            "nivel_alerta": self._get_nivel_alerta(alerta),
            "prioridad": self._get_prioridad(alerta),
            "intro": [],
            "bloques": [],
            "nota": None,
            "cta_url": getattr(settings, "SITE_URL", "http://localhost:8000"),
            "cta_text": "Ver en el Sistema",
        }

        # Configurar según tipo de alerta
        if alerta.tipo_alerta in ["documentacion_siniestro", "documentacion_pendiente"]:
            contexto["intro"] = [
                "Se ha detectado un siniestro con documentación pendiente que ha excedido el plazo establecido.",
                "Es necesario que el custodio responsable envíe la documentación requerida lo antes posible para continuar con el proceso de reclamo.",
            ]
            contexto["nota"] = (
                "Por favor, contacte al custodio responsable y solicite el envío de los documentos pendientes."
            )

            if alerta.siniestro:
                s = alerta.siniestro
                contexto["bloques"].append(
                    {
                        "titulo": "Información del Siniestro",
                        "filas": [
                            {"label": "Número de Siniestro", "valor": s.numero_siniestro},
                            {"label": "Bien Afectado", "valor": s.bien_nombre},
                            {"label": "Fecha del Siniestro", "valor": s.fecha_siniestro.strftime("%d/%m/%Y")},
                            {"label": "Días sin documentación", "valor": f"{s.dias_desde_registro} días"},
                            {"label": "Estado", "valor": s.get_estado_display()},
                        ],
                    }
                )
                if s.responsable_custodio:
                    contexto["bloques"].append(
                        {
                            "titulo": "Custodio Responsable",
                            "filas": [
                                {"label": "Nombre", "valor": s.responsable_custodio.nombre},
                                {"label": "Email", "valor": s.responsable_custodio.email or "No registrado"},
                            ],
                        }
                    )
                contexto["cta_url"] = f"{contexto['cta_url']}/siniestros/{s.id}/"
                contexto["cta_text"] = "Ver Siniestro"

        elif alerta.tipo_alerta == "respuesta_aseguradora":
            contexto["intro"] = [
                "Se ha detectado un siniestro enviado a la aseguradora que no ha recibido respuesta dentro del plazo establecido.",
                "Es necesario dar seguimiento con el broker/aseguradora para obtener una respuesta sobre el estado del reclamo.",
            ]
            contexto["nota"] = "Por favor, contacte al corredor de seguros para dar seguimiento al estado del reclamo."

            if alerta.siniestro:
                s = alerta.siniestro
                contexto["bloques"].append(
                    {
                        "titulo": "Información del Siniestro",
                        "filas": [
                            {"label": "Número de Siniestro", "valor": s.numero_siniestro},
                            {"label": "Bien Afectado", "valor": s.bien_nombre},
                            {
                                "label": "Fecha de Envío",
                                "valor": (
                                    s.fecha_envio_aseguradora.strftime("%d/%m/%Y")
                                    if s.fecha_envio_aseguradora
                                    else "N/A"
                                ),
                            },
                            {"label": "Días esperando respuesta", "valor": f"{s.dias_espera_respuesta} días"},
                            {"label": "Estado", "valor": s.get_estado_display()},
                        ],
                    }
                )
                if alerta.poliza:
                    contexto["bloques"].append(
                        {
                            "titulo": "Información del Seguro",
                            "filas": [
                                {"label": "Póliza", "valor": alerta.poliza.numero_poliza},
                                {"label": "Aseguradora", "valor": str(alerta.poliza.compania_aseguradora)},
                                {"label": "Corredor", "valor": str(alerta.poliza.corredor_seguros)},
                            ],
                        }
                    )
                contexto["cta_url"] = f"{contexto['cta_url']}/siniestros/{s.id}/"
                contexto["cta_text"] = "Ver Siniestro"

        elif alerta.tipo_alerta == "vencimiento_poliza":
            contexto["intro"] = [
                "Una póliza de seguro está próxima a vencer.",
                "Es necesario gestionar la renovación para mantener la cobertura de los bienes asegurados.",
            ]
            contexto["nota"] = "Inicie el proceso de renovación con el corredor de seguros lo antes posible."

            if alerta.poliza:
                p = alerta.poliza
                contexto["bloques"].append(
                    {
                        "titulo": "Información de la Póliza",
                        "filas": [
                            {"label": "Número de Póliza", "valor": p.numero_poliza},
                            {"label": "Aseguradora", "valor": str(p.compania_aseguradora)},
                            {"label": "Fecha de Vencimiento", "valor": p.fecha_fin.strftime("%d/%m/%Y")},
                            {"label": "Días para vencer", "valor": f"{p.dias_para_vencer} días"},
                        ],
                    }
                )
                contexto["cta_url"] = f"{contexto['cta_url']}/polizas/{p.id}/"
                contexto["cta_text"] = "Ver Póliza"

        elif alerta.tipo_alerta == "factura_vencida":
            contexto["intro"] = [
                "Se ha detectado una factura vencida pendiente de pago.",
                "Es necesario gestionar el pago para evitar problemas con la cobertura del seguro.",
            ]
            contexto["nota"] = "Por favor, gestione el pago de esta factura a la brevedad posible."

            if alerta.factura:
                f = alerta.factura
                contexto["bloques"].append(
                    {
                        "titulo": "Información de la Factura",
                        "filas": [
                            {"label": "Número de Factura", "valor": f.numero_factura},
                            {"label": "Monto Total", "valor": f"${f.monto_total:,.2f}"},
                            {"label": "Saldo Pendiente", "valor": f"${f.saldo_pendiente:,.2f}"},
                            {"label": "Fecha de Vencimiento", "valor": f.fecha_vencimiento.strftime("%d/%m/%Y")},
                        ],
                    }
                )

        else:
            # Alerta genérica
            contexto["intro"] = [alerta.mensaje]

        return contexto

    def _get_nivel_alerta(self, alerta):
        """Obtiene el nivel de alerta para mostrar en el header"""
        niveles = {
            "documentacion_siniestro": "Documentación Pendiente",
            "documentacion_pendiente": "Documentación Pendiente",
            "respuesta_aseguradora": "Respuesta Pendiente",
            "vencimiento_poliza": "Póliza por Vencer",
            "factura_vencida": "Factura Vencida",
        }
        return niveles.get(alerta.tipo_alerta, "Alerta del Sistema")

    def _get_prioridad(self, alerta):
        """Determina la prioridad según el tipo de alerta"""
        prioridades_altas = ["factura_vencida", "respuesta_aseguradora"]
        prioridades_medias = ["documentacion_siniestro", "documentacion_pendiente", "vencimiento_poliza"]

        if alerta.tipo_alerta in prioridades_altas:
            return "alta"
        elif alerta.tipo_alerta in prioridades_medias:
            return "media"
        return "normal"

    def construir_texto_plano(self, alerta):
        """Construye la versión en texto plano del email (fallback)"""
        mensaje = f"""
{alerta.titulo}
{'=' * len(alerta.titulo)}

{alerta.mensaje}

---
Tipo de Alerta: {alerta.get_tipo_alerta_display()}
Fecha de Creación: {alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M')}
"""

        if alerta.siniestro:
            mensaje += f"""
Siniestro Relacionado:
  - Número: {alerta.siniestro.numero_siniestro}
  - Bien: {alerta.siniestro.bien_nombre}
  - Estado: {alerta.siniestro.get_estado_display()}
"""

        if alerta.poliza:
            mensaje += f"""
Póliza Relacionada:
  - Número: {alerta.poliza.numero_poliza}
  - Aseguradora: {alerta.poliza.compania_aseguradora}
"""

        mensaje += f"""
---
Este es un mensaje automático del Sistema de Gestión de Seguros - UTPL.
Para más información, acceda al sistema: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}
"""
        return mensaje

    def construir_mensaje(self, alerta):
        """Construye el mensaje del correo electrónico"""

        mensaje = f"""

{alerta.titulo}

{'=' * len(alerta.titulo)}

{alerta.mensaje}

---

Tipo de Alerta: {alerta.get_tipo_alerta_display()}

Fecha de Creación: {alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M')}

"""

        # Agregar información contextual según el tipo de alerta

        if alerta.poliza:

            mensaje += f"""

Póliza Relacionada:

  - Número: {alerta.poliza.numero_poliza}

  - Compañía: {alerta.poliza.compania_aseguradora}

  - Vigencia: {alerta.poliza.fecha_inicio} al {alerta.poliza.fecha_fin}

"""

        if alerta.factura:

            mensaje += f"""

Factura Relacionada:

  - Número: {alerta.factura.numero_factura}

  - Monto Total: ${alerta.factura.monto_total:,.2f}

  - Saldo Pendiente: ${alerta.factura.saldo_pendiente:,.2f}

  - Fecha de Vencimiento: {alerta.factura.fecha_vencimiento}

"""

        if alerta.siniestro:

            mensaje += f"""

Siniestro Relacionado:

  - Número: {alerta.siniestro.numero_siniestro}

  - Bien: {alerta.siniestro.bien_nombre}

  - Tipo: {alerta.siniestro.tipo_siniestro}

  - Fecha: {alerta.siniestro.fecha_siniestro.strftime('%d/%m/%Y %H:%M')}

  - Estado: {alerta.siniestro.get_estado_display()}

"""

        mensaje += f"""

---

Este es un mensaje automático del Sistema de Gestión de Seguros - UTPL.

Por favor, no responda a este correo.

Para más información, acceda al sistema: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}

"""

        return mensaje
