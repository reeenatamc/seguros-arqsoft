"""
Comando para poblar la base de datos con datos de prueba.
Uso: python manage.py poblar_datos_prueba
Opciones:
  --limpiar: Limpiar datos existentes antes de poblar
  --extendido: Crear dataset extendido con más registros históricos
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random
import calendar

from app.models import (
    ConfiguracionSistema, CompaniaAseguradora, CorredorSeguros, 
    TipoPoliza, ResponsableCustodio, Poliza, Factura, Pago, TipoSiniestro, Siniestro, Alerta,
    BienAsegurado, SubgrupoRamo, Quote, QuoteOption, PolicyRenewal, PaymentApproval, CalendarEvent
)


class Command(BaseCommand):
    help = 'Poblar la base de datos con datos de prueba'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpiar datos existentes antes de poblar',
        )
        parser.add_argument(
            '--extendido',
            action='store_true',
            help='Crear dataset extendido con más registros históricos (2 años de datos)',
        )

    def handle(self, *args, **options):
        self.extendido = options.get('extendido', False)
        modo = 'EXTENDIDO' if self.extendido else 'BÁSICO'
        
        self.stdout.write(self.style.NOTICE(f'🚀 Iniciando población de datos de prueba (Modo {modo})...'))
        
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
        
        # 5. Tipos de siniestro (ampliado)
        self.stdout.write('  ⚠️ Creando tipos de siniestro...')
        tipos_siniestro = self.crear_tipos_siniestro()
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(tipos_siniestro)} tipos de siniestro creados'))
        
        # 6. Responsables/Custodios
        self.stdout.write('  👤 Creando responsables/custodios...')
        responsables = self.crear_responsables()
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(responsables)} responsables creados'))
        
        # 7. Pólizas
        self.stdout.write('  📄 Creando pólizas...')
        polizas = self.crear_polizas(companias, corredores, tipos_poliza, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(polizas)} pólizas creadas'))
        
        # 8. Facturas (distribuidas en el tiempo)
        self.stdout.write('  💰 Creando facturas...')
        facturas = self.crear_facturas(polizas, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(facturas)} facturas creadas'))
        
        # 9. Pagos
        self.stdout.write('  💳 Creando pagos...')
        pagos = self.crear_pagos(facturas, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(pagos)} pagos creados'))
        
        # 10. Siniestros (variedad de tipos y estados)
        self.stdout.write('  🚗 Creando siniestros...')
        siniestros = self.crear_siniestros(polizas, tipos_siniestro, responsables, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(siniestros)} siniestros creados'))
        
        # 11. Alertas
        self.stdout.write('  🔔 Creando alertas...')
        alertas = self.crear_alertas(polizas, facturas, siniestros)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(alertas)} alertas creadas'))
        
        # 12. Bienes Asegurados
        self.stdout.write('  📦 Creando bienes asegurados...')
        bienes = self.create_insured_assets(polizas, responsables, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(bienes)} bienes asegurados creados'))
        
        # 13. Cotizaciones
        self.stdout.write('  📝 Creando cotizaciones...')
        cotizaciones = self.create_quotes(companias, corredores, tipos_poliza, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(cotizaciones)} cotizaciones creadas'))
        
        # 14. Renovaciones
        self.stdout.write('  🔄 Creando renovaciones de pólizas...')
        renovaciones = self.create_renewals(polizas, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(renovaciones)} renovaciones creadas'))
        
        # 15. Aprobaciones de Pago
        self.stdout.write('  ✅ Creando aprobaciones de pago...')
        aprobaciones = self.create_payment_approvals(pagos)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(aprobaciones)} aprobaciones creadas'))
        
        # 16. Eventos del Calendario
        self.stdout.write('  📅 Creando eventos de calendario...')
        eventos = self.create_calendar_events(polizas, facturas, admin_user)
        self.stdout.write(self.style.SUCCESS(f'     ✓ {len(eventos)} eventos creados'))
        
        # 17. Actualizar estados
        self.stdout.write('  🔄 Actualizando estados...')
        self.actualizar_estados(polizas, facturas)
        self.stdout.write(self.style.SUCCESS('     ✓ Estados actualizados'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✅ ¡Datos de prueba creados exitosamente! (Modo {modo})'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(f'   Usuario admin: admin / admin123')
        self.stdout.write(f'   Compañías aseguradoras: {len(companias)}')
        self.stdout.write(f'   Corredores: {len(corredores)}')
        self.stdout.write(f'   Tipos de póliza: {len(tipos_poliza)}')
        self.stdout.write(f'   Tipos de siniestro: {len(tipos_siniestro)}')
        self.stdout.write(f'   Responsables: {len(responsables)}')
        self.stdout.write(f'   Pólizas: {len(polizas)}')
        self.stdout.write(f'   Facturas: {len(facturas)}')
        self.stdout.write(f'   Pagos: {len(pagos)}')
        self.stdout.write(f'   Siniestros: {len(siniestros)}')
        self.stdout.write(f'   Alertas: {len(alertas)}')
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
        # Lista ampliada de tipos de siniestro para cubrir todos los casos posibles
        tipos_data = [
            {'nombre': 'Daño accidental', 'descripcion': 'Daños causados por accidentes no intencionales'},
            {'nombre': 'Robo', 'descripcion': 'Sustracción con violencia o intimidación'},
            {'nombre': 'Hurto', 'descripcion': 'Sustracción sin violencia'},
            {'nombre': 'Incendio', 'descripcion': 'Daños causados por fuego'},
            {'nombre': 'Inundación', 'descripcion': 'Daños por agua o desbordamientos'},
            {'nombre': 'Vandalismo', 'descripcion': 'Daños intencionales por terceros'},
            {'nombre': 'Colisión vehicular', 'descripcion': 'Accidentes de tránsito con otros vehículos'},
            {'nombre': 'Volcamiento', 'descripcion': 'Vuelco de vehículo'},
            {'nombre': 'Choque contra objeto fijo', 'descripcion': 'Impacto contra postes, muros, etc.'},
            {'nombre': 'Fenómeno natural', 'descripcion': 'Terremotos, tormentas, rayos, etc.'},
            {'nombre': 'Cortocircuito', 'descripcion': 'Daños eléctricos y cortocircuitos'},
            {'nombre': 'Explosión', 'descripcion': 'Daños por explosión'},
            {'nombre': 'Falla mecánica', 'descripcion': 'Daños por fallas mecánicas cubiertas'},
            {'nombre': 'Cristales rotos', 'descripcion': 'Rotura de vidrios y cristales'},
            {'nombre': 'Responsabilidad civil', 'descripcion': 'Daños causados a terceros'},
            {'nombre': 'Accidente personal', 'descripcion': 'Lesiones personales cubiertas'},
        ]
        
        tipos = []
        for data in tipos_data:
            tipo, _ = TipoSiniestro.objects.get_or_create(
                nombre=data['nombre'],
                defaults={
                    'descripcion': data.get('descripcion', ''),
                    'activo': True
                }
            )
            tipos.append(tipo)
        return tipos

    def crear_polizas(self, companias, corredores, tipos, usuario):
        hoy = timezone.now().date()
        current_year = hoy.year
        polizas = []
        
        # Usar timestamp para generar números únicos y evitar colisiones
        import time
        base_id = int(time.time()) % 100000  # Últimos 5 dígitos del timestamp
        contador = base_id
        
        # Determinar cantidad según modo
        if self.extendido:
            num_vigentes = 25
            num_por_vencer = 10
            num_vencidas = 15
            num_historicas_por_anio = 20  # Pólizas históricas por año
            anios_historicos = 2
        else:
            num_vigentes = 8
            num_por_vencer = 4
            num_vencidas = 3
            num_historicas_por_anio = 0
            anios_historicos = 0
        
        # Pólizas vigentes (estado actual: vigente)
        for i in range(num_vigentes):
            dias_inicio = random.randint(-180, -30)
            dias_fin = random.randint(60, 365)
            
            poliza = Poliza.objects.create(
                numero_poliza=f'POL-{current_year}-{contador}',
                compania_aseguradora=random.choice(companias),
                corredor_seguros=random.choice(corredores),
                tipo_poliza=random.choice(tipos),
                suma_asegurada=Decimal(random.randint(10000, 500000)),
                coberturas=f'Cobertura completa para póliza {contador}. Incluye daños materiales, responsabilidad civil y asistencia.',
                fecha_inicio=hoy + timedelta(days=dias_inicio),
                fecha_fin=hoy + timedelta(days=dias_fin),
                creado_por=usuario,
                observaciones=f'Póliza vigente #{i+1}'
            )
            polizas.append(poliza)
            contador += 1
        
        # Pólizas por vencer (próximos 30 días)
        for i in range(num_por_vencer):
            dias_fin = random.randint(1, 30)
            
            poliza = Poliza.objects.create(
                numero_poliza=f'POL-{current_year}-{contador}',
                compania_aseguradora=random.choice(companias),
                corredor_seguros=random.choice(corredores),
                tipo_poliza=random.choice(tipos),
                suma_asegurada=Decimal(random.randint(20000, 300000)),
                coberturas='Cobertura estándar con límites definidos.',
                fecha_inicio=hoy - timedelta(days=335),
                fecha_fin=hoy + timedelta(days=dias_fin),
                creado_por=usuario,
                observaciones=f'Póliza por vencer #{i+1}'
            )
            polizas.append(poliza)
            contador += 1
        
        # Pólizas vencidas (recientemente)
        for i in range(num_vencidas):
            dias_fin = random.randint(-90, -1)
            
            poliza = Poliza.objects.create(
                numero_poliza=f'POL-{current_year}-{contador}',
                compania_aseguradora=random.choice(companias),
                corredor_seguros=random.choice(corredores),
                tipo_poliza=random.choice(tipos),
                suma_asegurada=Decimal(random.randint(15000, 200000)),
                coberturas='Cobertura básica.',
                fecha_inicio=hoy + timedelta(days=dias_fin - 365),
                fecha_fin=hoy + timedelta(days=dias_fin),
                creado_por=usuario,
                observaciones=f'Póliza vencida #{i+1}'
            )
            polizas.append(poliza)
            contador += 1
        
        # Pólizas históricas (años anteriores) - solo en modo extendido
        for anio_offset in range(1, anios_historicos + 1):
            anio = current_year - anio_offset
            for i in range(num_historicas_por_anio):
                # Distribuir las fechas a lo largo del año
                mes_inicio = random.randint(1, 12)
                dia_inicio = random.randint(1, 28)
                fecha_inicio = date(anio, mes_inicio, dia_inicio)
                fecha_fin = fecha_inicio + timedelta(days=365)
                
                # Algunos con estado cancelado
                estado = 'cancelada' if random.random() < 0.1 else 'vencida'
                
                poliza = Poliza.objects.create(
                    numero_poliza=f'POL-{anio}-{contador}',
                    compania_aseguradora=random.choice(companias),
                    corredor_seguros=random.choice(corredores),
                    tipo_poliza=random.choice(tipos),
                    suma_asegurada=Decimal(random.randint(10000, 400000)),
                    coberturas=f'Cobertura histórica del año {anio}.',
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    estado=estado,
                    creado_por=usuario,
                    observaciones=f'Póliza histórica {anio} #{i+1}'
                )
                polizas.append(poliza)
                contador += 1
        
        return polizas

    def crear_facturas(self, polizas, usuario):
        hoy = timezone.now().date()
        current_year = hoy.year
        facturas = []
        
        # Usar timestamp para generar números únicos
        import time
        base_id = int(time.time()) % 100000
        contador = base_id + 50000  # Offset para diferenciar de pólizas
        
        # Generar facturas para la mayoría de las pólizas
        for poliza in polizas:
            # Calcular cuántas facturas generar según la duración de la póliza
            duracion_dias = (poliza.fecha_fin - poliza.fecha_inicio).days
            
            # Determinar número de facturas según duración
            if duracion_dias > 300:
                num_facturas = random.randint(2, 4) if self.extendido else random.randint(1, 2)
            else:
                num_facturas = 1
            
            for j in range(num_facturas):
                # Distribuir fechas de emisión a lo largo de la vigencia de la póliza
                rango_emision = duracion_dias // num_facturas
                offset_base = j * rango_emision
                dias_desde_inicio = offset_base + random.randint(0, max(1, rango_emision - 30))
                
                fecha_emision = poliza.fecha_inicio + timedelta(days=dias_desde_inicio)
                
                # No crear facturas con fecha futura
                if fecha_emision > hoy:
                    continue
                
                fecha_vencimiento = fecha_emision + timedelta(days=30)
                anio_factura = fecha_emision.year
                
                # Variar los estados de las facturas
                if fecha_vencimiento < hoy:
                    # Factura vencida - puede estar pagada, vencida o parcialmente pagada
                    estado_base = random.choice(['pagada', 'pagada', 'vencida', 'parcialmente_pagada'])
                else:
                    # Factura vigente
                    estado_base = random.choice(['pendiente', 'pagada', 'parcialmente_pagada'])
                
                subtotal = Decimal(random.randint(500, 8000))
                
                factura = Factura.objects.create(
                    poliza=poliza,
                    numero_factura=f'FAC-{anio_factura}-{contador}',
                    fecha_emision=fecha_emision,
                    fecha_vencimiento=fecha_vencimiento,
                    subtotal=subtotal,
                    iva=Decimal('0.00'),  # Se calcula automáticamente
                    creado_por=usuario
                )
                facturas.append(factura)
                contador += 1
        
        # Facturas adicionales distribuidas mensualmente (modo extendido)
        if self.extendido:
            for anio_offset in range(2):
                anio = current_year - anio_offset
                for mes in range(1, 13):
                    # Saltar meses futuros
                    if anio == current_year and mes > hoy.month:
                        continue
                    
                    # Crear 3-8 facturas por mes
                    num_facturas_mes = random.randint(3, 8)
                    for _ in range(num_facturas_mes):
                        dia = random.randint(1, 28)
                        fecha_emision = date(anio, mes, dia)
                        
                        # Seleccionar una póliza válida para esa fecha
                        polizas_validas = [p for p in polizas if p.fecha_inicio <= fecha_emision <= p.fecha_fin]
                        if not polizas_validas:
                            continue
                        
                        poliza = random.choice(polizas_validas)
                        fecha_vencimiento = fecha_emision + timedelta(days=30)
                        
                        subtotal = Decimal(random.randint(800, 12000))
                        
                        factura = Factura.objects.create(
                            poliza=poliza,
                            numero_factura=f'FAC-{anio}-{contador}',
                            fecha_emision=fecha_emision,
                            fecha_vencimiento=fecha_vencimiento,
                            subtotal=subtotal,
                            iva=Decimal('0.00'),
                            creado_por=usuario
                        )
                        facturas.append(factura)
                        contador += 1
        
        return facturas

    def crear_pagos(self, facturas, usuario):
        hoy = timezone.now().date()
        pagos = []
        formas_pago = ['transferencia', 'cheque', 'efectivo', 'tarjeta']
        estados_pago = ['aprobado', 'aprobado', 'aprobado', 'pendiente', 'rechazado']
        
        for factura in facturas:
            # Probabilidad de tener pago según antigüedad
            dias_desde_emision = (hoy - factura.fecha_emision).days
            prob_pago = min(0.9, 0.3 + (dias_desde_emision / 100))
            
            if random.random() > prob_pago:
                continue  # Sin pago para esta factura
            
            # Determinar tipo de pago
            tipo_pago = random.choices(
                ['completo', 'parcial', 'multiple'],
                weights=[0.6, 0.25, 0.15]
            )[0]
            
            if tipo_pago == 'completo':
                # Pago completo
                fecha_pago = factura.fecha_emision + timedelta(days=random.randint(1, 25))
                if fecha_pago > hoy:
                    fecha_pago = hoy - timedelta(days=random.randint(1, 5))
                
            pago = Pago.objects.create(
                factura=factura,
                    fecha_pago=fecha_pago,
                monto=factura.monto_total,
                forma_pago=random.choice(formas_pago),
                referencia=f'REF-{random.randint(10000, 99999)}',
                    estado=random.choice(estados_pago),
                registrado_por=usuario
            )
            pagos.append(pago)
        
            elif tipo_pago == 'parcial':
                # Pago parcial (30-70% del monto)
                porcentaje = Decimal(str(random.uniform(0.3, 0.7)))
                monto_parcial = (factura.monto_total * porcentaje).quantize(Decimal('0.01'))
                
                fecha_pago = factura.fecha_emision + timedelta(days=random.randint(5, 20))
                if fecha_pago > hoy:
                    fecha_pago = hoy - timedelta(days=random.randint(1, 5))
                
            pago = Pago.objects.create(
                factura=factura,
                    fecha_pago=fecha_pago,
                monto=monto_parcial,
                forma_pago=random.choice(formas_pago),
                referencia=f'REF-{random.randint(10000, 99999)}',
                    estado='aprobado',
                    registrado_por=usuario
                )
                pagos.append(pago)
                
            else:
                # Múltiples pagos
                num_pagos = random.randint(2, 3)
                monto_por_pago = (factura.monto_total / num_pagos).quantize(Decimal('0.01'))
                
                for k in range(num_pagos):
                    dias_offset = (k + 1) * random.randint(7, 15)
                    fecha_pago = factura.fecha_emision + timedelta(days=dias_offset)
                    
                    if fecha_pago > hoy:
                        break  # No crear pagos futuros
                    
                    pago = Pago.objects.create(
                        factura=factura,
                        fecha_pago=fecha_pago,
                        monto=monto_por_pago,
                        forma_pago=random.choice(formas_pago),
                        referencia=f'REF-{random.randint(10000, 99999)}-{k+1}',
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

    def crear_siniestros(self, polizas, tipos_siniestro, responsables, usuario):
        hoy = timezone.now()
        current_year = hoy.year
        siniestros = []
        
        # Todos los estados posibles de siniestros
        estados = [
            'registrado', 
            'documentacion_pendiente', 
            'enviado_aseguradora', 
            'en_evaluacion', 
            'aprobado', 
            'rechazado',
            'cerrado'
        ]
        
        # Pesos para distribución realista de estados
        pesos_estados = [0.1, 0.15, 0.1, 0.15, 0.15, 0.05, 0.3]
        
        # Lista ampliada de bienes afectados
        bienes = [
            ('Laptop HP ProBook', 'HP', 'ProBook 450 G8', 'SN'),
            ('Laptop Dell Latitude', 'Dell', 'Latitude 5520', 'SN'),
            ('MacBook Pro 14"', 'Apple', 'MacBook Pro M2', 'SN'),
            ('Vehículo Toyota Corolla', 'Toyota', 'Corolla 2022', 'VIN'),
            ('Vehículo Chevrolet Aveo', 'Chevrolet', 'Aveo 2021', 'VIN'),
            ('Camioneta Ford Ranger', 'Ford', 'Ranger XLT 2023', 'VIN'),
            ('Motocicleta Yamaha', 'Yamaha', 'MT-07', 'VIN'),
            ('Servidor Dell PowerEdge', 'Dell', 'PowerEdge R740', 'SRV'),
            ('Servidor HP ProLiant', 'HP', 'ProLiant DL380', 'SRV'),
            ('Impresora Epson', 'Epson', 'L3150', 'IMP'),
            ('Impresora HP LaserJet', 'HP', 'LaserJet Pro M404', 'IMP'),
            ('Monitor LG 27"', 'LG', '27UK850', 'MON'),
            ('Monitor Dell 24"', 'Dell', 'P2419H', 'MON'),
            ('Proyector Epson', 'Epson', 'PowerLite X49', 'PRY'),
            ('Aire Acondicionado LG', 'LG', 'Inverter 24000 BTU', 'AC'),
            ('UPS APC', 'APC', 'Smart-UPS 3000VA', 'UPS'),
            ('Switch Cisco', 'Cisco', 'Catalyst 2960', 'NET'),
            ('Router Mikrotik', 'Mikrotik', 'CCR1036', 'NET'),
            ('Edificio Administrativo', 'N/A', 'Bloque A', 'EDI'),
            ('Bodega Central', 'N/A', 'Galpón 1', 'EDI'),
            ('Mobiliario Oficina', 'Varios', 'Set ejecutivo', 'MOB'),
            ('Equipo de Laboratorio', 'Varios', 'Microscopio digital', 'LAB'),
        ]
        
        ubicaciones = [
            'Edificio A, Piso 1', 'Edificio A, Piso 2', 'Edificio A, Piso 3',
            'Edificio B, Planta Baja', 'Edificio B, Piso 1', 'Edificio B, Piso 2',
            'Edificio C, Oficina 101', 'Edificio C, Oficina 205',
            'Bodega Central', 'Parqueadero Norte', 'Parqueadero Sur',
            'Laboratorio 1', 'Laboratorio 2', 'Sala de Servidores',
            'Recepción Principal', 'Área de Mantenimiento',
        ]
        
        causas = [
            'El bien sufrió daños durante su operación normal.',
            'Se reportó intento de sustracción del bien.',
            'Daños causados por cortocircuito eléctrico.',
            'Afectación por condiciones climáticas adversas.',
            'Daño por manipulación inadecuada.',
            'Colisión durante traslado del bien.',
            'Vandalismo reportado por personal de seguridad.',
            'Falla estructural detectada durante inspección.',
            'Daños causados por inundación en el área.',
            'Incendio parcial en las instalaciones.',
        ]
        
        # Usar timestamp para generar números únicos
        import time
        base_id = int(time.time()) % 100000
        contador = base_id + 70000  # Offset para diferenciar de pólizas y facturas
        
        # Determinar cantidad de siniestros según modo
        if self.extendido:
            # Crear siniestros distribuidos en 2 años
            # Asegurar que cada tipo de siniestro tenga al menos 2-5 registros
            for tipo_siniestro in tipos_siniestro:
                num_siniestros_tipo = random.randint(3, 8)
                
                for _ in range(num_siniestros_tipo):
                    # Seleccionar póliza válida
                    poliza = random.choice(polizas)
                    
                    # Calcular fecha del siniestro dentro de la vigencia
                    dias_vigencia = (poliza.fecha_fin - poliza.fecha_inicio).days
                    if dias_vigencia <= 0:
                        continue
                    
                    dias_offset = random.randint(1, max(1, dias_vigencia - 1))
                    fecha_siniestro_date = poliza.fecha_inicio + timedelta(days=dias_offset)
                    
                    # No crear siniestros futuros
                    if fecha_siniestro_date > hoy.date():
                        fecha_siniestro_date = hoy.date() - timedelta(days=random.randint(1, 30))
                    
                    fecha_siniestro = timezone.make_aware(
                        timezone.datetime.combine(fecha_siniestro_date, timezone.datetime.min.time())
                    ) + timedelta(hours=random.randint(8, 18), minutes=random.randint(0, 59))
                    
                    bien = random.choice(bienes)
                    estado = random.choices(estados, weights=pesos_estados)[0]
                    
                    siniestro = self._crear_siniestro(
                        poliza, tipo_siniestro, fecha_siniestro, bien, estado,
                        responsables, ubicaciones, causas, contador, usuario
                    )
                    siniestros.append(siniestro)
                    contador += 1
            
            # Agregar siniestros adicionales para tener buena distribución mensual
            for anio_offset in range(2):
                anio = current_year - anio_offset
                for mes in range(1, 13):
                    # Saltar meses futuros
                    if anio == current_year and mes > hoy.month:
                        continue
                    
                    # 3-10 siniestros por mes
                    num_siniestros_mes = random.randint(3, 10)
                    
                    for _ in range(num_siniestros_mes):
                        dia = random.randint(1, 28)
                        fecha_siniestro_date = date(anio, mes, dia)
                        
                        # Buscar póliza válida
                        polizas_validas = [p for p in polizas if p.fecha_inicio <= fecha_siniestro_date <= p.fecha_fin]
                        if not polizas_validas:
                            continue
                        
                        poliza = random.choice(polizas_validas)
                        
                        fecha_siniestro = timezone.make_aware(
                            timezone.datetime.combine(fecha_siniestro_date, timezone.datetime.min.time())
                        ) + timedelta(hours=random.randint(8, 18), minutes=random.randint(0, 59))
                        
                        bien = random.choice(bienes)
                        tipo_siniestro = random.choice(tipos_siniestro)
                        estado = random.choices(estados, weights=pesos_estados)[0]
                        
                        siniestro = self._crear_siniestro(
                            poliza, tipo_siniestro, fecha_siniestro, bien, estado,
                            responsables, ubicaciones, causas, contador, usuario
                        )
                        siniestros.append(siniestro)
                        contador += 1
        else:
            # Modo básico: siniestros simples
            for i, poliza in enumerate(polizas[:12]):
            bien = random.choice(bienes)
            dias_atras = random.randint(5, 90)
            fecha_siniestro = hoy - timedelta(days=dias_atras)
            
            if fecha_siniestro.date() < poliza.fecha_inicio:
                fecha_siniestro = timezone.make_aware(
                    timezone.datetime.combine(poliza.fecha_inicio + timedelta(days=5), timezone.datetime.min.time())
                )
            
                estado = random.choices(estados, weights=pesos_estados)[0]
                tipo_siniestro = random.choice(tipos_siniestro)
                
                siniestro = self._crear_siniestro(
                    poliza, tipo_siniestro, fecha_siniestro, bien, estado,
                    responsables, ubicaciones, causas, contador, usuario
                )
                siniestros.append(siniestro)
                contador += 1
        
        return siniestros
    
    def _crear_siniestro(self, poliza, tipo_siniestro, fecha_siniestro, bien, estado, 
                         responsables, ubicaciones, causas, contador, usuario):
        """Helper para crear un siniestro con todos sus datos"""
        anio = fecha_siniestro.year if hasattr(fecha_siniestro, 'year') else fecha_siniestro.date().year
        
        responsable = random.choice(responsables) if responsables else None
            
            siniestro = Siniestro.objects.create(
                poliza=poliza,
            numero_siniestro=f'SIN-{anio}-{contador}',
            tipo_siniestro=tipo_siniestro,
                fecha_siniestro=fecha_siniestro,
                bien_nombre=bien[0],
                bien_marca=bien[1],
                bien_modelo=bien[2],
            bien_serie=f'{bien[3]}{random.randint(100000, 999999)}',
                responsable_custodio=responsable,
            ubicacion=random.choice(ubicaciones),
            causa=random.choice(causas),
            descripcion_detallada=f'Reporte detallado del siniestro. {random.choice(causas)} Se procedió según protocolo establecido.',
            monto_estimado=Decimal(random.randint(500, 80000)),
                estado=estado,
                creado_por=usuario
            )
            
            # Agregar datos adicionales según el estado
        fecha_base = fecha_siniestro.date() if hasattr(fecha_siniestro, 'date') else fecha_siniestro
        
        if estado in ['enviado_aseguradora', 'en_evaluacion', 'aprobado', 'rechazado', 'cerrado']:
            siniestro.fecha_envio_aseguradora = fecha_base + timedelta(days=random.randint(3, 10))
                siniestro.save()
            
            if estado in ['aprobado', 'cerrado']:
            siniestro.fecha_respuesta_aseguradora = siniestro.fecha_envio_aseguradora + timedelta(days=random.randint(5, 20))
            siniestro.monto_indemnizado = siniestro.monto_estimado * Decimal(str(random.uniform(0.6, 1.0)))
            siniestro.save()
        
        if estado == 'rechazado':
                siniestro.fecha_respuesta_aseguradora = siniestro.fecha_envio_aseguradora + timedelta(days=random.randint(5, 15))
            siniestro.monto_indemnizado = Decimal('0')
            siniestro.observaciones = 'Siniestro rechazado por la aseguradora. ' + random.choice([
                'No cumple con las condiciones de la póliza.',
                'Documentación insuficiente.',
                'Evento no cubierto según exclusiones.',
                'Plazo de reporte excedido.',
            ])
                siniestro.save()
            
            if estado == 'cerrado':
            siniestro.fecha_liquidacion = siniestro.fecha_respuesta_aseguradora + timedelta(days=random.randint(3, 15))
                siniestro.save()
            
        return siniestro

    def crear_alertas(self, polizas, facturas, siniestros):
        """Crea alertas de prueba con diferentes tipos y estados"""
        alertas = []
        # Tipos válidos según el modelo: vencimiento_poliza, pago_pendiente, documentacion_pendiente, 
        # respuesta_aseguradora, pronto_pago
        tipos_alerta_validos = ['vencimiento_poliza', 'pago_pendiente', 'documentacion_pendiente', 'respuesta_aseguradora']
        # Estados válidos: pendiente, enviada, leida, atendida
        estados_alerta = ['pendiente', 'enviada', 'leida', 'atendida']
        
        hoy = timezone.now().date()
        ahora = timezone.now()
        
        # Alertas de pólizas por vencer
        for poliza in polizas:
            dias_para_vencer = (poliza.fecha_fin - hoy).days
            if 0 < dias_para_vencer <= 30:
                urgencia = 'URGENTE: ' if dias_para_vencer <= 7 else ''
                alerta, created = Alerta.objects.get_or_create(
                    tipo_alerta='vencimiento_poliza',
                    poliza=poliza,
                    defaults={
                        'titulo': f'{urgencia}Póliza por vencer - {poliza.numero_poliza}',
                        'mensaje': f'La póliza {poliza.numero_poliza} vence en {dias_para_vencer} días ({poliza.fecha_fin}).',
                        'estado': random.choice(['pendiente', 'enviada']),
                    }
                )
                if created:
                    alertas.append(alerta)
        
        # Alertas de facturas vencidas (pago pendiente)
        for factura in facturas:
            if factura.fecha_vencimiento < hoy and factura.estado in ['pendiente', 'vencida']:
                dias_vencida = (hoy - factura.fecha_vencimiento).days
                urgencia = 'CRÍTICO: ' if dias_vencida > 30 else 'URGENTE: ' if dias_vencida > 15 else ''
                alerta, created = Alerta.objects.get_or_create(
                    tipo_alerta='pago_pendiente',
                    factura=factura,
                    defaults={
                        'titulo': f'{urgencia}Pago pendiente - {factura.numero_factura}',
                        'mensaje': f'La factura {factura.numero_factura} está vencida desde hace {dias_vencida} días.',
                        'estado': random.choice(['pendiente', 'enviada', 'leida']),
                    }
                )
                if created:
                    alertas.append(alerta)
        
        # Alertas de siniestros pendientes
        for siniestro in siniestros:
            if siniestro.estado == 'documentacion_pendiente':
                dias_pendiente = (hoy - siniestro.fecha_registro.date()).days
                if dias_pendiente > 5:
                    alerta, created = Alerta.objects.get_or_create(
                        tipo_alerta='documentacion_pendiente',
                        siniestro=siniestro,
                        defaults={
                            'titulo': f'Documentación pendiente - {siniestro.numero_siniestro}',
                            'mensaje': f'El siniestro {siniestro.numero_siniestro} tiene documentación pendiente desde hace {dias_pendiente} días.',
                            'estado': random.choice(['pendiente', 'enviada']),
                        }
                    )
                    if created:
                        alertas.append(alerta)
            
            elif siniestro.estado == 'enviado_aseguradora':
                dias_esperando = (hoy - siniestro.fecha_envio_aseguradora).days if siniestro.fecha_envio_aseguradora else 0
                if dias_esperando > 7:
                    alerta, created = Alerta.objects.get_or_create(
                        tipo_alerta='respuesta_aseguradora',
                        siniestro=siniestro,
                        defaults={
                            'titulo': f'Esperando respuesta - {siniestro.numero_siniestro}',
                            'mensaje': f'El siniestro {siniestro.numero_siniestro} está esperando respuesta de la aseguradora desde hace {dias_esperando} días.',
                            'estado': random.choice(['pendiente', 'enviada']),
                        }
                    )
                    if created:
                        alertas.append(alerta)
        
        # Algunas alertas históricas atendidas (modo extendido)
        if self.extendido:
            for i in range(20):
                dias_atras = random.randint(30, 180)
                fecha_creacion = ahora - timedelta(days=dias_atras)
                fecha_envio = fecha_creacion + timedelta(hours=random.randint(1, 24))
                fecha_lectura = fecha_envio + timedelta(days=random.randint(1, 3))
                
                alerta = Alerta.objects.create(
                    tipo_alerta=random.choice(tipos_alerta_validos),
                    titulo=f'Alerta histórica #{i+1}',
                    mensaje=f'Alerta histórica #{i+1} - Atendida automáticamente.',
                    estado='atendida',
                )
                # Actualizar fechas después de crear (para evitar auto_now_add)
                Alerta.objects.filter(pk=alerta.pk).update(
                    fecha_creacion=fecha_creacion,
                    fecha_envio=fecha_envio,
                    fecha_lectura=fecha_lectura,
                )
                alertas.append(alerta)
        
        return alertas

    def actualizar_estados(self, polizas, facturas):
        for poliza in polizas:
            poliza.actualizar_estado()
            poliza.save()
        
        for factura in facturas:
            factura.actualizar_estado()

    # ==================== NUEVOS MÓDULOS ====================
    
    def create_insured_assets(self, polizas, responsables, usuario):
        """Crea bienes asegurados de prueba"""
        assets = []
        hoy = timezone.now().date()
        
        # Usar timestamp para IDs únicos
        import time
        base_id = int(time.time()) % 100000
        
        # Categorías de bienes
        categories = [
            'Equipos de Cómputo',
            'Mobiliario',
            'Vehículos',
            'Maquinaria',
            'Infraestructura',
            'Equipos de Comunicación',
            'Equipos Médicos',
            'Equipos de Laboratorio',
        ]
        
        # Bienes de ejemplo
        sample_assets = [
            {'name': 'Laptop HP ProBook 450', 'brand': 'HP', 'model': 'ProBook 450 G8', 'category': 'Equipos de Cómputo', 'value': 1200},
            {'name': 'MacBook Pro 14"', 'brand': 'Apple', 'model': 'MacBook Pro M3', 'category': 'Equipos de Cómputo', 'value': 2500},
            {'name': 'Servidor Dell PowerEdge', 'brand': 'Dell', 'model': 'R740', 'category': 'Equipos de Cómputo', 'value': 8500},
            {'name': 'Impresora Multifunción', 'brand': 'Epson', 'model': 'L15160', 'category': 'Equipos de Cómputo', 'value': 650},
            {'name': 'Toyota Corolla 2023', 'brand': 'Toyota', 'model': 'Corolla XEI', 'category': 'Vehículos', 'value': 28000},
            {'name': 'Chevrolet Tracker 2024', 'brand': 'Chevrolet', 'model': 'Tracker Premier', 'category': 'Vehículos', 'value': 32000},
            {'name': 'Montacargas Yale', 'brand': 'Yale', 'model': 'GLP35VX', 'category': 'Maquinaria', 'value': 45000},
            {'name': 'Generador Eléctrico', 'brand': 'Caterpillar', 'model': 'C9.3', 'category': 'Maquinaria', 'value': 55000},
            {'name': 'Escritorio Ejecutivo', 'brand': 'Steelcase', 'model': 'Flex', 'category': 'Mobiliario', 'value': 850},
            {'name': 'Silla Ergonómica', 'brand': 'Herman Miller', 'model': 'Aeron', 'category': 'Mobiliario', 'value': 1200},
            {'name': 'Router Cisco', 'brand': 'Cisco', 'model': 'ISR 4331', 'category': 'Equipos de Comunicación', 'value': 3500},
            {'name': 'Switch Cisco', 'brand': 'Cisco', 'model': 'Catalyst 9200', 'category': 'Equipos de Comunicación', 'value': 4200},
            {'name': 'Microscopio Digital', 'brand': 'Olympus', 'model': 'BX53', 'category': 'Equipos de Laboratorio', 'value': 15000},
            {'name': 'Centrífuga', 'brand': 'Thermo Fisher', 'model': 'Sorvall X4R', 'category': 'Equipos de Laboratorio', 'value': 12000},
            {'name': 'Desfibrilador', 'brand': 'Philips', 'model': 'HeartStart FRx', 'category': 'Equipos Médicos', 'value': 2800},
            {'name': 'Panel Solar 400W', 'brand': 'LG', 'model': 'NeON R', 'category': 'Infraestructura', 'value': 450},
            {'name': 'Aire Acondicionado Central', 'brand': 'Carrier', 'model': 'WeatherExpert', 'category': 'Infraestructura', 'value': 8500},
        ]
        
        locations = [
            ('Edificio Principal', 'Planta Baja', 'Recepción'),
            ('Edificio Principal', 'Piso 1', 'Administración'),
            ('Edificio Principal', 'Piso 2', 'Sistemas'),
            ('Edificio Académico', 'Piso 1', 'Laboratorio 1'),
            ('Edificio Académico', 'Piso 2', 'Aulas'),
            ('Bodega Central', 'N/A', 'Almacén'),
            ('Taller Mecánico', 'N/A', 'Área de Trabajo'),
            ('Centro Médico', 'Planta Baja', 'Consultorio'),
        ]
        
        num_assets = 40 if self.extendido else 15
        
        # Obtener subgrupos para asignar a los bienes
        subgrupos = list(SubgrupoRamo.objects.all())
        if not subgrupos:
            self.stdout.write(self.style.WARNING('No hay SubgrupoRamo disponibles. Ejecuta poblar_catalogo_ramos primero.'))
            return assets
        
        for i in range(num_assets):
            sample = random.choice(sample_assets)
            location = random.choice(locations)
            poliza = random.choice(polizas) if random.random() > 0.15 else None
            
            # Valor con depreciación
            purchase_value = Decimal(str(sample['value'] * random.uniform(0.9, 1.2)))
            years_old = random.uniform(0, 5)
            depreciation = Decimal(str(random.uniform(0.05, 0.20) * years_old))
            current_value = max(purchase_value * (1 - depreciation), purchase_value * Decimal('0.2'))
            
            purchase_date = hoy - timedelta(days=int(years_old * 365))
            
            # Mapeo de estados y condiciones a español
            estado_map = {'active': 'activo', 'inactive': 'inactivo', 'disposed': 'dado_de_baja'}
            condicion_map = {'excellent': 'excelente', 'good': 'bueno', 'fair': 'regular', 'poor': 'malo'}
            
            estado_en = random.choices(
                ['active', 'inactive', 'disposed'],
                weights=[0.85, 0.10, 0.05]
            )[0]
            condicion_en = random.choices(
                ['excellent', 'good', 'fair', 'poor'],
                weights=[0.2, 0.5, 0.25, 0.05]
            )[0]
            
            # Si no hay póliza, usar la primera disponible (BienAsegurado requiere póliza)
            if not poliza:
                poliza = polizas[0] if polizas else None
            if not poliza:
                continue  # Saltar si no hay póliza
            
            asset = BienAsegurado.objects.create(
                poliza=poliza,
                subgrupo_ramo=random.choice(subgrupos),
                responsable_custodio=random.choice(responsables),
                codigo_bien=f'ACT-{base_id + i:05d}',
                nombre=f"{sample['name']} #{i+1}",
                descripcion=f"Bien {sample['name']} asignado para uso institucional.",
                categoria=sample['category'],
                marca=sample['brand'],
                modelo=sample['model'],
                serie=f"SN-{random.randint(100000, 999999)}",
                ubicacion=f"{location[0]} - {location[2]}",
                edificio=location[0],
                piso=location[1],
                departamento=location[2],
                valor_compra=purchase_value.quantize(Decimal('0.01')),
                valor_actual=current_value.quantize(Decimal('0.01')),
                valor_asegurado=current_value.quantize(Decimal('0.01')),
                fecha_adquisicion=purchase_date,
                fecha_garantia=purchase_date + timedelta(days=730) if random.random() > 0.4 else None,
                estado=estado_map[estado_en],
                condicion=condicion_map[condicion_en],
                observaciones=f"Bien registrado en inventario el {purchase_date}.",
                creado_por=usuario,
            )
            assets.append(asset)
        
        return assets

    def create_quotes(self, companias, corredores, tipos_poliza, usuario):
        """Crea cotizaciones de prueba"""
        quotes = []
        hoy = timezone.now().date()
        
        import time
        base_id = int(time.time()) % 100000
        
        titles = [
            'Renovación de seguro vehicular flota 2025',
            'Ampliación cobertura equipos de cómputo',
            'Seguro todo riesgo edificio nuevo',
            'Póliza colectiva de vida empleados',
            'Seguro de transporte mercancías',
            'Cobertura equipos especializados laboratorio',
            'Seguro responsabilidad civil eventos',
            'Póliza multirriesgo empresarial',
        ]
        
        num_quotes = 15 if self.extendido else 5
        
        for i in range(num_quotes):
            dias_atras = random.randint(0, 60) if random.random() > 0.3 else -random.randint(1, 30)
            request_date = hoy - timedelta(days=dias_atras)
            
            status = random.choices(
                ['draft', 'sent', 'under_review', 'accepted', 'rejected', 'expired', 'converted'],
                weights=[0.15, 0.20, 0.15, 0.15, 0.10, 0.10, 0.15]
            )[0]
            
            quote = Quote.objects.create(
                quote_number=f'COT-{hoy.year}-{base_id + i:04d}',
                title=random.choice(titles),
                policy_type=random.choice(tipos_poliza),
                sum_insured=Decimal(str(random.randint(50000, 500000))),
                coverage_details='Cobertura amplia que incluye daños materiales, responsabilidad civil, y asistencia 24/7.',
                request_date=request_date,
                valid_until=request_date + timedelta(days=random.randint(15, 45)),
                desired_start_date=request_date + timedelta(days=random.randint(10, 30)),
                desired_end_date=request_date + timedelta(days=random.randint(375, 730)),
                status=status,
                priority=random.choices(
                    ['low', 'medium', 'high', 'urgent'],
                    weights=[0.15, 0.50, 0.25, 0.10]
                )[0],
                notes='Cotización generada automáticamente para pruebas.',
                requested_by=usuario,
            )
            
            # Crear opciones de cotización (2-4 por cotización)
            num_options = random.randint(2, 4)
            for j in range(num_options):
                base_premium = float(quote.sum_insured) * random.uniform(0.02, 0.08)
                
                QuoteOption.objects.create(
                    quote=quote,
                    insurer=random.choice(companias),
                    broker=random.choice(corredores),
                    premium_amount=Decimal(str(base_premium)).quantize(Decimal('0.01')),
                    deductible=Decimal(str(base_premium * random.uniform(0.05, 0.15))).quantize(Decimal('0.01')),
                    coverage_offered='Cobertura estándar según condiciones generales de la póliza.',
                    exclusions='Se excluyen daños intencionales, guerras, y catástrofes naturales según condiciones.',
                    is_recommended=(j == 0 and random.random() > 0.5),
                    rating=random.randint(3, 5) if random.random() > 0.3 else None,
                    received_date=request_date + timedelta(days=random.randint(3, 10)),
                    valid_until=request_date + timedelta(days=random.randint(30, 60)),
                )
            
            quotes.append(quote)
        
        return quotes

    def create_renewals(self, polizas, usuario):
        """Crea renovaciones de pólizas de prueba"""
        renewals = []
        hoy = timezone.now().date()
        
        import time
        base_id = int(time.time()) % 100000
        
        # Seleccionar pólizas que podrían estar por renovar
        polizas_para_renovar = [p for p in polizas if p.dias_para_vencer <= 60]
        
        if not polizas_para_renovar:
            polizas_para_renovar = random.sample(polizas, min(10, len(polizas)))
        
        num_renewals = min(len(polizas_para_renovar), 12 if self.extendido else 5)
        
        for i, poliza in enumerate(polizas_para_renovar[:num_renewals]):
            notification_date = poliza.fecha_fin - timedelta(days=random.randint(45, 60))
            due_date = poliza.fecha_fin - timedelta(days=random.randint(7, 15))
            
            # Determinar estado basado en fechas
            if due_date < hoy:
                status = random.choice(['completed', 'cancelled', 'rejected'])
            elif due_date < hoy + timedelta(days=15):
                status = random.choice(['pending', 'in_progress', 'quoted'])
            else:
                status = random.choice(['pending', 'in_progress'])
            
            # Prima propuesta con variación
            original_premium = random.uniform(1000, 10000)
            change_pct = random.uniform(-0.1, 0.25)
            proposed_premium = original_premium * (1 + change_pct)
            
            renewal = PolicyRenewal.objects.create(
                original_policy=poliza,
                renewal_number=f'REN-{hoy.year}-{base_id + i:04d}',
                notification_date=notification_date,
                due_date=due_date,
                original_premium=Decimal(str(original_premium)).quantize(Decimal('0.01')),
                proposed_premium=Decimal(str(proposed_premium)).quantize(Decimal('0.01')) if status not in ['pending'] else None,
                status=status,
                decision=random.choice(['renew_same', 'renew_different', 'pending']) if status in ['in_progress', 'quoted'] else 'pending',
                coverage_changes='Sin cambios significativos' if random.random() > 0.3 else 'Se propone ampliar cobertura de responsabilidad civil.',
                notes='Proceso de renovación iniciado automáticamente.',
                created_by=usuario,
            )
            renewals.append(renewal)
        
        return renewals

    def create_payment_approvals(self, pagos):
        """Crea aprobaciones de pago de prueba"""
        approvals = []
        
        # Seleccionar pagos que requieren aprobación (montos altos)
        pagos_para_aprobar = [p for p in pagos if p.monto >= Decimal('1000')]
        
        if not pagos_para_aprobar:
            pagos_para_aprobar = random.sample(pagos, min(10, len(pagos)))
        
        num_approvals = min(len(pagos_para_aprobar), 15 if self.extendido else 5)
        
        for pago in pagos_para_aprobar[:num_approvals]:
            required_level = PaymentApproval.get_required_level(pago.monto)
            
            status = random.choices(
                ['pending', 'approved', 'rejected'],
                weights=[0.40, 0.45, 0.15]
            )[0]
            
            approval = PaymentApproval.objects.create(
                payment=pago,
                approval_level=required_level,
                required_level=required_level,
                status=status,
                request_notes=f'Aprobación requerida para pago de ${pago.monto}',
                decision_notes='Aprobado según procedimiento estándar.' if status == 'approved' else (
                    'Rechazado por falta de documentación.' if status == 'rejected' else ''
                ),
                digital_signature=(status == 'approved'),
            )
            approvals.append(approval)
        
        return approvals

    def create_calendar_events(self, polizas, facturas, usuario):
        """Crea eventos de calendario de prueba"""
        events = []
        hoy = timezone.now().date()
        
        # Eventos de vencimiento de pólizas
        for poliza in polizas:
            if 0 < poliza.dias_para_vencer <= 60:
                priority = 'critical' if poliza.dias_para_vencer <= 7 else (
                    'high' if poliza.dias_para_vencer <= 15 else 'medium'
                )
                
                event, created = CalendarEvent.objects.get_or_create(
                    policy=poliza,
                    event_type='policy_expiry',
                    defaults={
                        'title': f'Vencimiento: {poliza.numero_poliza}',
                        'description': f'Vence la póliza {poliza.numero_poliza} de {poliza.compania_aseguradora}. Suma asegurada: ${poliza.suma_asegurada:,.2f}',
                        'start_date': poliza.fecha_fin,
                        'priority': priority,
                        'is_auto_generated': True,
                        'reminder_days': 15 if priority == 'critical' else 7,
                    }
                )
                if created:
                    events.append(event)
        
        # Eventos de vencimiento de facturas
        for factura in facturas:
            if factura.estado in ['pendiente', 'parcial']:
                dias_para_vencer = (factura.fecha_vencimiento - hoy).days
                if -30 < dias_para_vencer <= 30:
                    priority = 'critical' if dias_para_vencer <= 0 else (
                        'high' if dias_para_vencer <= 7 else 'medium'
                    )
                    
                    event, created = CalendarEvent.objects.get_or_create(
                        invoice=factura,
                        event_type='invoice_due',
                        defaults={
                            'title': f'Factura: {factura.numero_factura}',
                            'description': f'Vence factura {factura.numero_factura}. Saldo pendiente: ${factura.saldo_pendiente:,.2f}',
                            'start_date': factura.fecha_vencimiento,
                            'priority': priority,
                            'is_auto_generated': True,
                            'reminder_days': 7,
                        }
                    )
                    if created:
                        events.append(event)
        
        # Eventos manuales adicionales
        if self.extendido:
            tipos_evento = ['meeting', 'reminder', 'other']
            titulos_reunion = [
                'Reunión con aseguradora',
                'Revisión de siniestros pendientes',
                'Capacitación sobre nuevas pólizas',
                'Auditoría de documentos',
                'Seguimiento renovaciones',
            ]
            
            for i in range(10):
                dias = random.randint(-10, 45)
                fecha = hoy + timedelta(days=dias)
                
                event = CalendarEvent.objects.create(
                    title=random.choice(titulos_reunion),
                    description='Evento programado para seguimiento de actividades.',
                    event_type=random.choice(tipos_evento),
                    priority=random.choice(['low', 'medium', 'high']),
                    start_date=fecha,
                    all_day=random.random() > 0.3,
                    start_time=None if random.random() > 0.3 else timezone.now().time(),
                    is_completed=(dias < -3),
                    is_auto_generated=False,
                    reminder_days=random.choice([1, 3, 7]),
                    created_by=usuario,
                )
                events.append(event)
        
        return events

