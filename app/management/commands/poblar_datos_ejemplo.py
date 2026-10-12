"""
Comando para poblar la base de datos con datos de ejemplo completos.
Incluye: Compañías, Corredores, Tipos, Pólizas, Siniestros, Checklist, Alertas, etc.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Puebla la base de datos con datos de ejemplo completos incluyendo checklist de siniestros"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Elimina todos los datos existentes antes de poblar",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Iniciando población de datos de ejemplo..."))

        if options["limpiar"]:
            self.limpiar_datos()

        # Importar modelos aquí para evitar problemas de imports circulares
        from app.models import (
            Alerta,
            ChecklistSiniestro,
            ChecklistSiniestroConfig,
            CompaniaAseguradora,
            CorredorSeguros,
            Factura,
            Poliza,
            Ramo,
            ResponsableCustodio,
            Siniestro,
            TipoPoliza,
            TipoSiniestro,
        )

        # 1. Crear usuario admin si no existe
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@utpl.edu.ec",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Administrador",
                "last_name": "Sistema",
            },
        )
        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write(self.style.SUCCESS("  ✅ Usuario admin creado (password: admin123)"))

        # 2. Compañías Aseguradoras
        companias_data = [
            {
                "nombre": "Seguros Equinoccial S.A.",
                "ruc": "1790010937001",
                "direccion": "Av. República E7-123, Quito",
                "telefono": "02-2998000",
                "email": "info@segurosequinoccial.com",
            },
            {
                "nombre": "AIG Metropolitana S.A.",
                "ruc": "1790283526001",
                "direccion": "Av. 12 de Octubre N24-562, Quito",
                "telefono": "02-2235600",
                "email": "info@aig.com.ec",
            },
            {
                "nombre": "Liberty Seguros S.A.",
                "ruc": "1790401524001",
                "direccion": "Av. NNUU E3-82, Quito",
                "telefono": "02-3999000",
                "email": "info@libertyseguros.ec",
            },
            {
                "nombre": "Chubb Seguros Ecuador S.A.",
                "ruc": "0990283869001",
                "direccion": "Av. Francisco de Orellana, Guayaquil",
                "telefono": "04-2681700",
                "email": "info@chubb.com.ec",
            },
            {
                "nombre": "Mapfre Atlas S.A.",
                "ruc": "0990016870001",
                "direccion": "Av. 9 de Octubre 100, Guayaquil",
                "telefono": "04-2566000",
                "email": "info@mapfre.com.ec",
            },
        ]

        companias = []
        for data in companias_data:
            comp, created = CompaniaAseguradora.objects.get_or_create(ruc=data["ruc"], defaults=data)
            companias.append(comp)
        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(companias)} compañías aseguradoras"))

        # 3. Corredores de Seguros
        corredores_data = [
            {
                "nombre": "Tecniseguros S.A.",
                "ruc": "1790451801001",
                "direccion": "Av. Amazonas N37-29, Quito",
                "telefono": "02-2469000",
                "email": "info@tecniseguros.com",
            },
            {
                "nombre": "AON Ecuador S.A.",
                "ruc": "1791256727001",
                "direccion": "Av. República del Salvador N34-183, Quito",
                "telefono": "02-3952500",
                "email": "info@aon.com.ec",
            },
            {
                "nombre": "Marsh Ecuador S.A.",
                "ruc": "1791714091001",
                "direccion": "Av. 12 de Octubre N26-97, Quito",
                "telefono": "02-2546600",
                "email": "info@marsh.com.ec",
            },
        ]

        corredores = []
        for data in corredores_data:
            corr, created = CorredorSeguros.objects.get_or_create(ruc=data["ruc"], defaults=data)
            corredores.append(corr)
        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(corredores)} corredores de seguros"))

        # 4. Tipos de Póliza
        tipos_poliza_data = [
            {"nombre": "Todo Riesgo", "descripcion": "Cobertura integral para bienes muebles e inmuebles"},
            {"nombre": "Vehículos", "descripcion": "Cobertura para flota vehicular institucional"},
            {"nombre": "Robo", "descripcion": "Cobertura contra robo y asalto"},
            {"nombre": "Incendio", "descripcion": "Cobertura contra incendio y líneas aliadas"},
            {"nombre": "Responsabilidad Civil", "descripcion": "Cobertura de responsabilidad civil general"},
            {"nombre": "Equipo Electrónico", "descripcion": "Cobertura para equipos electrónicos y de cómputo"},
        ]

        tipos_poliza = []
        for data in tipos_poliza_data:
            tipo, created = TipoPoliza.objects.get_or_create(nombre=data["nombre"], defaults=data)
            tipos_poliza.append(tipo)
        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(tipos_poliza)} tipos de póliza"))

        # 5. Tipos de Siniestro
        tipos_siniestro_data = [
            ("robo", "Robo"),
            ("hurto", "Hurto"),
            ("incendio", "Incendio"),
            ("accidente_vehicular", "Accidente Vehicular"),
            ("dano_equipo", "Daño de Equipo"),
            ("desastre_natural", "Desastre Natural"),
            ("vandalismo", "Vandalismo"),
        ]

        tipos_siniestro = []
        for nombre_key, descripcion in tipos_siniestro_data:
            tipo, created = TipoSiniestro.objects.get_or_create(
                nombre=nombre_key, defaults={"descripcion": f"Siniestro por {descripcion.lower()}"}
            )
            tipos_siniestro.append(tipo)
        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(tipos_siniestro)} tipos de siniestro"))

        # 6. Configurar Checklist por Tipo de Siniestro
        checklist_config = {
            "robo": [
                ("Denuncia Policial", True, "Copia certificada de la denuncia ante la Policía Nacional"),
                ("Fotografías del lugar", True, "Evidencia fotográfica del lugar del siniestro"),
                ("Declaración Jurada", True, "Declaración jurada del afectado"),
                ("Inventario de bienes sustraídos", True, "Lista detallada de bienes robados con valores"),
                ("Facturas o comprobantes de compra", False, "Documentos que acrediten propiedad"),
                ("Informe del custodio", True, "Informe del responsable del bien"),
            ],
            "hurto": [
                ("Denuncia Policial", True, "Copia certificada de la denuncia"),
                ("Fotografías", True, "Evidencia fotográfica"),
                ("Declaración Jurada", True, "Declaración del afectado"),
                ("Inventario de bienes", True, "Lista de bienes hurtados"),
                ("Informe del custodio", True, "Informe del responsable"),
            ],
            "incendio": [
                ("Informe de Bomberos", True, "Informe oficial del Cuerpo de Bomberos"),
                ("Fotografías del siniestro", True, "Evidencia fotográfica de los daños"),
                ("Peritaje de daños", True, "Informe de perito avaluador"),
                ("Inventario de bienes afectados", True, "Lista completa de bienes dañados"),
                ("Proforma de reparación/reposición", True, "Cotización de trabajos de reparación"),
                ("Declaración Jurada", True, "Declaración del afectado"),
            ],
            "accidente_vehicular": [
                ("Parte Policial", True, "Parte policial del accidente"),
                ("Fotografías del vehículo", True, "Fotos de los daños del vehículo"),
                ("Licencia de conducir", True, "Copia de licencia del conductor"),
                ("Matrícula del vehículo", True, "Copia de matrícula vigente"),
                ("Proforma de reparación", True, "Cotización del taller autorizado"),
                ("Informe del conductor", True, "Declaración del conductor"),
                ("Croquis del accidente", False, "Diagrama del accidente"),
            ],
            "dano_equipo": [
                ("Informe técnico", True, "Informe técnico del daño"),
                ("Fotografías del equipo", True, "Evidencia fotográfica"),
                ("Proforma de reparación", True, "Cotización de reparación"),
                ("Certificado de garantía", False, "Si aplica garantía del fabricante"),
                ("Informe del custodio", True, "Informe del responsable del equipo"),
            ],
            "desastre_natural": [
                ("Declaración de emergencia", True, "Declaratoria oficial si existe"),
                ("Informe de autoridad competente", True, "Informe de Gestión de Riesgos"),
                ("Fotografías de daños", True, "Evidencia fotográfica"),
                ("Peritaje de daños", True, "Informe de perito"),
                ("Inventario de bienes afectados", True, "Lista de bienes dañados"),
                ("Proformas de reparación", True, "Cotizaciones"),
            ],
            "vandalismo": [
                ("Denuncia Policial", True, "Copia de denuncia"),
                ("Fotografías", True, "Evidencia fotográfica de daños"),
                ("Informe de seguridad", True, "Informe del personal de seguridad"),
                ("Inventario de daños", True, "Lista de bienes afectados"),
                ("Proforma de reparación", True, "Cotización de reparaciones"),
            ],
        }

        items_creados = 0
        for tipo in tipos_siniestro:
            items = checklist_config.get(tipo.nombre, [])
            for orden, (nombre, obligatorio, descripcion) in enumerate(items, start=1):
                item, created = ChecklistSiniestroConfig.objects.get_or_create(
                    tipo_siniestro=tipo,
                    nombre=nombre,
                    defaults={
                        "descripcion": descripcion,
                        "es_obligatorio": obligatorio,
                        "orden": orden,
                        "activo": True,
                    },
                )
                if created:
                    items_creados += 1

        self.stdout.write(self.style.SUCCESS(f"  ✅ {items_creados} items de checklist configurados"))

        # 7. Responsables/Custodios
        responsables_data = [
            {
                "nombre": "Dr. Juan Carlos Pérez",
                "cargo": "Director de TI",
                "departamento": "Tecnología de Información",
                "email": "jcperez@utpl.edu.ec",
                "telefono": "07-2570275",
            },
            {
                "nombre": "Ing. María Elena García",
                "cargo": "Coordinadora Administrativa",
                "departamento": "Servicios Generales",
                "email": "megarcia@utpl.edu.ec",
                "telefono": "07-2570276",
            },
            {
                "nombre": "Lic. Roberto Andrade",
                "cargo": "Jefe de Logística",
                "departamento": "Logística",
                "email": "randrade@utpl.edu.ec",
                "telefono": "07-2570277",
            },
            {
                "nombre": "Ing. Ana Lucia Sánchez",
                "cargo": "Directora de Investigación",
                "departamento": "Investigación",
                "email": "alsanchez@utpl.edu.ec",
                "telefono": "07-2570278",
            },
            {
                "nombre": "Dr. Fernando López",
                "cargo": "Decano de Ingeniería",
                "departamento": "Facultad de Ingeniería",
                "email": "flopez@utpl.edu.ec",
                "telefono": "07-2570279",
            },
        ]

        responsables = []
        for data in responsables_data:
            resp, created = ResponsableCustodio.objects.get_or_create(email=data["email"], defaults=data)
            responsables.append(resp)
        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(responsables)} responsables/custodios"))

        # 8. Inicializar Ramos si existe el método
        try:
            Ramo.crear_ramos_predefinidos()
            self.stdout.write(self.style.SUCCESS("  ✅ Ramos predefinidos inicializados"))
        except Exception:  # noqa: S110 - seed data, the method may not exist
            pass

        # 9. Pólizas
        hoy = timezone.now().date()
        polizas_data = [
            {
                "numero_poliza": "POL-2025-001",
                "tipo_poliza": tipos_poliza[0],  # Todo Riesgo
                "compania_aseguradora": companias[0],
                "corredor_seguros": corredores[0],
                "fecha_inicio": hoy - timedelta(days=180),
                "fecha_fin": hoy + timedelta(days=185),
                "suma_asegurada": Decimal("5000000.00"),
                "prima_total": Decimal("25000.00"),
                "estado": "vigente",
            },
            {
                "numero_poliza": "POL-2025-002",
                "tipo_poliza": tipos_poliza[1],  # Vehículos
                "compania_aseguradora": companias[1],
                "corredor_seguros": corredores[1],
                "fecha_inicio": hoy - timedelta(days=90),
                "fecha_fin": hoy + timedelta(days=275),
                "suma_asegurada": Decimal("2000000.00"),
                "prima_total": Decimal("18000.00"),
                "estado": "vigente",
            },
            {
                "numero_poliza": "POL-2025-003",
                "tipo_poliza": tipos_poliza[5],  # Equipo Electrónico
                "compania_aseguradora": companias[2],
                "corredor_seguros": corredores[2],
                "fecha_inicio": hoy - timedelta(days=60),
                "fecha_fin": hoy + timedelta(days=305),
                "suma_asegurada": Decimal("1500000.00"),
                "prima_total": Decimal("12000.00"),
                "estado": "vigente",
            },
            {
                "numero_poliza": "POL-2024-010",
                "tipo_poliza": tipos_poliza[3],  # Incendio
                "compania_aseguradora": companias[3],
                "corredor_seguros": corredores[0],
                "fecha_inicio": hoy - timedelta(days=400),
                "fecha_fin": hoy - timedelta(days=35),
                "suma_asegurada": Decimal("10000000.00"),
                "prima_total": Decimal("45000.00"),
                "estado": "vencida",
            },
        ]

        polizas = []
        for data in polizas_data:
            pol, created = Poliza.objects.get_or_create(numero_poliza=data["numero_poliza"], defaults=data)
            polizas.append(pol)
        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(polizas)} pólizas"))

        # 10. Siniestros con Checklist
        siniestros_data = [
            {
                "numero_siniestro": "SIN-2026-001",
                "poliza": polizas[0],
                "tipo_siniestro": tipos_siniestro[0],  # Robo
                "fecha_siniestro": timezone.now() - timedelta(days=15),
                "bien_nombre": "Laptop Dell Latitude 5520",
                "bien_marca": "Dell",
                "bien_modelo": "Latitude 5520",
                "bien_serie": "DELL-5520-ABC123",
                "bien_codigo_activo": "ACT-TI-2024-0150",
                "responsable_custodio": responsables[0],
                "ubicacion": "Edificio Central, Oficina 305",
                "causa": "Robo durante la noche, se forzó la cerradura de la oficina",
                "descripcion_detallada": "El día 05/01/2026, al llegar a la oficina se encontró la puerta forzada y la laptop había sido sustraída. Se reportó inmediatamente a seguridad.",
                "monto_estimado": Decimal("1500.00"),
                "estado": "documentacion_pendiente",
                "email_broker": "broker@tecniseguros.com",
            },
            {
                "numero_siniestro": "SIN-2026-002",
                "poliza": polizas[1],
                "tipo_siniestro": tipos_siniestro[3],  # Accidente Vehicular
                "fecha_siniestro": timezone.now() - timedelta(days=8),
                "bien_nombre": "Toyota Hilux 2023",
                "bien_marca": "Toyota",
                "bien_modelo": "Hilux 4x4",
                "bien_serie": "JTFST22P8M0123456",
                "bien_codigo_activo": "VEH-2023-025",
                "responsable_custodio": responsables[2],
                "ubicacion": "Av. Manuel Agustín Aguirre y Rocafuerte, Loja",
                "causa": "Colisión lateral con otro vehículo en intersección",
                "descripcion_detallada": "El conductor oficial del vehículo fue impactado por un vehículo particular que no respetó la señal de alto. Daños en puerta y guardafango derecho.",
                "monto_estimado": Decimal("4500.00"),
                "estado": "enviado_aseguradora",
                "fecha_envio_aseguradora": hoy - timedelta(days=5),
                "email_broker": "siniestros@aon.com.ec",
            },
            {
                "numero_siniestro": "SIN-2026-003",
                "poliza": polizas[2],
                "tipo_siniestro": tipos_siniestro[4],  # Daño Equipo
                "fecha_siniestro": timezone.now() - timedelta(days=3),
                "bien_nombre": "Servidor HPE ProLiant DL380",
                "bien_marca": "HPE",
                "bien_modelo": "ProLiant DL380 Gen10",
                "bien_serie": "HPE-DL380-XYZ789",
                "bien_codigo_activo": "SRV-DC-2022-005",
                "responsable_custodio": responsables[0],
                "ubicacion": "Data Center Principal, Rack A-15",
                "causa": "Falla en el sistema de enfriamiento causó sobrecalentamiento",
                "descripcion_detallada": "Durante el fin de semana se produjo una falla en el sistema HVAC del data center. El servidor sufrió daños por sobrecalentamiento.",
                "monto_estimado": Decimal("15000.00"),
                "estado": "registrado",
                "email_broker": "reclamos@marsh.com.ec",
            },
        ]

        siniestros = []
        for data in siniestros_data:
            sin, created = Siniestro.objects.get_or_create(
                numero_siniestro=data["numero_siniestro"], defaults={**data, "creado_por": admin}
            )
            siniestros.append(sin)

            # Crear items de checklist para este siniestro
            if created and sin.tipo_siniestro:
                configs = ChecklistSiniestroConfig.objects.filter(tipo_siniestro=sin.tipo_siniestro, activo=True)
                for config in configs:
                    ChecklistSiniestro.objects.get_or_create(
                        siniestro=sin, config_item=config, defaults={"completado": False}
                    )

        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(siniestros)} siniestros con checklist"))

        # 11. Facturas
        facturas_data = [
            {
                "numero_factura": "FAC-2026-0001",
                "poliza": polizas[0],
                "fecha_emision": hoy - timedelta(days=30),
                "fecha_vencimiento": hoy + timedelta(days=15),
                "monto_total": Decimal("6250.00"),
                "estado": "pendiente",
                "concepto": "Prima trimestral póliza Todo Riesgo",
            },
            {
                "numero_factura": "FAC-2026-0002",
                "poliza": polizas[1],
                "fecha_emision": hoy - timedelta(days=60),
                "fecha_vencimiento": hoy - timedelta(days=15),
                "monto_total": Decimal("4500.00"),
                "estado": "vencida",
                "concepto": "Prima trimestral póliza Vehículos",
            },
        ]

        facturas = []
        for data in facturas_data:
            fac, created = Factura.objects.get_or_create(numero_factura=data["numero_factura"], defaults=data)
            facturas.append(fac)
        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(facturas)} facturas"))

        # 12. Alertas
        alertas_data = [
            {
                "tipo_alerta": "vencimiento_poliza",
                "titulo": "Póliza próxima a vencer",
                "mensaje": f"La póliza {polizas[0].numero_poliza} vence en 30 días. Inicie el proceso de renovación.",
                "poliza": polizas[0],
                "estado": "pendiente",
            },
            {
                "tipo_alerta": "pago_pendiente",
                "titulo": "Factura con pago vencido",
                "mensaje": "La factura FAC-2026-0002 tiene 15 días de vencida. Monto: $4,500.00",
                "factura": facturas[1] if len(facturas) > 1 else None,
                "estado": "pendiente",
            },
            {
                "tipo_alerta": "documentacion_pendiente",
                "titulo": "Documentación pendiente de siniestro",
                "mensaje": f"El siniestro {siniestros[0].numero_siniestro} tiene documentación pendiente por más de 10 días.",
                "siniestro": siniestros[0],
                "estado": "pendiente",
            },
        ]

        for data in alertas_data:
            if data.get("factura") is None and "factura" in data:
                del data["factura"]
            alerta, created = Alerta.objects.get_or_create(titulo=data["titulo"], defaults=data)
            if created:
                alerta.destinatarios.add(admin)

        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(alertas_data)} alertas"))

        # Resumen final
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("━" * 50))
        self.stdout.write(self.style.SUCCESS("✅ POBLACIÓN DE DATOS COMPLETADA"))
        self.stdout.write(self.style.SUCCESS("━" * 50))
        self.stdout.write("  👤 Usuario: admin / admin123")
        self.stdout.write(f"  🏢 Compañías: {len(companias)}")
        self.stdout.write(f"  🤝 Corredores: {len(corredores)}")
        self.stdout.write(f"  📋 Pólizas: {len(polizas)}")
        self.stdout.write(f"  ⚠️  Siniestros: {len(siniestros)}")
        self.stdout.write(f"  📝 Items Checklist: {items_creados}")
        self.stdout.write(f"  💰 Facturas: {len(facturas)}")
        self.stdout.write(self.style.SUCCESS("━" * 50))

    def limpiar_datos(self):
        """Elimina todos los datos existentes"""
        from app.models import AdjuntoSiniestro, Alerta, ChecklistSiniestro, Documento, Factura, Pago, Poliza, Siniestro

        self.stdout.write(self.style.WARNING("⚠️  Limpiando datos existentes..."))

        # Orden de eliminación para respetar FK
        ChecklistSiniestro.objects.all().delete()
        AdjuntoSiniestro.objects.all().delete()
        Alerta.objects.all().delete()
        Documento.objects.all().delete()
        Siniestro.objects.all().delete()
        Pago.objects.all().delete()
        Factura.objects.all().delete()
        Poliza.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("  ✅ Datos limpiados"))
