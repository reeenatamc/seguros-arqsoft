from django.core.management.base import BaseCommand


from app.models import Poliza


class Command(BaseCommand):

    help = "Puebla la relación de brokers autorizados por aseguradora a partir de las pólizas existentes."

    def handle(self, *args, **options):

        """

        Recorre todas las pólizas y agrega a cada compañía aseguradora

        los brokers que ya han intermediado pólizas con ella.

        """

        from app.models import CompaniaAseguradora  # import local para evitar ciclos

        self.stdout.write(self.style.MIGRATE_HEADING("Poblando brokers autorizados por aseguradora..."))

        total_relaciones = 0

        for poliza in Poliza.objects.select_related('compania_aseguradora', 'corredor_seguros'):

            if not poliza.compania_aseguradora_id or not poliza.corredor_seguros_id:

                continue

            compania = poliza.compania_aseguradora

            broker = poliza.corredor_seguros

            if not compania.brokers.filter(pk=broker.pk).exists():

                compania.brokers.add(broker)

                total_relaciones += 1

                self.stdout.write(

                    self.style.SUCCESS(

                        f"Vinculado broker '{broker.nombre}' con aseguradora '{compania.nombre}'."

                    )

                )

        self.stdout.write(

            self.style.SUCCESS(

                f"Proceso completado. Relaciones nuevas creadas: {total_relaciones}"

            )

        )
