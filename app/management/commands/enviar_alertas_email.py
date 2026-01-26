from django.core.management.base import BaseCommand

from django.core.mail import send_mail, send_mass_mail

from django.conf import settings

from django.utils import timezone

from app.models import Alerta


class Command(BaseCommand):

    help = 'Envía alertas pendientes por correo electrónico'

    def add_arguments(self, parser):

        parser.add_argument(

            '--max',

            type=int,

            help='Número máximo de alertas a enviar',

            default=100

        )

    def handle(self, *args, **options):

        max_alertas = options['max']

        self.stdout.write(self.style.SUCCESS('Enviando alertas por correo electrónico...'))

        # Obtener alertas pendientes

        alertas_pendientes = Alerta.objects.filter(

            estado='pendiente'

        ).prefetch_related('destinatarios')[:max_alertas]

        if not alertas_pendientes:

            self.stdout.write(self.style.WARNING('No hay alertas pendientes para enviar'))

            return

        emails_enviados = 0

        emails_fallidos = 0

        for alerta in alertas_pendientes:

            try:

                # Preparar el mensaje

                asunto = f'[Sistema de Seguros UTPL] {alerta.titulo}'

                mensaje = self.construir_mensaje(alerta)

                # Obtener destinatarios

                destinatarios = [user.email for user in alerta.destinatarios.all() if user.email]

                if not destinatarios:

                    self.stdout.write(

                        self.style.WARNING(f'  ⚠ Alerta {alerta.id} sin destinatarios con email')

                    )

                    continue

                # Enviar correo

                send_mail(

                    subject=asunto,

                    message=mensaje,

                    from_email=settings.DEFAULT_FROM_EMAIL,

                    recipient_list=destinatarios,

                    fail_silently=False,

                )

                # Marcar como enviada

                alerta.marcar_como_enviada()

                emails_enviados += 1

                self.stdout.write(

                    self.style.SUCCESS(f'  ✓ Alerta {alerta.id} enviada a {len(destinatarios)} destinatario(s)')

                )

            except Exception as e:

                emails_fallidos += 1

                self.stdout.write(

                    self.style.ERROR(f'  ✗ Error al enviar alerta {alerta.id}: {str(e)}')

                )

        # Resumen

        self.stdout.write(self.style.SUCCESS('\n✓ Proceso completado:'))

        self.stdout.write(f'  - Emails enviados: {emails_enviados}')

        self.stdout.write(f'  - Emails fallidos: {emails_fallidos}')

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
