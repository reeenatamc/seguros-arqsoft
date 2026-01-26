"""

Comando para poblar el catálogo de ramos con datos predefinidos.

Crea la estructura jerárquica: TipoRamo > GrupoRamo > SubgrupoRamo

"""


from django.core.management.base import BaseCommand

from django.db import transaction


from app.models import TipoRamo, GrupoRamo, SubgrupoRamo


class Command(BaseCommand):

    help = 'Pobla el catálogo de ramos con los datos predefinidos de Ramos Generales'

    def add_arguments(self, parser):

        parser.add_argument(

            '--force',

            action='store_true',

            help='Forzar la actualización de datos existentes',

        )

    def handle(self, *args, **options):

        force = options.get('force', False)

        self.stdout.write('Iniciando población del catálogo de ramos...\n')

        with transaction.atomic():

            # Crear tipo principal: Ramos Generales

            tipo_rg, created = TipoRamo.objects.get_or_create(

                codigo='RG',

                defaults={

                    'nombre': 'Ramos Generales',

                    'descripcion': 'Ramos generales de seguros que cubren bienes patrimoniales, responsabilidad civil y otros riesgos no relacionados con la vida.',

                    'es_predefinido': True,

                    'activo': True,

                }

            )

            if created:

                self.stdout.write(self.style.SUCCESS(f'✓ Tipo de ramo creado: {tipo_rg}'))

            else:

                self.stdout.write(f'  Tipo de ramo existente: {tipo_rg}')

            # Definición de grupos y subgrupos

            catalogo = [

                {

                    'codigo': 'G1',

                    'nombre': 'Póliza Incendio y líneas aliadas o multiriesgo',

                    'descripcion': 'Cubre daños por incendio, robo, maquinaria y equipos electrónicos',

                    'orden': 1,

                    'subgrupos': [

                        ('INC', 'Incendio', 'Daños causados por incendio y riesgos aliados', 1),

                        ('LCI', 'Lucro cesante incendio', 'Pérdida de ingresos por paralización debido a incendio', 2),

                        ('LCR', 'Lucro cesante rotura de maquinaria', 'Pérdida de ingresos por falla de maquinaria', 3),

                        ('ROB', 'Robo y Asalto', 'Pérdidas por robo con violencia o asalto', 4),

                        ('RCV', 'Robo contenido y valores', 'Robo de contenido de inmuebles y valores', 5),

                        ('EEL', 'Equipo Electrónico', 'Daños a equipos electrónicos y de cómputo', 6),

                        ('MPR', 'Maquinaria de producción', 'Cobertura de maquinaria industrial y de producción', 7),

                    ]

                },

                {

                    'codigo': 'G2',

                    'nombre': 'Equipo y maquinaria',

                    'descripcion': 'Cobertura para equipos y maquinaria pesada',

                    'orden': 2,

                    'subgrupos': [

                        ('MPE', 'Póliza de Maquinaria pesada', 'Cobertura para maquinaria pesada y de construcción', 1),

                    ]

                },

                {

                    'codigo': 'G3',

                    'nombre': 'Póliza de Transporte',

                    'descripcion': 'Cobertura para transporte de mercancías',

                    'orden': 3,

                    'subgrupos': [

                        ('TIN', 'Póliza de transporte interno', 'Transporte de mercancías dentro del territorio nacional', 1),

                        ('TIM', 'Póliza importación', 'Transporte de mercancías importadas', 2),

                    ]

                },

                {

                    'codigo': 'G4',

                    'nombre': 'Responsabilidad civil',

                    'descripcion': 'Coberturas de responsabilidad civil profesional y directiva',

                    'orden': 4,

                    'subgrupos': [

                        ('RC1', 'Responsabilidad civil profesional 1', 'RC profesional primera capa', 1),

                        ('RC2', 'Responsabilidad civil profesional 2', 'RC profesional segunda capa', 2),

                        ('RCD', 'Responsabilidad civil Altos Directivos', 'D&O - Responsabilidad de directores y administradores', 3),

                        ('RCP', 'Responsabilidad civil profesional', 'RC profesional general', 4),

                    ]

                },

                {

                    'codigo': 'G5',

                    'nombre': 'Póliza de Vehículos',

                    'descripcion': 'Cobertura para vehículos automotores',

                    'orden': 5,

                    'subgrupos': [

                        ('VLI', 'Póliza de vehículo livianos', 'Vehículos livianos: automóviles, camionetas', 1),

                        ('VPE', 'Póliza de vehículos pesados', 'Vehículos pesados: camiones, buses', 2),

                    ]

                },

                {

                    'codigo': 'G6',

                    'nombre': 'Accidentes personales',

                    'descripcion': 'Cobertura de accidentes personales para diferentes grupos',

                    'orden': 6,

                    'subgrupos': [

                        ('APE', 'Accidentes personales estudiantes', 'Cobertura para estudiantes', 1),

                        ('APC', 'Accidentes personales capacitadores', 'Cobertura para capacitadores y docentes', 2),

                        ('APP', 'Accidentes personales personal de proyecto', 'Cobertura para personal de proyectos', 3),

                    ]

                },

                {

                    'codigo': 'G7',

                    'nombre': 'Fianzas',

                    'descripcion': 'Pólizas de fianzas y garantías',

                    'orden': 7,

                    'subgrupos': [

                        ('FIA', 'Pólizas de Fianzas', 'Fianzas de cumplimiento y garantías', 1),

                    ]

                },

                {

                    'codigo': 'G8',

                    'nombre': 'Fidelidad',

                    'descripcion': 'Cobertura contra actos desleales de empleados',

                    'orden': 8,

                    'subgrupos': [

                        ('FID', 'General', 'Seguro de fidelidad general', 1),

                    ]

                },

            ]

            grupos_creados = 0

            grupos_existentes = 0

            subgrupos_creados = 0

            subgrupos_existentes = 0

            for grupo_data in catalogo:

                grupo, created = GrupoRamo.objects.get_or_create(

                    tipo_ramo=tipo_rg,

                    codigo=grupo_data['codigo'],

                    defaults={

                        'nombre': grupo_data['nombre'],

                        'descripcion': grupo_data['descripcion'],

                        'orden': grupo_data['orden'],

                        'es_predefinido': True,

                        'activo': True,

                    }

                )

                if created:

                    grupos_creados += 1

                    self.stdout.write(self.style.SUCCESS(f'  ✓ Grupo creado: {grupo}'))

                else:

                    grupos_existentes += 1

                    if force:

                        grupo.nombre = grupo_data['nombre']

                        grupo.descripcion = grupo_data['descripcion']

                        grupo.orden = grupo_data['orden']

                        grupo.save()

                        self.stdout.write(f'  ↻ Grupo actualizado: {grupo}')

                # Crear subgrupos

                for sub_codigo, sub_nombre, sub_desc, sub_orden in grupo_data['subgrupos']:

                    subgrupo, sub_created = SubgrupoRamo.objects.get_or_create(

                        grupo_ramo=grupo,

                        codigo=sub_codigo,

                        defaults={

                            'nombre': sub_nombre,

                            'descripcion': sub_desc,

                            'orden': sub_orden,

                            'es_predefinido': True,

                            'activo': True,

                        }

                    )

                    if sub_created:

                        subgrupos_creados += 1

                        self.stdout.write(self.style.SUCCESS(f'    ✓ Subgrupo creado: {subgrupo}'))

                    else:

                        subgrupos_existentes += 1

                        if force:

                            subgrupo.nombre = sub_nombre

                            subgrupo.descripcion = sub_desc

                            subgrupo.orden = sub_orden

                            subgrupo.save()

            self.stdout.write('\n' + '='*60)

            self.stdout.write(self.style.SUCCESS('Resumen de población:'))

            self.stdout.write(f'  Tipo de ramo: {"Creado" if created else "Existente"}')

            self.stdout.write(f'  Grupos creados: {grupos_creados}')

            self.stdout.write(f'  Grupos existentes: {grupos_existentes}')

            self.stdout.write(f'  Subgrupos creados: {subgrupos_creados}')

            self.stdout.write(f'  Subgrupos existentes: {subgrupos_existentes}')

            self.stdout.write('='*60 + '\n')

            self.stdout.write(self.style.SUCCESS(

                '¡Catálogo de ramos poblado exitosamente!'

            ))
