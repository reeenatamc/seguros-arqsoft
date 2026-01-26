from django.core.management.base import BaseCommand

from django.contrib.auth import get_user_model

from django.db import transaction

from app.models import (

    CompaniaAseguradora,

    CorredorSeguros,

    TipoPoliza,

    TipoSiniestro,

    Ramo,

    SubtipoRamo,

    SubgrupoRamo,

    Poliza,

    ResponsableCustodio,

    Siniestro,

    GrupoBienes,

    Factura,

    Pago,

    PaymentApproval,

    BienAsegurado,

    PolicyRenewal,

    DetallePolizaRamo,

    ChecklistSiniestro,

    ChecklistSiniestroConfig,

    AdjuntoSiniestro,

)


class Command(BaseCommand):

    help = (

        "Elimina los datos de negocio (pólizas, siniestros, ramos, etc.) y "

        "crea un conjunto mínimo de datos de ejemplo. No toca usuarios del sistema."

    )

    @transaction.atomic
    def handle(self, *args, **options):

        self.stdout.write(self.style.WARNING(

            "ATENCIÓN: Se eliminarán datos de negocio (pólizas, siniestros, ramos, aseguradoras, "

            "brokers, responsables, grupos de bienes). Los usuarios (auth.User) NO se tocan."

        ))

        # Borrar en orden para respetar FKs (siniestros primero, luego pólizas, luego catálogos)

        self.stdout.write("Eliminando adjuntos de siniestros...")

        AdjuntoSiniestro.objects.all().delete()

        self.stdout.write("Eliminando checklists de siniestros...")

        ChecklistSiniestro.objects.all().delete()

        self.stdout.write("Eliminando configuración de checklists...")

        ChecklistSiniestroConfig.objects.all().delete()

        self.stdout.write("Eliminando aprobaciones de pagos...")

        PaymentApproval.objects.all().delete()

        self.stdout.write("Eliminando pagos...")

        Pago.objects.all().delete()

        self.stdout.write("Eliminando facturas...")

        Factura.objects.all().delete()

        self.stdout.write("Eliminando bienes asegurados...")

        BienAsegurado.objects.all().delete()

        self.stdout.write("Eliminando renovaciones...")

        PolicyRenewal.objects.all().delete()

        self.stdout.write("Eliminando siniestros...")

        Siniestro.objects.all().delete()

        self.stdout.write("Eliminando pólizas...")

        Poliza.objects.all().delete()

        self.stdout.write("Eliminando grupos de bienes...")

        GrupoBienes.objects.all().delete()

        self.stdout.write("Eliminando responsables/custodios...")

        ResponsableCustodio.objects.all().delete()

        self.stdout.write("Eliminando ramos y subtipos...")

        SubtipoRamo.objects.all().delete()

        Ramo.objects.all().delete()

        self.stdout.write("Eliminando tipos de póliza...")

        TipoPoliza.objects.all().delete()

        self.stdout.write("Eliminando compañías aseguradoras y corredores...")

        CompaniaAseguradora.objects.all().delete()

        CorredorSeguros.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Datos de negocio eliminados. Creando datos de ejemplo..."))

        # 1) Catálogos básicos

        aseguradora = CompaniaAseguradora.objects.create(

            nombre="Tecniseguros Ejemplo",

            ruc="1790012345001",

            direccion="Loja, Ecuador",

            telefono="072123456",

            email="contacto@tecniseguros-ejemplo.com",

            contacto_nombre="Ejecutivo Comercial",

            contacto_telefono="0999999999",

            activo=True,

        )

        broker = CorredorSeguros.objects.create(

            nombre="Broker UTPL",

            compania_aseguradora=aseguradora,

            ruc="1790098765001",

            direccion="Loja, Ecuador",

            telefono="072654321",

            email="broker@utpl.edu.ec",

            contacto_nombre="Asesor de Seguros",

            contacto_telefono="0988888888",

            activo=True,

        )

        tipo_poliza = TipoPoliza.objects.create(

            nombre="Multiriesgo Incendio",

            descripcion="Póliza multiriesgo de incendio y líneas aliadas",

            activo=True,

        )

        # Ramo y subtipo de ejemplo (si quieres luego puedes usar poblar_ramos_generales)

        ramo = Ramo.objects.create(

            codigo="INCENDIO",

            nombre="Poliza Incendio y líneas aliadas o multiriesgo",

            descripcion="Ramo general de incendio y líneas aliadas",

            activo=True,

            es_predefinido=True,

        )

        subtipo_ramo = SubtipoRamo.objects.create(

            ramo=ramo,

            codigo="INCENDIO_SIMPLE",

            nombre="Incendio",

            descripcion="Cobertura básica de incendio",

            activo=True,

        )

        # 2) Póliza de ejemplo

        from django.utils import timezone

        from decimal import Decimal

        from datetime import timedelta

        hoy = timezone.now().date()

        poliza = Poliza.objects.create(

            numero_poliza="POL-UTPL-0001",

            compania_aseguradora=aseguradora,

            corredor_seguros=broker,

            tipo_poliza=tipo_poliza,

            suma_asegurada=Decimal("50000.00"),

            coberturas="Cobertura de incendio y líneas aliadas para equipos de cómputo.",

            fecha_inicio=hoy - timedelta(days=30),

            fecha_fin=hoy + timedelta(days=335),

            estado="vigente",

            es_gran_contribuyente=False,

        )

        # 2.1) Detalle de póliza por ramo (desglose financiero)

        detalle_ramo = DetallePolizaRamo.objects.create(

            poliza=poliza,

            ramo=ramo,

            subtipo_ramo=subtipo_ramo,

            numero_factura="FAC-UTPL-0001",

            suma_asegurada=Decimal("50000.00"),

            total_prima=Decimal("5000.00"),  # Este valor activará el cálculo automático

            observaciones="Desglose por ramo de incendio para equipos de cómputo.",

        )

        # 3) Responsable y grupo de bienes de ejemplo

        responsable = ResponsableCustodio.objects.create(

            nombre="Juan Pérez",

            cargo="Analista de Sistemas",

            departamento="Tecnologías de la Información",

            email="juan.perez@utpl.edu.ec",

            telefono="0991112223",

            activo=True,

        )

        grupo = GrupoBienes.objects.create(

            nombre="Equipos de Cómputo UTPL",

            descripcion="Grupo de laptops y PCs asegurados",

            ramo=ramo,

        )

        # 4) Siniestro de ejemplo

        tipo_siniestro, _ = TipoSiniestro.objects.get_or_create(

            nombre='daño',

            defaults={

                'descripcion': 'Tipo de siniestro de ejemplo',

                'activo': True,

            }

        )

        siniestro = Siniestro.objects.create(

            poliza=poliza,

            numero_siniestro="SIN-UTPL-0001",

            tipo_siniestro=tipo_siniestro,

            fecha_siniestro=timezone.now() - timedelta(days=1),

            bien_nombre="Laptop Dell Latitude 7420",

            bien_modelo="Latitude 7420",

            bien_serie="ABC123456",

            bien_marca="Dell",

            bien_codigo_activo="ACT-UTPL-0001",

            responsable_custodio=responsable,

            ubicacion="Campus UTPL - Edificio Central",

            causa="Derrame accidental de líquido sobre el teclado.",

            descripcion_detallada="Durante la jornada laboral se derramó café sobre el equipo, causando daños en el teclado y placa base.",

            monto_estimado=Decimal("1200.00"),

            valor_reclamo=Decimal("1200.00"),

            deducible=Decimal("100.00"),

            depreciacion=Decimal("200.00"),

            suma_asegurada_bien=Decimal("1500.00"),

            email_broker=broker.email,

            estado="registrado",

        )

        # 5) Factura de ejemplo

        factura = Factura.objects.create(

            poliza=poliza,

            numero_factura="FAC-UTPL-0001",

            fecha_emision=hoy - timedelta(days=20),

            fecha_vencimiento=hoy + timedelta(days=10),

            subtotal=Decimal("5000.00"),

            iva=Decimal("750.00"),

            monto_total=Decimal("5750.00"),

            estado="pendiente",

        )

        # 6) Pago de ejemplo

        pago = Pago.objects.create(

            factura=factura,

            fecha_pago=hoy - timedelta(days=15),

            monto=Decimal("3000.00"),

            forma_pago="transferencia",

            referencia="TRF-2024-001",

            estado="aprobado",

        )

        # 7) Aprobación de pago de ejemplo

        PaymentApproval.objects.create(

            payment=pago,

            approval_level="level_2",

            required_level="level_2",

            status="approved",

            decision_notes="Aprobado por supervisión",

            digital_signature=True,

        )

        # 8) Bien asegurado de ejemplo

        subgrupo = SubgrupoRamo.objects.first()  # Obtener un subgrupo existente

        bien = BienAsegurado.objects.create(

            poliza=poliza,

            subgrupo_ramo=subgrupo,

            responsable_custodio=responsable,

            grupo_bienes=grupo,

            codigo_bien="ACT-UTPL-0001",

            nombre="Laptop Dell Latitude 7420",

            descripcion="Laptop Dell Latitude 7420 para uso administrativo",

            categoria="Equipos de Cómputo",

            marca="Dell",

            modelo="Latitude 7420",

            serie="ABC123456",

            ubicacion="Campus UTPL - Edificio Central",

            edificio="Edificio Central",

            piso="2",

            departamento="Tecnologías de la Información",

            valor_compra=Decimal("1500.00"),

            valor_actual=Decimal("1200.00"),

            valor_asegurado=Decimal("1500.00"),

            fecha_adquisicion=hoy - timedelta(days=180),

            fecha_garantia=hoy + timedelta(days=545),

            estado="activo",

            condicion="bueno",

        )

        # 9) Renovación de póliza de ejemplo

        renovacion = PolicyRenewal.objects.create(

            original_policy=poliza,

            renewal_number="REN-UTPL-0001",

            notification_date=hoy - timedelta(days=60),

            due_date=hoy + timedelta(days=30),

            original_premium=Decimal("5000.00"),

            proposed_premium=Decimal("5200.00"),

            status="in_progress",

            decision="pending",

            notes="Renovación pendiente de aprobación",

        )

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo creados correctamente."))

        self.stdout.write(self.style.SUCCESS(f"Póliza creada: {poliza.numero_poliza}"))

        self.stdout.write(self.style.SUCCESS(f"Detalle por ramo creado: {detalle_ramo}"))

        self.stdout.write(self.style.SUCCESS(f"Siniestro creado: {siniestro.numero_siniestro}"))

        self.stdout.write(self.style.SUCCESS(f"Factura creada: {factura.numero_factura}"))

        self.stdout.write(self.style.SUCCESS(f"Pago creado: {pago.referencia}"))

        self.stdout.write(self.style.SUCCESS("Aprobación de pago creada"))

        self.stdout.write(self.style.SUCCESS(f"Bien asegurado creado: {bien.asset_code}"))

        self.stdout.write(self.style.SUCCESS(f"Renovación creada: {renovacion.renewal_number}"))
