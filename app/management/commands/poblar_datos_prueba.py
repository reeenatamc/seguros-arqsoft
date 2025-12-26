"""
Comando para poblar la base de datos con datos de prueba.
Uso: python manage.py poblar_datos_prueba
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from app.models import (
    ConfiguracionSistema, CompaniaAseguradora, CorredorSeguros, 
    TipoPoliza, ResponsableCustodio, Poliza, Factura, Pago, TipoSiniestro, Siniestro, Alerta
)


class Command(BaseCommand):
    help = 'Poblar la base de datos con datos de prueba'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpiar datos existentes antes de poblar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('🚀 Iniciando población de datos de prueba...'))
        
        if options['limpiar']:
            self.limpiar_datos()
        
        # Crear usuario admin si no existe
        admin_user = self.crear_usuario_admin()
        
        # 1. Configuración del sistema
        self.stdout.write('  📝 Creando configuraciones del sistema...')
        ConfiguracionSistema.inicializar_valores_default()
        self.stdout.write(self.style.SUCCESS('     ✓ Configuraciones creadas'))
        
        # 2. Compañías aseguradoras
        self.stdout.write('  🏢 Creando compañías aseguradoras...')
        companias = self.crear_companias()
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(companias)} compañías creadas'))
        
        # 3. Corredores de seguros
        self.stdout.write('  👔 Creando corredores de seguros...')
        corredores = self.crear_corredores()
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(corredores)} corredores creados'))
        
        # 4. Tipos de póliza
        self.stdout.write('  📋 Creando tipos de póliza...')
        tipos_poliza = self.crear_tipos_poliza()
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(tipos_poliza)} tipos de póliza creados'))
        
        # 5. Tipos de siniestro
        self.stdout.write('  ⚠️ Creando tipos de siniestro...')
        tipos_siniestro = self.crear_tipos_siniestro()
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(tipos_siniestro)} tipos de siniestro creados'))
        
        # 6. Pólizas
        self.stdout.write('  📄 Creando pólizas...')
        polizas = self.crear_polizas(companias, corredores, tipos_poliza, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(polizas)} pólizas creadas'))
        
        # 7. Facturas
        self.stdout.write('  💰 Creando facturas...')
        facturas = self.crear_facturas(polizas, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(facturas)} facturas creadas'))
        
        # 8. Pagos
        self.stdout.write('  💳 Creando pagos...')
        pagos = self.crear_pagos(facturas, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(pagos)} pagos creados'))
        
        # 9. Siniestros
        self.stdout.write('  🚗 Creando siniestros...')
        siniestros = self.crear_siniestros(polizas, tipos_siniestro, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(siniestros)} siniestros creados'))
        
        # 10. Actualizar estados
        self.stdout.write('  🔄 Actualizando estados...')
        self.actualizar_estados(polizas, facturas)
        self.stdout.write(self.style.SUCCESS('     ✓ Estados actualizados'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('✅ ¡Datos de prueba creados exitosamente!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write(f'   Usuario admin: admin / admin123')
        self.stdout.write(f'   Pólizas: {len(polizas)}')
        self.stdout.write(f'   Facturas: {len(facturas)}')
        self.stdout.write(f'   Pagos: {len(pagos)}')
        self.stdout.write(f'   Siniestros: {len(siniestros)}')
        self.stdout.write('')

    def limpiar_datos(self):
        self.stdout.write(self.style.WARNING('  🗑️ Limpiando datos existentes...'))
        Alerta.objects.all().delete()
        Pago.objects.all().delete()
        Siniestro.objects.all().delete()
        Factura.objects.all().delete()
        Poliza.objects.all().delete()
        TipoSiniestro.objects.all().delete()
        TipoPoliza.objects.all().delete()
        CorredorSeguros.objects.all().delete()
        CompaniaAseguradora.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('     ✓ Datos limpiados'))

    def crear_usuario_admin(self):
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

    def crear_companias(self):
        companias_data = [
            {'nombre': 'Seguros Equinoccial', 'ruc': '1790010234001'},
            {'nombre': 'AIG Metropolitana', 'ruc': '1791251237001'},
            {'nombre': 'Seguros Sucre', 'ruc': '1790014975001'},
            {'nombre': 'Liberty Seguros', 'ruc': '1792145678001'},
            {'nombre': 'Aseguradora del Sur', 'ruc': '1791408780001'},
        ]
        
        companias = []
        for data in companias_data:
            compania, _ = CompaniaAseguradora.objects.get_or_create(
                ruc=data['ruc'],
                defaults={
                    'nombre': data['nombre'],
                    'direccion': f'Av. Principal 123, Quito',
                    'telefono': f'02-{random.randint(200,299)}-{random.randint(1000,9999)}',
                    'email': f'contacto@{data["nombre"].lower().replace(" ", "")}.com',
                    'contacto_nombre': f'Juan Pérez',
                    'activo': True
                }
            )
            companias.append(compania)
        return companias

    def crear_corredores(self):
        corredores_data = [
            {'nombre': 'Tecniseguros', 'ruc': '1792345678001'},
            {'nombre': 'Asertec', 'ruc': '1791234567001'},
            {'nombre': 'Nova Corredores', 'ruc': '1793456789001'},
        ]
        
        corredores = []
        for data in corredores_data:
            corredor, _ = CorredorSeguros.objects.get_or_create(
                ruc=data['ruc'],
                defaults={
                    'nombre': data['nombre'],
                    'direccion': f'Calle Comercial 456, Guayaquil',
                    'telefono': f'04-{random.randint(200,299)}-{random.randint(1000,9999)}',
                    'email': f'info@{data["nombre"].lower()}.com',
                    'activo': True
                }
            )
            corredores.append(corredor)
        return corredores

    def crear_tipos_poliza(self):
        tipos_data = [
            {'nombre': 'Vehículos', 'descripcion': 'Seguro para automóviles y motocicletas'},
            {'nombre': 'Incendio', 'descripcion': 'Seguro contra incendios y riesgos aliados'},
            {'nombre': 'Robo', 'descripcion': 'Seguro contra robo y asalto'},
            {'nombre': 'Responsabilidad Civil', 'descripcion': 'Cobertura de responsabilidad civil'},
            {'nombre': 'Equipo Electrónico', 'descripcion': 'Seguro para equipos electrónicos'},
            {'nombre': 'Todo Riesgo', 'descripcion': 'Cobertura integral todo riesgo'},
        ]
        
        tipos = []
        for data in tipos_data:
            tipo, _ = TipoPoliza.objects.get_or_create(
                nombre=data['nombre'],
                defaults={'descripcion': data['descripcion'], 'activo': True}
            )
            tipos.append(tipo)
        return tipos

    def crear_tipos_siniestro(self):
        tipos_nombres = ['daño', 'robo', 'hurto', 'incendio', 'inundacion', 'vandalismo']
        
        tipos = []
        for nombre in tipos_nombres:
            tipo, _ = TipoSiniestro.objects.get_or_create(
                nombre=nombre,
                defaults={'activo': True}
            )
            tipos.append(tipo)
        return tipos

    def crear_polizas(self, companias, corredores, tipos, usuario):
        hoy = timezone.now().date()
        polizas = []
        
        # Pólizas vigentes
        for i in range(8):
            dias_inicio = random.randint(-180, -30)
            dias_fin = random.randint(30, 365)
            
            poliza = Poliza.objects.create(
                numero_poliza=f'POL-{2024}-{1000 + i}',
                compania_aseguradora=random.choice(companias),
                corredor_seguros=random.choice(corredores),
                tipo_poliza=random.choice(tipos),
                suma_asegurada=Decimal(random.randint(10000, 500000)),
                coberturas=f'Cobertura completa para póliza {i+1}. Incluye daños materiales, responsabilidad civil y asistencia.',
                fecha_inicio=hoy + timedelta(days=dias_inicio),
                fecha_fin=hoy + timedelta(days=dias_fin),
                creado_por=usuario,
                observaciones='Póliza de prueba'
            )
            polizas.append(poliza)
        
        # Pólizas por vencer (próximos 30 días)
        for i in range(4):
            dias_fin = random.randint(5, 25)
            
            poliza = Poliza.objects.create(
                numero_poliza=f'POL-{2024}-{2000 + i}',
                compania_aseguradora=random.choice(companias),
                corredor_seguros=random.choice(corredores),
                tipo_poliza=random.choice(tipos),
                suma_asegurada=Decimal(random.randint(20000, 300000)),
                coberturas='Cobertura estándar con límites definidos.',
                fecha_inicio=hoy - timedelta(days=335),
                fecha_fin=hoy + timedelta(days=dias_fin),
                creado_por=usuario
            )
            polizas.append(poliza)
        
        # Pólizas vencidas
        for i in range(3):
            dias_fin = random.randint(-90, -5)
            
            poliza = Poliza.objects.create(
                numero_poliza=f'POL-{2023}-{3000 + i}',
                compania_aseguradora=random.choice(companias),
                corredor_seguros=random.choice(corredores),
                tipo_poliza=random.choice(tipos),
                suma_asegurada=Decimal(random.randint(15000, 200000)),
                coberturas='Cobertura básica.',
                fecha_inicio=hoy + timedelta(days=dias_fin - 365),
                fecha_fin=hoy + timedelta(days=dias_fin),
                creado_por=usuario
            )
            polizas.append(poliza)
        
        return polizas

    def crear_facturas(self, polizas, usuario):
        hoy = timezone.now().date()
        facturas = []
        
        for i, poliza in enumerate(polizas[:12]):  # Solo las primeras 12 pólizas
            dias_emision = random.randint(-60, -5)
            
            factura = Factura.objects.create(
                poliza=poliza,
                numero_factura=f'FAC-{2024}-{5000 + i}',
                fecha_emision=hoy + timedelta(days=dias_emision),
                fecha_vencimiento=hoy + timedelta(days=dias_emision + 30),
                subtotal=Decimal(random.randint(500, 5000)),
                iva=Decimal('0.00'),  # Se calcula automáticamente
                creado_por=usuario
            )
            facturas.append(factura)
        
        return facturas

    def crear_pagos(self, facturas, usuario):
        hoy = timezone.now().date()
        pagos = []
        formas_pago = ['transferencia', 'cheque', 'efectivo', 'tarjeta']
        
        # Pagar completamente algunas facturas
        for factura in facturas[:5]:
            pago = Pago.objects.create(
                factura=factura,
                fecha_pago=factura.fecha_emision + timedelta(days=random.randint(1, 15)),
                monto=factura.monto_total,
                forma_pago=random.choice(formas_pago),
                referencia=f'REF-{random.randint(10000, 99999)}',
                estado='aprobado',
                registrado_por=usuario
            )
            pagos.append(pago)
        
        # Pagos parciales
        for factura in facturas[5:8]:
            monto_parcial = factura.monto_total * Decimal('0.5')
            pago = Pago.objects.create(
                factura=factura,
                fecha_pago=factura.fecha_emision + timedelta(days=random.randint(5, 20)),
                monto=monto_parcial,
                forma_pago=random.choice(formas_pago),
                referencia=f'REF-{random.randint(10000, 99999)}',
                estado='aprobado',
                registrado_por=usuario
            )
            pagos.append(pago)
        
        return pagos

    def crear_responsables(self):
        """Crea responsables/custodios de prueba"""
        departamentos = [
            'Informática', 'Administración', 'Recursos Humanos', 
            'Contabilidad', 'Mantenimiento', 'Seguridad'
        ]
        cargos = [
            'Jefe de Departamento', 'Coordinador', 'Supervisor',
            'Analista', 'Técnico', 'Asistente'
        ]
        nombres = [
            'Juan Pérez', 'María González', 'Carlos Rodríguez',
            'Ana Martínez', 'Luis Fernández', 'Laura Sánchez',
            'Pedro Ramírez', 'Carmen López', 'Diego Torres',
            'Sofía Morales'
        ]
        
        responsables = []
        for i, nombre in enumerate(nombres):
            responsable = ResponsableCustodio.objects.create(
                nombre=nombre,
                cargo=random.choice(cargos),
                departamento=random.choice(departamentos),
                email=f'{nombre.lower().replace(" ", ".")}@utpl.edu.ec',
                telefono=f'07{random.randint(2000000, 9999999)}',
                activo=True
            )
            responsables.append(responsable)
        
        return responsables

    def crear_siniestros(self, polizas, tipos_siniestro, usuario):
        hoy = timezone.now()
        siniestros = []
        estados = ['registrado', 'documentacion_pendiente', 'enviado_aseguradora', 'en_evaluacion', 'aprobado', 'cerrado']
        
        # Crear responsables primero
        responsables = self.crear_responsables()
        
        bienes = [
            ('Laptop HP ProBook', 'HP', 'ProBook 450 G8', 'SN123456'),
            ('Vehículo Toyota Corolla', 'Toyota', 'Corolla 2022', 'VIN987654'),
            ('Servidor Dell PowerEdge', 'Dell', 'PowerEdge R740', 'SRV456789'),
            ('Impresora Epson', 'Epson', 'L3150', 'EP123456'),
            ('Monitor LG 27"', 'LG', '27UK850', 'MON789012'),
            ('Edificio Administrativo', 'N/A', 'Bloque A', 'EDI001'),
        ]
        
        for i, poliza in enumerate(polizas[:8]):
            bien = random.choice(bienes)
            dias_atras = random.randint(5, 90)
            fecha_siniestro = hoy - timedelta(days=dias_atras)
            
            # Asegurar que la fecha del siniestro esté dentro de la vigencia de la póliza
            if fecha_siniestro.date() < poliza.fecha_inicio:
                fecha_siniestro = timezone.make_aware(
                    timezone.datetime.combine(poliza.fecha_inicio + timedelta(days=5), timezone.datetime.min.time())
                )
            
            estado = random.choice(estados)
            responsable = random.choice(responsables)
            
            siniestro = Siniestro.objects.create(
                poliza=poliza,
                numero_siniestro=f'SIN-{2024}-{7000 + i}',
                tipo_siniestro=random.choice(tipos_siniestro),
                fecha_siniestro=fecha_siniestro,
                bien_nombre=bien[0],
                bien_marca=bien[1],
                bien_modelo=bien[2],
                bien_serie=bien[3],
                responsable_custodio=responsable,
                ubicacion=f'Edificio {chr(65 + i % 5)}, Piso {(i % 3) + 1}',
                causa=f'Causa del siniestro número {i+1}. Descripción detallada del evento.',
                descripcion_detallada=f'Descripción completa del siniestro {i+1}. Se reportó el evento y se procedió con el protocolo establecido.',
                monto_estimado=Decimal(random.randint(1000, 50000)),
                estado=estado,
                creado_por=usuario
            )
            
            # Agregar datos adicionales según el estado
            if estado in ['enviado_aseguradora', 'en_evaluacion', 'aprobado', 'cerrado']:
                siniestro.fecha_envio_aseguradora = (fecha_siniestro + timedelta(days=random.randint(3, 10))).date()
                siniestro.save()
            
            if estado in ['aprobado', 'cerrado']:
                siniestro.fecha_respuesta_aseguradora = siniestro.fecha_envio_aseguradora + timedelta(days=random.randint(5, 15))
                siniestro.monto_indemnizado = siniestro.monto_estimado * Decimal(str(random.uniform(0.7, 1.0)))
                siniestro.save()
            
            if estado == 'cerrado':
                siniestro.fecha_liquidacion = siniestro.fecha_respuesta_aseguradora + timedelta(days=random.randint(3, 10))
                siniestro.save()
            
            siniestros.append(siniestro)
        
        return siniestros

    def actualizar_estados(self, polizas, facturas):
        for poliza in polizas:
            poliza.actualizar_estado()
            poliza.save()
        
        for factura in facturas:
            factura.actualizar_estado()

