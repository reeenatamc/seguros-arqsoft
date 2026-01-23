"""
Comando para poblar siniestros con datos completos para el reporte de contaduría.
Incluye todas las fechas de gestión y montos financieros.

Uso: python manage.py poblar_siniestros_contadora
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random

from app.models import (
    Poliza, Siniestro, TipoSiniestro, ResponsableCustodio,
    CompaniaAseguradora, CorredorSeguros, TipoPoliza
)


class Command(BaseCommand):
    help = 'Poblar siniestros con datos completos para el reporte de contaduría'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🚀 Iniciando población de siniestros para contaduría...'))
        
        # Obtener o crear usuario admin
        admin_user = self.get_or_create_admin()
        
        # Crear datos base si no existen
        companias = self.crear_companias_si_no_existen()
        corredores = self.crear_corredores_si_no_existen(companias)
        tipos_poliza = self.crear_tipos_poliza_si_no_existen()
        tipos_siniestro = self.crear_tipos_siniestro_si_no_existen()
        responsables = self.crear_responsables_si_no_existen()
        
        # Crear pólizas si no hay suficientes
        polizas = list(Poliza.objects.all()[:20])
        if len(polizas) < 5:
            polizas = self.crear_polizas(companias, corredores, tipos_poliza, admin_user)
        
        # Crear siniestros con datos completos
        siniestros = self.crear_siniestros_completos(
            polizas, tipos_siniestro, responsables, admin_user
        )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✅ Datos creados exitosamente!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'   Siniestros creados: {len(siniestros)}')
        self.stdout.write(f'   URL del reporte: /reportes/dias-gestion/')
        self.stdout.write('')

    def get_or_create_admin(self):
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@utpl.edu.ec',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Administrador',
                'last_name': 'Sistema'
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
        return user

    def crear_companias_si_no_existen(self):
        if CompaniaAseguradora.objects.exists():
            return list(CompaniaAseguradora.objects.filter(activo=True))
        
        companias_data = [
            {'nombre': 'Seguros Equinoccial', 'ruc': '1790010234001'},
            {'nombre': 'AIG Metropolitana', 'ruc': '1791251237001'},
            {'nombre': 'Seguros Sucre', 'ruc': '1790014975001'},
        ]
        
        companias = []
        for data in companias_data:
            compania, _ = CompaniaAseguradora.objects.get_or_create(
                ruc=data['ruc'],
                defaults={
                    'nombre': data['nombre'],
                    'direccion': 'Av. Principal 123, Quito',
                    'telefono': f'02-{random.randint(200,299)}-{random.randint(1000,9999)}',
                    'email': f'contacto@{data["nombre"].lower().replace(" ", "")}.com',
                    'activo': True
                }
            )
            companias.append(compania)
        return companias

    def crear_corredores_si_no_existen(self, companias):
        if CorredorSeguros.objects.exists():
            return list(CorredorSeguros.objects.filter(activo=True))
        
        corredores_data = [
            {'nombre': 'Tecniseguros', 'ruc': '1792345678001'},
            {'nombre': 'Asertec', 'ruc': '1791234567001'},
        ]
        
        corredores = []
        for data in corredores_data:
            corredor, _ = CorredorSeguros.objects.get_or_create(
                ruc=data['ruc'],
                defaults={
                    'nombre': data['nombre'],
                    'direccion': 'Calle Comercial 456, Guayaquil',
                    'telefono': f'04-{random.randint(200,299)}-{random.randint(1000,9999)}',
                    'email': f'info@{data["nombre"].lower()}.com',
                    'compania_aseguradora': random.choice(companias) if companias else None,
                    'activo': True
                }
            )
            corredores.append(corredor)
        return corredores

    def crear_tipos_poliza_si_no_existen(self):
        if TipoPoliza.objects.exists():
            return list(TipoPoliza.objects.filter(activo=True))
        
        tipos_data = [
            {'nombre': 'Vehículos', 'descripcion': 'Seguro para automóviles'},
            {'nombre': 'Incendio', 'descripcion': 'Seguro contra incendios'},
            {'nombre': 'Equipo Electrónico', 'descripcion': 'Seguro para equipos'},
        ]
        
        tipos = []
        for data in tipos_data:
            tipo, _ = TipoPoliza.objects.get_or_create(
                nombre=data['nombre'],
                defaults={'descripcion': data['descripcion'], 'activo': True}
            )
            tipos.append(tipo)
        return tipos

    def crear_tipos_siniestro_si_no_existen(self):
        if TipoSiniestro.objects.exists():
            return list(TipoSiniestro.objects.filter(activo=True))
        
        tipos_data = [
            'Daño accidental', 'Robo', 'Hurto', 'Incendio', 
            'Colisión vehicular', 'Cortocircuito', 'Vandalismo'
        ]
        
        tipos = []
        for nombre in tipos_data:
            tipo, _ = TipoSiniestro.objects.get_or_create(
                nombre=nombre,
                defaults={'activo': True}
            )
            tipos.append(tipo)
        return tipos

    def crear_responsables_si_no_existen(self):
        if ResponsableCustodio.objects.exists():
            return list(ResponsableCustodio.objects.filter(activo=True))
        
        responsables_data = [
            {'nombre': 'Juan Pérez', 'departamento': 'Informática'},
            {'nombre': 'María González', 'departamento': 'Administración'},
            {'nombre': 'Carlos Rodríguez', 'departamento': 'Contabilidad'},
            {'nombre': 'Ana Martínez', 'departamento': 'Recursos Humanos'},
        ]
        
        responsables = []
        for data in responsables_data:
            responsable, _ = ResponsableCustodio.objects.get_or_create(
                nombre=data['nombre'],
                defaults={
                    'departamento': data['departamento'],
                    'cargo': 'Jefe de Área',
                    'email': f'{data["nombre"].lower().replace(" ", ".")}@utpl.edu.ec',
                    'activo': True
                }
            )
            responsables.append(responsable)
        return responsables

    def crear_polizas(self, companias, corredores, tipos, usuario):
        hoy = timezone.now().date()
        polizas = []
        
        for i in range(10):
            poliza = Poliza.objects.create(
                numero_poliza=f'POL-{hoy.year}-{random.randint(10000, 99999)}',
                compania_aseguradora=random.choice(companias),
                corredor_seguros=random.choice(corredores) if corredores else None,
                tipo_poliza=random.choice(tipos),
                suma_asegurada=Decimal(random.randint(50000, 500000)),
                coberturas='Cobertura completa',
                fecha_inicio=hoy - timedelta(days=random.randint(30, 365)),
                fecha_fin=hoy + timedelta(days=random.randint(30, 365)),
                creado_por=usuario
            )
            polizas.append(poliza)
        
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(polizas)} pólizas creadas'))
        return polizas

    def crear_siniestros_completos(self, polizas, tipos_siniestro, responsables, usuario):
        """Crea siniestros con TODAS las fechas de gestión para el reporte de contaduría"""
        from django.db import connection
        
        hoy = timezone.now()
        siniestros_creados = 0
        
        # Estados con sus pesos de distribución
        estados_config = [
            ('registrado', 10, False, False, False, False),
            ('documentacion_pendiente', 15, False, False, False, False),
            ('enviado_aseguradora', 15, True, False, False, False),
            ('en_evaluacion', 15, True, True, False, False),
            ('aprobado', 10, True, True, False, False),
            ('liquidado', 25, True, True, True, True),
            ('cerrado', 5, True, True, True, True),
            ('rechazado', 5, True, True, False, False),
        ]
        
        bienes = [
            ('Laptop HP ProBook', 'HP', 'ProBook 450'),
            ('MacBook Pro 14"', 'Apple', 'M3 Pro'),
            ('Toyota Corolla 2023', 'Toyota', 'Corolla XEI'),
            ('Servidor Dell', 'Dell', 'PowerEdge R740'),
        ]
        
        ubicaciones = ['Edificio A', 'Edificio B', 'Bodega Central', 'Parqueadero']
        
        self.stdout.write('     Creando siniestros...')
        
        # Crear 30 siniestros (reducido para velocidad)
        for i in range(30):
            estado_cfg = random.choices(estados_config, weights=[cfg[1] for cfg in estados_config])[0]
            estado, _, tiene_envio, tiene_respuesta, tiene_liquidacion, tiene_pago = estado_cfg
            
            poliza = random.choice(polizas)
            tipo = random.choice(tipos_siniestro)
            bien = random.choice(bienes)
            
            # Fecha del siniestro dentro de la vigencia de la póliza
            dias_desde_inicio = random.randint(10, 180)
            fecha_siniestro_date = poliza.fecha_inicio + timedelta(days=dias_desde_inicio)
            
            if fecha_siniestro_date > hoy.date():
                fecha_siniestro_date = hoy.date() - timedelta(days=random.randint(10, 90))
            
            fecha_siniestro = timezone.make_aware(
                timezone.datetime.combine(fecha_siniestro_date, timezone.datetime.min.time())
            ) + timedelta(hours=random.randint(8, 17))
            
            monto_estimado = Decimal(random.randint(1000, 30000))
            
            # Preparar datos
            data = {
                'poliza_id': poliza.id,
                'numero_siniestro': f'SIN-{hoy.year}-{10000 + i}',
                'tipo_siniestro_id': tipo.id,
                'fecha_siniestro': fecha_siniestro,
                'bien_nombre': bien[0],
                'bien_marca': bien[1],
                'bien_modelo': bien[2],
                'bien_serie': f'SN-{100000 + i}',
                'ubicacion': random.choice(ubicaciones),
                'causa': 'Daño durante operación normal',
                'descripcion_detallada': f'Siniestro #{i+1} - Reporte detallado del incidente.',
                'monto_estimado': monto_estimado,
                'estado': estado,
                'creado_por_id': usuario.id,
            }
            
            if responsables:
                data['responsable_custodio_id'] = random.choice(responsables).id
            
            # Fechas de gestión
            fecha_base = fecha_siniestro_date
            
            if tiene_envio:
                data['fecha_envio_aseguradora'] = fecha_base + timedelta(days=random.randint(2, 5))
            
            if tiene_respuesta and 'fecha_envio_aseguradora' in data:
                data['fecha_respuesta_aseguradora'] = data['fecha_envio_aseguradora'] + timedelta(days=random.randint(5, 20))
            
            if tiene_liquidacion and 'fecha_respuesta_aseguradora' in data:
                data['fecha_liquidacion'] = data['fecha_respuesta_aseguradora'] + timedelta(days=random.randint(3, 10))
                data['monto_indemnizado'] = (monto_estimado * Decimal('0.9')).quantize(Decimal('0.01'))
                data['deducible_aplicado'] = (monto_estimado * Decimal('0.1')).quantize(Decimal('0.01'))
            
            if tiene_pago and 'fecha_liquidacion' in data:
                data['fecha_pago'] = data['fecha_liquidacion'] + timedelta(days=random.randint(1, 5))
                data['valor_pagado'] = data.get('monto_indemnizado', monto_estimado) - data.get('deducible_aplicado', Decimal('0'))
            
            if estado == 'rechazado':
                data['monto_indemnizado'] = Decimal('0')
                data['observaciones'] = 'Rechazado: No cumple condiciones de póliza.'
            
            # Crear usando bulk_create para velocidad (sin validación)
            try:
                siniestro = Siniestro.objects.create(**data)
                siniestros_creados += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'     Error creando siniestro {i}: {e}'))
                continue
        
        self.stdout.write(self.style.SUCCESS(f'     ✓ {siniestros_creados} siniestros creados'))
        return list(Siniestro.objects.all()[:30])
