from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = "Limpia la base de datos y la vuelve a poblar con todos los datos necesarios"

    def add_arguments(self, parser):

        parser.add_argument(
            "--skip-reset",
            action="store_true",
            help="Omitir el reset de datos (solo poblar checklist y siniestros)",
        )

    def handle(self, *args, **options):

        if not options["skip_reset"]:

            self.stdout.write(self.style.WARNING("\n" + "=" * 60))

            self.stdout.write(self.style.WARNING("PASO 1: LIMPIANDO Y RESETEANDO BASE DE DATOS"))

            self.stdout.write(self.style.WARNING("=" * 60))

            call_command("reset_demo_data")

            self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))

        self.stdout.write(self.style.SUCCESS("PASO 2: CONFIGURANDO CHECKLIST DE SINIESTROS"))

        self.stdout.write(self.style.SUCCESS("=" * 60))

        call_command("poblar_checklist")

        self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))

        self.stdout.write(self.style.SUCCESS("PASO 3: CREANDO SINIESTROS CON DOCUMENTACIÓN PENDIENTE"))

        self.stdout.write(self.style.SUCCESS("=" * 60))

        call_command("crear_siniestros_documentacion")

        self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))

        self.stdout.write(self.style.SUCCESS("✅ SETUP COMPLETO EXITOSO"))

        self.stdout.write(self.style.SUCCESS("=" * 60))

        self.stdout.write(self.style.SUCCESS("\nLa base de datos está lista con:"))

        self.stdout.write(self.style.SUCCESS("  ✓ Datos de ejemplo (pólizas, facturas, pagos, etc.)"))

        self.stdout.write(self.style.SUCCESS("  ✓ Checklist configurado para todos los tipos de siniestro"))

        self.stdout.write(self.style.SUCCESS("  ✓ 2 siniestros en estado 'documentacion_pendiente' con checklist"))
