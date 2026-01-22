from django.core.management.base import BaseCommand
from app.models import TipoSiniestro, ChecklistSiniestroConfig


class Command(BaseCommand):
    help = "Configura el checklist de documentación para todos los tipos de siniestro"

    def handle(self, *args, **options):
        # Documentos estándar para TODOS los tipos de siniestro
        documentos_comunes = [
            {
                'nombre': 'Carta formal de notificación',
                'descripcion': 'Oficio formal dirigido a la aseguradora notificando el siniestro. Incluye datos del equipo afectado y descripción del incidente.',
                'es_obligatorio': True,
                'orden': 1,
            },
            {
                'nombre': 'Informe técnico de causas y daños',
                'descripcion': 'Reporte del responsable/custodio detallando el problema, causa probable y datos del equipo. En caso de robo, adjuntar denuncia policial.',
                'es_obligatorio': True,
                'orden': 2,
            },
            {
                'nombre': 'Proforma de reparación o reposición',
                'descripcion': 'Cotización de reparación del equipo dañado o proforma de reposición si es pérdida total.',
                'es_obligatorio': True,
                'orden': 3,
            },
            {
                'nombre': 'Documento contable de preexistencia',
                'descripcion': 'Documento que certifica la existencia del bien antes del siniestro (registro de inventario, factura de compra, etc.).',
                'es_obligatorio': True,
                'orden': 4,
            },
            {
                'nombre': 'Acta de salvamento',
                'descripcion': 'Acta de entrega del bien dañado a la aseguradora. Solo aplica en caso de pérdida total.',
                'es_obligatorio': False,
                'orden': 5,
            },
            {
                'nombre': 'Fotografías del daño',
                'descripcion': 'Evidencia fotográfica del estado del bien y los daños ocasionados.',
                'es_obligatorio': False,
                'orden': 6,
            },
            {
                'nombre': 'Documentos adicionales',
                'descripcion': 'Cualquier otro documento relevante solicitado por la aseguradora.',
                'es_obligatorio': False,
                'orden': 7,
            },
        ]

        # Documentos específicos por tipo
        documentos_especificos = {
            'robo': [
                {
                    'nombre': 'Denuncia policial',
                    'descripcion': 'Parte policial o denuncia formal del robo ante las autoridades competentes.',
                    'es_obligatorio': True,
                    'orden': 2,  # Reemplaza al informe técnico
                },
            ],
            'hurto': [
                {
                    'nombre': 'Denuncia policial',
                    'descripcion': 'Parte policial o denuncia formal del hurto ante las autoridades competentes.',
                    'es_obligatorio': True,
                    'orden': 2,
                },
            ],
        }

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("CONFIGURANDO CHECKLIST DE SINIESTROS"))
        self.stdout.write("=" * 60)

        # Asegurar que existe el tipo 'daño'
        tipo_dano, _ = TipoSiniestro.objects.get_or_create(
            nombre='daño',
            defaults={
                'descripcion': 'Tipo de siniestro por daño',
                'activo': True,
            }
        )

        # Obtener todos los tipos de siniestro activos
        tipos_siniestro = TipoSiniestro.objects.filter(activo=True)

        for tipo in tipos_siniestro:
            self.stdout.write(f"\n📋 {tipo.get_nombre_display()}:")

            # Obtener documentos para este tipo
            docs_a_crear = documentos_comunes.copy()

            # Si hay documentos específicos, modificar la lista
            if tipo.nombre in documentos_especificos:
                # Reemplazar o agregar documentos específicos
                for doc_esp in documentos_especificos[tipo.nombre]:
                    # Buscar si hay uno con el mismo orden para reemplazar
                    for i, doc in enumerate(docs_a_crear):
                        if doc['orden'] == doc_esp['orden']:
                            docs_a_crear[i] = doc_esp
                            break
                    else:
                        docs_a_crear.append(doc_esp)

            # Crear los items de checklist
            for doc in docs_a_crear:
                item, created = ChecklistSiniestroConfig.objects.get_or_create(
                    tipo_siniestro=tipo,
                    nombre=doc['nombre'],
                    defaults={
                        'descripcion': doc['descripcion'],
                        'es_obligatorio': doc['es_obligatorio'],
                        'orden': doc['orden'],
                        'activo': True,
                    }
                )
                if created:
                    obligatorio = "🔴" if doc['es_obligatorio'] else "⚪"
                    self.stdout.write(self.style.SUCCESS(f"   {obligatorio} {doc['nombre']}"))
                else:
                    self.stdout.write(f"   ✓ Ya existe: {doc['nombre']}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ CHECKLIST CONFIGURADO EXITOSAMENTE"))
        self.stdout.write("=" * 60)

        # Mostrar resumen
        total_tipos = TipoSiniestro.objects.filter(activo=True).count()
        total_items = ChecklistSiniestroConfig.objects.filter(activo=True).count()
        self.stdout.write(f"\nResumen:")
        self.stdout.write(f"  - Tipos de siniestro activos: {total_tipos}")
        self.stdout.write(f"  - Items de checklist totales: {total_items}")
