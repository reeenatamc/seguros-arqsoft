#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seguros.settings')
django.setup()

from decimal import Decimal  # noqa: E402
from datetime import date  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from app.models import (  # noqa: E402
    CompaniaAseguradora, CorredorSeguros, TipoPoliza,
    Poliza, Ramo, DetallePolizaRamo
)

# Crear usuario si no existe
user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})

# Crear compañía aseguradora
compania, _ = CompaniaAseguradora.objects.get_or_create(
    nombre='Tecniseguros',
    defaults={'ruc': '1790123456001', 'activo': True}
)

# Crear corredor
corredor, _ = CorredorSeguros.objects.get_or_create(
    nombre='Broker Agente',
    defaults={'ruc': '1790654321001', 'activo': True}
)

# Crear tipo de póliza
tipo, _ = TipoPoliza.objects.get_or_create(nombre='Todo Riesgo', defaults={'activo': True})

# Inicializar ramos predefinidos
Ramo.crear_ramos_predefinidos()

# Crear póliza
poliza, created = Poliza.objects.get_or_create(
    numero_poliza='429965',
    defaults={
        'compania_aseguradora': compania,
        'corredor_seguros': corredor,
        'tipo_poliza': tipo,
        'suma_asegurada': Decimal('4510000.00'),
        'coberturas': 'Incendio, Lucro Cesante',
        'fecha_inicio': date(2025, 6, 25),
        'fecha_fin': date(2026, 6, 25),
        'estado': 'vigente',
        'es_gran_contribuyente': True,
        'creado_por': user
    }
)

if created:
    print(f'Póliza creada: {poliza.numero_poliza}')
else:
    print(f'Póliza ya existe: {poliza.numero_poliza}')

# Obtener ramos
ramo_incendio = Ramo.objects.get(codigo='INC')
ramo_lucro = Ramo.objects.get(codigo='LCR')  # Lucro cesante rotura de maquinaria
ramo_rotura = Ramo.objects.get(codigo='TIM')  # Rotura de maquinaria

# Crear detalles de ramo (los de la imagen)
detalles_data = [
    {
        'ramo': ramo_incendio,
        'numero_factura': '218549',
        'documento_contable': 'P56-39981',
        'suma_asegurada': Decimal('1000000'),
        'total_prima': Decimal('150000'),
        'emision': Decimal('750'),
    },
    {
        'ramo': ramo_lucro,
        'numero_factura': '218549',
        'documento_contable': 'P56-39981',
        'suma_asegurada': Decimal('10000'),
        'total_prima': Decimal('14000'),
        'emision': Decimal('70'),
    },
    {
        'ramo': ramo_rotura,
        'numero_factura': '218549',
        'documento_contable': 'P56-39981',
        'suma_asegurada': Decimal('3500000'),
        'total_prima': Decimal('2000'),
        'emision': Decimal('10'),
    },
]

# Limpiar detalles anteriores
poliza.detalles_ramo.all().delete()

for d in detalles_data:
    detalle = DetallePolizaRamo.objects.create(
        poliza=poliza,
        ramo=d['ramo'],
        numero_factura=d['numero_factura'],
        documento_contable=d['documento_contable'],
        suma_asegurada=d['suma_asegurada'],
        total_prima=d['total_prima'],
        emision=d['emision'],
    )
    print(f'Detalle creado: {detalle.ramo.nombre} - Prima: ${detalle.total_prima} - Total Facturado: ${detalle.total_facturado}')

print('\n✅ Datos de prueba creados exitosamente!')
print('\n👉 Ve a: http://localhost:8000/polizas/')
print(f'   Haz clic en el ojo 👁 de la póliza {poliza.numero_poliza} para ver la tabla de ramos')
