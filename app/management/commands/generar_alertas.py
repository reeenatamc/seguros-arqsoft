from django.core.management.base import BaseCommand

from django.utils import timezone

from django.contrib.auth.models import User

from datetime import timedelta

from app.models import Poliza, Factura, Siniestro, Alerta

class Command(BaseCommand):

    help = 'Genera alertas automáticas para pólizas, facturas y siniestros'

    def add_arguments(self, parser):

        parser.add_argument(

            '--tipo',

            type=str,

            help='Tipo de alerta a generar: polizas, facturas, siniestros, o todas',

            default='todas'

        )

    def handle(self, *args, **options):

        tipo = options['tipo']

        self.stdout.write(self.style.SUCCESS(f'Generando alertas tipo: {tipo}'))

        if tipo in ['polizas', 'todas']:

            self.generar_alertas_polizas()

        if tipo in ['facturas', 'todas']:

            self.generar_alertas_facturas()

        if tipo in ['siniestros', 'todas']:

            self.generar_alertas_siniestros()

        self.stdout.write(self.style.SUCCESS('✓ Generación de alertas completada'))

    def generar_alertas_polizas(self):

        """Genera alertas para pólizas próximas a vencer"""

        self.stdout.write('Generando alertas de pólizas...')

        hoy = timezone.now().date()

        # Usar manager centralizado (DRY)

        polizas_por_vencer = Poliza.objects.por_vencer(dias=30)

        usuarios_admin = User.objects.filter(is_staff=True, is_active=True)

        for poliza in polizas_por_vencer:

            dias_restantes = (poliza.fecha_fin - hoy).days

            # Verificar si ya existe una alerta reciente para esta póliza

            alerta_existente = Alerta.objects.filter(

                poliza=poliza,

                tipo_alerta='vencimiento_poliza',

                fecha_creacion__gte=timezone.now() - timedelta(days=7)

            ).exists()

            if not alerta_existente:

                alerta = Alerta.objects.create(

                    tipo_alerta='vencimiento_poliza',

                    titulo=f'Póliza {poliza.numero_poliza} próxima a vencer',

                    mensaje=f'La póliza {poliza.numero_poliza} de {poliza.compania_aseguradora} '

                           f'vencerá en {dias_restantes} días (Fecha de vencimiento: {poliza.fecha_fin}). '

                           f'Por favor, tome las acciones necesarias para su renovación.',

                    poliza=poliza,

                    estado='pendiente'

                )

                alerta.destinatarios.set(usuarios_admin)

                self.stdout.write(f'  ✓ Alerta creada para póliza {poliza.numero_poliza} ({dias_restantes} días)')

    def generar_alertas_facturas(self):

        """Genera alertas para facturas pendientes y descuentos por pronto pago"""

        self.stdout.write('Generando alertas de facturas...')

        hoy = timezone.now().date()

        usuarios_admin = User.objects.filter(is_staff=True, is_active=True)

        # Alertas de pagos pendientes próximos a vencer

        facturas_pendientes = Factura.objects.filter(

            estado__in=['pendiente', 'parcial'],

            fecha_vencimiento__gte=hoy,

            fecha_vencimiento__lte=hoy + timedelta(days=7)

        )

        for factura in facturas_pendientes:

            dias_restantes = (factura.fecha_vencimiento - hoy).days

            alerta_existente = Alerta.objects.filter(

                factura=factura,

                tipo_alerta='pago_pendiente',

                fecha_creacion__gte=timezone.now() - timedelta(days=3)

            ).exists()

            if not alerta_existente:

                alerta = Alerta.objects.create(

                    tipo_alerta='pago_pendiente',

                    titulo=f'Factura {factura.numero_factura} próxima a vencer',

                    mensaje=f'La factura {factura.numero_factura} de la póliza {factura.poliza.numero_poliza} '

                           f'vencerá en {dias_restantes} días (Fecha de vencimiento: {factura.fecha_vencimiento}). '

                           f'Saldo pendiente: ${factura.saldo_pendiente:,.2f}',

                    factura=factura,

                    poliza=factura.poliza,

                    estado='pendiente'

                )

                alerta.destinatarios.set(usuarios_admin)

                self.stdout.write(f'  ✓ Alerta de pago pendiente para factura {factura.numero_factura}')

        # Alertas de descuento por pronto pago

        fecha_limite_descuento = hoy + timedelta(days=5)

        facturas_con_descuento = Factura.objects.filter(

            estado='pendiente',

            fecha_emision__gte=hoy - timedelta(days=15),

            fecha_emision__lte=hoy - timedelta(days=0)

        )

        for factura in facturas_con_descuento:

            if factura.puede_aplicar_descuento:

                dias_restantes = 20 - (hoy - factura.fecha_emision).days

                alerta_existente = Alerta.objects.filter(

                    factura=factura,

                    tipo_alerta='pronto_pago',

                    fecha_creacion__gte=timezone.now() - timedelta(days=3)

                ).exists()

                if not alerta_existente and dias_restantes <= 5:

                    alerta = Alerta.objects.create(

                        tipo_alerta='pronto_pago',

                        titulo=f'Descuento disponible para factura {factura.numero_factura}',

                        mensaje=f'La factura {factura.numero_factura} tiene disponible un descuento del 5% '

                               f'si se paga dentro de los próximos {dias_restantes} días. '

                               f'Descuento potencial: ${factura.descuento_pronto_pago:,.2f}',

                        factura=factura,

                        poliza=factura.poliza,

                        estado='pendiente'

                    )

                    alerta.destinatarios.set(usuarios_admin)

                    self.stdout.write(f'  ✓ Alerta de pronto pago para factura {factura.numero_factura}')

    def generar_alertas_siniestros(self):

        """Genera alertas para siniestros con documentación o respuesta pendiente"""

        self.stdout.write('Generando alertas de siniestros...')

        usuarios_admin = User.objects.filter(is_staff=True, is_active=True)

        # Alertas por documentación pendiente (más de 30 días)

        siniestros_doc_pendiente = Siniestro.objects.filter(

            estado='documentacion_pendiente'

        )

        for siniestro in siniestros_doc_pendiente:

            if siniestro.requiere_alerta_documentacion:

                # Verificar si ya existe una alerta reciente

                alerta_existente = Alerta.objects.filter(

                    siniestro=siniestro,

                    tipo_alerta='documentacion_pendiente',

                    fecha_creacion__gte=timezone.now() - timedelta(days=8)

                ).exists()

                if not alerta_existente:

                    alerta = Alerta.objects.create(

                        tipo_alerta='documentacion_pendiente',

                        titulo=f'Documentación pendiente para siniestro {siniestro.numero_siniestro}',

                        mensaje=f'El siniestro {siniestro.numero_siniestro} lleva {siniestro.dias_desde_registro} días '

                               f'con documentación pendiente. El plazo establecido es de 30 días. '

                               f'Por favor, complete la documentación necesaria.',

                        siniestro=siniestro,

                        poliza=siniestro.poliza,

                        estado='pendiente'

                    )

                    alerta.destinatarios.set(usuarios_admin)

                    self.stdout.write(f'  ✓ Alerta de documentación para siniestro {siniestro.numero_siniestro}')

        # Alertas por falta de respuesta de aseguradora (más de 8 días)

        siniestros_sin_respuesta = Siniestro.objects.filter(

            estado='enviado_aseguradora',

            fecha_envio_aseguradora__isnull=False,

            fecha_respuesta_aseguradora__isnull=True

        )

        for siniestro in siniestros_sin_respuesta:

            if siniestro.requiere_alerta_respuesta:

                alerta_existente = Alerta.objects.filter(

                    siniestro=siniestro,

                    tipo_alerta='respuesta_aseguradora',

                    fecha_creacion__gte=timezone.now() - timedelta(days=8)

                ).exists()

                if not alerta_existente:

                    alerta = Alerta.objects.create(

                        tipo_alerta='respuesta_aseguradora',

                        titulo=f'Respuesta pendiente de aseguradora - Siniestro {siniestro.numero_siniestro}',

                        mensaje=f'El siniestro {siniestro.numero_siniestro} fue enviado a la aseguradora '

                               f'{siniestro.poliza.compania_aseguradora} hace {siniestro.dias_espera_respuesta} días '

                               f'(Fecha de envío: {siniestro.fecha_envio_aseguradora}). '

                               f'Se ha excedido el plazo de 8 días hábiles para obtener respuesta.',

                        siniestro=siniestro,

                        poliza=siniestro.poliza,

                        estado='pendiente'

                    )

                    alerta.destinatarios.set(usuarios_admin)

                    self.stdout.write(f'  ✓ Alerta de respuesta para siniestro {siniestro.numero_siniestro}')
