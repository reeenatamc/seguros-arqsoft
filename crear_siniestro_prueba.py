#!/usr/bin/env python

"""Script para crear un siniestro de prueba con checklist."""

import os

import sys

import django

# Setup Django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seguros.settings')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from app.models import (  # noqa: E402

    Siniestro, Poliza, TipoSiniestro,

    ChecklistSiniestroConfig, ChecklistSiniestro,

    ResponsableCustodio

)

from django.utils import timezone  # noqa: E402


def main():

    # Obtener una póliza existente

    poliza = Poliza.objects.first()

    print(f'Póliza: {poliza}')

    if not poliza:

        print('No hay pólizas. Crea una póliza primero.')

        return

    # Obtener tipo de siniestro

    tipo_siniestro = TipoSiniestro.objects.filter(nombre='daño').first()

    if not tipo_siniestro:

        print('No hay tipo de siniestro "daño". Ejecuta poblar_checklist_siniestros.py primero.')

        return

    # Obtener o crear responsable

    responsable, _ = ResponsableCustodio.objects.get_or_create(

        nombre='Juan Pérez',

        defaults={

            'email': 'juan.perez@empresa.com',

            'cargo': 'Analista de Sistemas',

            'departamento': 'TI',

            'activo': True

        }

    )

    # Crear un siniestro

    siniestro, created = Siniestro.objects.get_or_create(

        numero_siniestro='SIN-2024-001',

        defaults={

            'poliza': poliza,

            'tipo_siniestro': tipo_siniestro,

            'fecha_siniestro': timezone.now(),

            'causa': 'Daño por golpe accidental',

            'descripcion_detallada': 'El equipo de cómputo sufrió daños debido a una caída accidental desde el escritorio. La pantalla quedó rota y no enciende.',

            'ubicacion': 'Oficina Principal - Piso 3',

            'bien_nombre': 'Laptop Dell Latitude 7420',

            'bien_marca': 'Dell',

            'bien_modelo': 'Latitude 7420',

            'bien_serie': 'ABC123456',

            'bien_codigo_activo': 'ACT-2024-0001',

            'monto_estimado': 1500.00,

            'estado': 'registrado',

            'responsable_custodio': responsable,

        }

    )

    if created:

        print(f'Siniestro creado: {siniestro}')

        # Crear items de checklist basados en la configuración

        configs = ChecklistSiniestroConfig.objects.filter(

            tipo_siniestro=tipo_siniestro,

            activo=True

        ).order_by('orden')

        for config in configs:

            item, item_created = ChecklistSiniestro.objects.get_or_create(

                siniestro=siniestro,

                config_item=config

            )

            status = '✓ Creado' if item_created else 'Ya existía'

            obligatorio = '🔴' if config.es_obligatorio else '⚪'

            print(f'  {obligatorio} {status}: {config.nombre}')

        print(f'\nTotal items checklist: {siniestro.checklist_items.count()}')

        print(f'\nAccede al siniestro en: http://localhost:8000/siniestros/{siniestro.pk}/')

    else:

        print(f'Siniestro ya existía: {siniestro}')

        items = siniestro.checklist_items.count()

        print(f'Items de checklist: {items}')

        if items == 0:

            print('Creando items de checklist...')

            configs = ChecklistSiniestroConfig.objects.filter(

                tipo_siniestro=tipo_siniestro,

                activo=True

            ).order_by('orden')

            for config in configs:

                ChecklistSiniestro.objects.get_or_create(

                    siniestro=siniestro,

                    config_item=config

                )

                print(f'  Creado: {config.nombre}')

        print(f'\nAccede al siniestro en: http://localhost:8000/siniestros/{siniestro.pk}/')


if __name__ == '__main__':

    main()
