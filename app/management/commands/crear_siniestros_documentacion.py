from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from app.models import (
    Siniestro,
    Poliza,
    TipoSiniestro,
    ResponsableCustodio,
)


class Command(BaseCommand):
    help = "Crea dos siniestros en estado 'documentacion_pendiente' para pruebas"

    def handle(self, *args, **options):
        # Obtener o crear tipo de siniestro
        tipo_siniestro, _ = TipoSiniestro.objects.get_or_create(
            nombre='daño',
            defaults={
                'descripcion': 'Tipo de siniestro de ejemplo',
                'activo': True,
            }
        )

        # Obtener una póliza existente
        poliza = Poliza.objects.first()
        if not poliza:
            self.stdout.write(self.style.ERROR("No hay pólizas en el sistema. Ejecuta primero 'reset_demo_data'"))
            return

        # Obtener o crear responsables
        responsable1, _ = ResponsableCustodio.objects.get_or_create(
            nombre="María González",
            defaults={
                'cargo': "Coordinadora de Tecnología",
                'departamento': "Tecnologías de la Información",
                'email': "maria.gonzalez@utpl.edu.ec",
                'telefono': "0992223334",
                'activo': True,
            }
        )

        responsable2, _ = ResponsableCustodio.objects.get_or_create(
            nombre="Carlos Ramírez",
            defaults={
                'cargo': "Jefe de Mantenimiento",
                'departamento': "Infraestructura",
                'email': "carlos.ramirez@utpl.edu.ec",
                'telefono': "0993334445",
                'activo': True,
            }
        )

        # Obtener el broker de la póliza
        broker_email = poliza.corredor_seguros.email if poliza.corredor_seguros else ""

        # Crear primer siniestro
        siniestro1, created1 = Siniestro.objects.get_or_create(
            numero_siniestro="SIN-UTPL-DOC-001",
            defaults={
                'poliza': poliza,
                'tipo_siniestro': tipo_siniestro,
                'fecha_siniestro': timezone.now() - timedelta(days=5),
                'bien_nombre': "Monitor Dell UltraSharp 27 pulgadas",
                'bien_modelo': "U2720Q",
                'bien_serie': "DLU2720Q001",
                'bien_marca': "Dell",
                'bien_codigo_activo': "ACT-UTPL-0021",
                'responsable_custodio': responsable1,
                'ubicacion': "Campus UTPL - Edificio Administrativo, Piso 3",
                'causa': "Caída accidental del equipo desde el escritorio durante limpieza.",
                'descripcion_detallada': "El monitor sufrió daños en la pantalla y estructura debido a una caída accidental. Se requiere evaluación técnica para determinar si es reparable o requiere reemplazo total.",
                'monto_estimado': Decimal("450.00"),
                'valor_reclamo': Decimal("450.00"),
                'deducible': Decimal("100.00"),
                'depreciacion': Decimal("50.00"),
                'suma_asegurada_bien': Decimal("500.00"),
                'email_broker': broker_email,
                'estado': 'documentacion_pendiente',
            }
        )

        # Crear segundo siniestro
        siniestro2, created2 = Siniestro.objects.get_or_create(
            numero_siniestro="SIN-UTPL-DOC-002",
            defaults={
                'poliza': poliza,
                'tipo_siniestro': tipo_siniestro,
                'fecha_siniestro': timezone.now() - timedelta(days=3),
                'bien_nombre': "Impresora Multifuncional HP LaserJet Pro",
                'bien_modelo': "M404dn",
                'bien_serie': "HP404DN789",
                'bien_marca': "HP",
                'bien_codigo_activo': "ACT-UTPL-0035",
                'responsable_custodio': responsable2,
                'ubicacion': "Campus UTPL - Biblioteca Central, Sala de Impresión",
                'causa': "Sobrecarga eléctrica que causó daño en la placa principal.",
                'descripcion_detallada': "La impresora dejó de funcionar después de una sobrecarga eléctrica. El técnico de mantenimiento confirmó que la placa principal está dañada y requiere reemplazo. Se necesita documentación técnica y cotización de reparación.",
                'monto_estimado': Decimal("680.00"),
                'valor_reclamo': Decimal("680.00"),
                'deducible': Decimal("150.00"),
                'depreciacion': Decimal("85.00"),
                'suma_asegurada_bien': Decimal("800.00"),
                'email_broker': broker_email,
                'estado': 'documentacion_pendiente',
            }
        )

        if created1:
            self.stdout.write(self.style.SUCCESS(f"Siniestro 1 creado: {siniestro1.numero_siniestro}"))
        else:
            self.stdout.write(self.style.WARNING(f"Siniestro 1 ya existía: {siniestro1.numero_siniestro}"))

        if created2:
            self.stdout.write(self.style.SUCCESS(f"Siniestro 2 creado: {siniestro2.numero_siniestro}"))
        else:
            self.stdout.write(self.style.WARNING(f"Siniestro 2 ya existía: {siniestro2.numero_siniestro}"))

        self.stdout.write(self.style.SUCCESS("\n✅ Siniestros listos para subir documentación!"))
        self.stdout.write(self.style.SUCCESS(f"   - {siniestro1.numero_siniestro}: {siniestro1.bien_nombre}"))
        self.stdout.write(self.style.SUCCESS(f"   - {siniestro2.numero_siniestro}: {siniestro2.bien_nombre}"))
