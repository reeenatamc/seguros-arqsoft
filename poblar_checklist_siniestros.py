#!/usr/bin/env python
"""
Script para poblar la configuración del checklist de siniestros.
Ejecutar: python manage.py shell < poblar_checklist_siniestros.py
O: python poblar_checklist_siniestros.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seguros.settings')
django.setup()

from app.models import TipoSiniestro, ChecklistSiniestroConfig

# Primero asegurarnos de que existen los tipos de siniestro
tipos_siniestro = [
    ('daño', 'Daño'),
    ('robo', 'Robo'),
    ('hurto', 'Hurto'),
    ('incendio', 'Incendio'),
    ('inundacion', 'Inundación'),
    ('terremoto', 'Terremoto'),
    ('vandalismo', 'Vandalismo'),
    ('otro', 'Otro'),
]

print("=" * 60)
print("POBLANDO TIPOS DE SINIESTRO Y CHECKLIST")
print("=" * 60)

for nombre, _ in tipos_siniestro:
    tipo, created = TipoSiniestro.objects.get_or_create(
        nombre=nombre,
        defaults={'activo': True}
    )
    if created:
        print(f"✓ Tipo de siniestro creado: {tipo}")
    else:
        print(f"  Tipo de siniestro ya existe: {tipo}")

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

print("\n" + "-" * 60)
print("CREANDO ITEMS DE CHECKLIST POR TIPO DE SINIESTRO")
print("-" * 60)

for tipo in TipoSiniestro.objects.filter(activo=True):
    print(f"\n📋 {tipo.get_nombre_display()}:")
    
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
            print(f"   {obligatorio} {doc['nombre']}")
        else:
            print(f"   ✓ Ya existe: {doc['nombre']}")

print("\n" + "=" * 60)
print("✅ CHECKLIST CONFIGURADO EXITOSAMENTE")
print("=" * 60)

# Mostrar resumen
total_tipos = TipoSiniestro.objects.filter(activo=True).count()
total_items = ChecklistSiniestroConfig.objects.filter(activo=True).count()
print(f"\nResumen:")
print(f"  - Tipos de siniestro activos: {total_tipos}")
print(f"  - Items de checklist totales: {total_items}")
