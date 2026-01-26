from django.core.management.base import BaseCommand

from app.models import Ramo, SubtipoRamo

class Command(BaseCommand):

    help = "Puebla los datos maestros de RAMOS GENERALES según la tabla del TDR de Seguros UTPL"

    RAMOS = {

        "Poliza Incendio y líneas aliadas o multiriesgo": [

            "Incendio",

            "Lucro cesante incendio",

            "Lucro cesante rotura de maquinaria",

            "Robo y Asalto",

            "Robo contenido y valores",

            "Equipo Electrónico",

            "Maquinaria de producción",

        ],

        "Equip y maquinaria": [

            "Poliza de Maquinaria pesada",

        ],

        "Poliza de Transporte": [

            "Poliza de trasporte interno",

            "Poliza importacion",

        ],

        "Responsabilidad civil": [

            "Responsabilidad civil profesiona 1",

            "Responsabilidad civil profesiona 2",

            "Responsabilidad civil Altos Directivos",

            "Responsabilidad civil profesional",

        ],

        "Poliza de Vehículos": [

            "Poliza de vehiculo livianos",

            "Poliza de vehículos pesados",

        ],

        "Accidentes personales": [

            "Accidentes personales est.",

            "Accidentes personales capacitadores",

            "Accidentes personales personal de proye",

        ],

        "Fianzas": [

            "Polizas de Fianzas",

        ],

        "Fidelidad": [

            "Fidelidad",

        ],

    }

    def handle(self, *args, **options):

        """

        Crea (si no existen) los registros de Ramo (Grupo) y SubtipoRamo (Subgrupos)

        usando exactamente los nombres definidos en el TDR.

        """

        self.stdout.write(self.style.MIGRATE_HEADING("Poblando RAMOS GENERALES según TDR..."))

        for grupo_nombre, subgrupos in self.RAMOS.items():

            codigo_grupo = self._slugify_codigo(grupo_nombre)

            ramo, created = Ramo.objects.get_or_create(

                codigo=codigo_grupo,

                defaults={

                    "nombre": grupo_nombre,

                    "descripcion": grupo_nombre,

                    "activo": True,

                },

            )

            if created:

                self.stdout.write(self.style.SUCCESS(f"Creado Ramo: {grupo_nombre} (código={codigo_grupo})"))

            else:

                self.stdout.write(self.style.WARNING(f"Ramo ya existía: {grupo_nombre} (código={ramo.codigo})"))

            for sg in subgrupos:

                codigo_sg = self._slugify_codigo(sg)

                subtipo, sg_created = SubtipoRamo.objects.get_or_create(

                    ramo=ramo,

                    codigo=codigo_sg,

                    defaults={

                        "nombre": sg,

                        "descripcion": sg,

                        "activo": True,

                    },

                )

                if sg_created:

                    self.stdout.write(self.style.SUCCESS(f"  - Subgrupo creado: {sg} (código={codigo_sg})"))

                else:

                    self.stdout.write(self.style.WARNING(f"  - Subgrupo ya existía: {sg} (código={subtipo.codigo})"))

        self.stdout.write(self.style.SUCCESS("Poblado de RAMOS GENERALES completado."))

    def _slugify_codigo(self, texto: str) -> str:

        """

        Genera un código corto y sin espacios a partir del nombre.

        Se usa solo como identificador interno (no se muestra al usuario).

        """

        import re

        base = texto.upper()

        reemplazos = {

            "Á": "A",

            "É": "E",

            "Í": "I",

            "Ó": "O",

            "Ú": "U",

            "Ü": "U",

            "Ñ": "N",

        }

        for orig, repl in reemplazos.items():

            base = base.replace(orig, repl)

        base = re.sub(r"[^A-Z0-9]+", "_", base)

        base = base.strip("_")

        # Limitar longitud por si acaso

        return base[:20]
