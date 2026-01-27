"""
Comando para poblar pólizas con sus desgloses de ramos.
Crea datos de ejemplo con cálculos correctos.
Incluye envío de alertas por documentación pendiente a custodios.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app.models import (
    Alerta,
    BienAsegurado,
    ChecklistSiniestro,
    ChecklistSiniestroConfig,
    CompaniaAseguradora,
    CorredorSeguros,
    DetallePolizaRamo,
    Factura,
    GrupoRamo,
    Poliza,
    ResponsableCustodio,
    Siniestro,
    SubgrupoRamo,
    TipoPoliza,
    TipoRamo,
    TipoSiniestro,
    User,
)


class Command(BaseCommand):
    help = "Pobla pólizas con sus desgloses de ramos y cálculos correctos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--completo",
            action="store_true",
            help="Crear una póliza por cada grupo con TODOS sus subgrupos (8 pólizas, 21 detalles)",
        )
        parser.add_argument(
            "--polizas",
            type=int,
            default=5,
            help="Número de pólizas aleatorias a crear (default: 5, ignorado si --completo)",
        )
        parser.add_argument("--clean", action="store_true", help="Limpiar datos existentes antes de crear nuevos")
        parser.add_argument(
            "--siniestros",
            action="store_true",
            help="Crear siniestros de prueba con fechas atrasadas para generar alertas",
        )
        parser.add_argument(
            "--enviar-alertas", action="store_true", help="Enviar emails de documentación pendiente a los custodios"
        )

    def handle(self, *args, **options):
        completo = options["completo"]
        num_polizas = options["polizas"]
        clean = options["clean"]
        crear_siniestros = options["siniestros"]
        enviar_alertas = options["enviar_alertas"]

        # Si se solicitan siniestros, forzar modo completo (8 pólizas con todos los subramos)
        if crear_siniestros:
            completo = True

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("POBLANDO PÓLIZAS CON DESGLOSE DE RAMOS"))
        self.stdout.write("=" * 60 + "\n")

        with transaction.atomic():
            # 1. Asegurar que existan los ramos
            self.stdout.write("1. Verificando catálogo de ramos...")
            call_command("poblar_catalogo_ramos", verbosity=0)
            self.stdout.write(self.style.SUCCESS("   ✓ Catálogo de ramos verificado\n"))

            # 2. Asegurar entidades base
            self.stdout.write("2. Verificando entidades base...")
            companias_corredores = self._get_or_create_companias()
            tipo_poliza = self._get_or_create_tipo_poliza()
            usuario = self._get_or_create_usuario()

            for comp, corr in companias_corredores:
                self.stdout.write(f"   ✓ {comp.nombre} → Broker: {corr.nombre}")
            self.stdout.write(self.style.SUCCESS("   ✓ Entidades base verificadas\n"))

            # 3. Limpiar si se solicita
            if clean:
                self.stdout.write("3. Limpiando datos existentes...")

                # Primero limpiar siniestros (para poder borrar bienes después)
                bienes_demo = BienAsegurado.objects.filter(codigo_bien__startswith="BIEN-02002001")
                siniestros_demo = Siniestro.objects.filter(bien_asegurado__in=bienes_demo)
                # También siniestros de 6 dígitos
                siniestros_demo_numeros = Siniestro.objects.filter(numero_siniestro__regex=r"^\d{6}$")

                # Eliminar dependencias de siniestros
                Alerta.objects.filter(siniestro__in=siniestros_demo).delete()
                Alerta.objects.filter(siniestro__in=siniestros_demo_numeros).delete()
                ChecklistSiniestro.objects.filter(siniestro__in=siniestros_demo).delete()
                ChecklistSiniestro.objects.filter(siniestro__in=siniestros_demo_numeros).delete()
                count_siniestros = siniestros_demo.count() + siniestros_demo_numeros.count()
                siniestros_demo.delete()
                siniestros_demo_numeros.delete()
                self.stdout.write(f"   ✓ {count_siniestros} siniestros demo eliminados")

                # Limpiar bienes y custodios de prueba
                BienAsegurado.objects.filter(codigo_bien__startswith="BIEN-02002001").delete()
                ResponsableCustodio.objects.filter(nombre__icontains="TEST").delete()

                # Limpiar pólizas creadas por este comando:
                # - Formato nuevo: 6 dígitos numéricos (ej: 123456)
                # - Formato antiguo: POL-DEMO-XXXX
                from django.db.models import Q

                from app.models import Pago

                polizas_demo = Poliza.objects.filter(
                    Q(numero_poliza__regex=r"^\d{6}$") | Q(numero_poliza__startswith="POL-DEMO-")
                )
                count_polizas = polizas_demo.count()
                # Eliminar en orden: Pagos -> Facturas -> Detalles -> Pólizas
                Pago.objects.filter(factura__poliza__in=polizas_demo).delete()
                Factura.objects.filter(poliza__in=polizas_demo).delete()
                DetallePolizaRamo.objects.filter(poliza__in=polizas_demo).delete()
                polizas_demo.delete()
                self.stdout.write(f"   ✓ {count_polizas} pólizas demo eliminadas")
                self.stdout.write(self.style.SUCCESS("   ✓ Datos limpiados\n"))

            # 4. Obtener grupos de ramo disponibles
            grupos = list(GrupoRamo.objects.filter(activo=True).prefetch_related("subgrupos").order_by("orden"))
            if not grupos:
                self.stdout.write(self.style.ERROR("   ✗ No hay grupos de ramo disponibles"))
                return

            polizas_creadas = 0
            detalles_creados = 0
            facturas_creadas = 0

            # Modo completo: una póliza por grupo con TODOS sus subgrupos
            if completo:
                self.stdout.write(f"4. Creando {len(grupos)} pólizas (una por grupo) con TODOS sus subgrupos...\n")

                for i, grupo in enumerate(grupos, 1):
                    subgrupos = list(grupo.subgrupos.filter(activo=True).order_by("orden"))

                    if not subgrupos:
                        continue

                    # Alternar entre compañías
                    compania, corredor = companias_corredores[i % len(companias_corredores)]

                    # Número fijo para Incendio (429965)
                    numero_fijo = "429965" if "incendio" in grupo.nombre.lower() else None

                    # Crear póliza
                    poliza = self._crear_poliza(
                        grupo=grupo,
                        compania=compania,
                        corredor=corredor,
                        tipo_poliza=tipo_poliza,
                        usuario=usuario,
                        numero=i,
                        numero_poliza_fijo=numero_fijo,
                    )
                    polizas_creadas += 1

                    self.stdout.write(f"   📋 Póliza: {poliza.numero_poliza}")
                    self.stdout.write(f"      Grupo: {grupo.nombre} ({len(subgrupos)} subgrupos)")

                    # Totales para la póliza
                    total_suma = Decimal("0")
                    total_prima = Decimal("0")

                    # Totales para la factura (sumados de los detalles)
                    total_contrib_super = Decimal("0")
                    total_seg_campesino = Decimal("0")
                    total_emision = Decimal("0")
                    total_iva = Decimal("0")
                    total_facturado = Decimal("0")
                    total_retenciones = Decimal("0")

                    # Crear detalle para CADA subgrupo del grupo
                    detalles_poliza = []
                    for subgrupo in subgrupos:
                        detalle = self._crear_detalle_ramo(poliza, subgrupo)
                        detalles_poliza.append(detalle)
                        detalles_creados += 1

                        # Sumar para póliza
                        total_suma += detalle.suma_asegurada
                        total_prima += detalle.total_prima

                        # Sumar para factura
                        total_contrib_super += detalle.contribucion_superintendencia
                        total_seg_campesino += detalle.seguro_campesino
                        total_emision += detalle.emision
                        total_iva += detalle.iva
                        total_facturado += detalle.total_facturado
                        total_retenciones += detalle.retencion_prima + detalle.retencion_iva

                        self.stdout.write(
                            f"      └─ {subgrupo.nombre}: "
                            f"Suma ${detalle.suma_asegurada:,.2f} | "
                            f"Prima ${detalle.total_prima:,.2f} | "
                            f"Total ${detalle.total_facturado:,.2f}"
                        )

                    # Actualizar totales de póliza
                    poliza.suma_asegurada = total_suma
                    poliza.prima_neta = total_prima
                    poliza.prima_total = total_facturado
                    poliza.save()

                    # Crear factura que cuadre con el desglose
                    factura = self._crear_factura(
                        poliza=poliza,
                        usuario=usuario,
                        subtotal=total_prima,
                        iva=total_iva,
                        contrib_super=total_contrib_super,
                        seg_campesino=total_seg_campesino,
                        retenciones=total_retenciones,
                        monto_total=total_facturado,
                        detalles=detalles_poliza,
                    )
                    facturas_creadas += 1

                    self.stdout.write(
                        f"      📄 Factura: {factura.numero_factura} | " f"Total: ${factura.monto_total:,.2f}"
                    )
                    self.stdout.write("")

            # Modo aleatorio: número específico de pólizas
            else:
                self.stdout.write(f"4. Creando {num_polizas} pólizas aleatorias...\n")

                for i in range(num_polizas):
                    grupo = random.choice(grupos)
                    subgrupos = list(grupo.subgrupos.filter(activo=True))

                    if not subgrupos:
                        continue

                    # Seleccionar compañía aleatoria
                    compania, corredor = random.choice(companias_corredores)

                    # Número fijo para Incendio (429965)
                    numero_fijo = "429965" if "incendio" in grupo.nombre.lower() else None

                    poliza = self._crear_poliza(
                        grupo=grupo,
                        compania=compania,
                        corredor=corredor,
                        tipo_poliza=tipo_poliza,
                        usuario=usuario,
                        numero=i + 1,
                        numero_poliza_fijo=numero_fijo,
                    )
                    polizas_creadas += 1

                    self.stdout.write(f"   📋 Póliza: {poliza.numero_poliza}")
                    self.stdout.write(f"      Grupo: {grupo.nombre}")

                    max_detalles = min(5, len(subgrupos))
                    num_detalles = random.randint(1, max_detalles) if max_detalles >= 1 else 1
                    subgrupos_seleccionados = random.sample(subgrupos, min(num_detalles, len(subgrupos)))

                    total_suma = Decimal("0")
                    total_prima = Decimal("0")
                    total_contrib_super = Decimal("0")
                    total_seg_campesino = Decimal("0")
                    total_iva = Decimal("0")
                    total_facturado = Decimal("0")
                    total_retenciones = Decimal("0")

                    detalles_poliza = []
                    for subgrupo in subgrupos_seleccionados:
                        detalle = self._crear_detalle_ramo(poliza, subgrupo)
                        detalles_poliza.append(detalle)
                        detalles_creados += 1
                        total_suma += detalle.suma_asegurada
                        total_prima += detalle.total_prima
                        total_contrib_super += detalle.contribucion_superintendencia
                        total_seg_campesino += detalle.seguro_campesino
                        total_iva += detalle.iva
                        total_facturado += detalle.total_facturado
                        total_retenciones += detalle.retencion_prima + detalle.retencion_iva

                        self.stdout.write(
                            f"      └─ {subgrupo.nombre}: "
                            f"Suma ${detalle.suma_asegurada:,.2f} | "
                            f"Prima ${detalle.total_prima:,.2f} | "
                            f"Total ${detalle.total_facturado:,.2f}"
                        )

                    poliza.suma_asegurada = total_suma
                    poliza.prima_neta = total_prima
                    poliza.prima_total = total_facturado
                    poliza.save()

                    # Crear factura
                    factura = self._crear_factura(
                        poliza=poliza,
                        usuario=usuario,
                        subtotal=total_prima,
                        iva=total_iva,
                        contrib_super=total_contrib_super,
                        seg_campesino=total_seg_campesino,
                        retenciones=total_retenciones,
                        monto_total=total_facturado,
                        detalles=detalles_poliza,
                    )
                    facturas_creadas += 1

                    self.stdout.write(
                        f"      📄 Factura: {factura.numero_factura} | " f"Total: ${factura.monto_total:,.2f}"
                    )
                    self.stdout.write("")

            # 5. Crear custodios y bienes de ejemplo
            self.stdout.write("\n5. Creando custodios y bienes de ejemplo...\n")

            # Obtener la primera póliza para asignar bienes
            poliza_ejemplo = Poliza.objects.first()

            if poliza_ejemplo:
                custodios_creados, bienes_creados = self._crear_custodios_y_bienes(poliza_ejemplo)
                self.stdout.write(self.style.SUCCESS(f"   ✓ {custodios_creados} custodios creados"))
                self.stdout.write(self.style.SUCCESS(f"   ✓ {bienes_creados} bienes creados"))
            else:
                custodios_creados = 0
                bienes_creados = 0
                self.stdout.write(self.style.WARNING("   No hay pólizas para asignar bienes"))

            # Crear siniestros para alertas si se solicitó
            siniestros_creados = 0
            emails_enviados = 0
            if crear_siniestros:
                self.stdout.write("\n6. Creando siniestros para alertas (3 custodios, diferentes ramos)...")
                siniestros_creados = self._crear_siniestros_diversos()
                self.stdout.write(self.style.SUCCESS(f"   ✓ {siniestros_creados} siniestros creados para alertas"))

                # Enviar alertas por email si se solicitó
                if enviar_alertas:
                    self.stdout.write("\n7. Enviando emails de documentación pendiente a custodios...")
                    emails_enviados = self._enviar_alertas_custodios()
                    self.stdout.write(self.style.SUCCESS(f"   ✓ {emails_enviados} email(s) enviados a custodios"))

            # Resumen
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("RESUMEN:"))
            self.stdout.write(f"   Pólizas creadas: {polizas_creadas}")
            self.stdout.write(f"   Detalles de ramo creados: {detalles_creados}")
            self.stdout.write(f"   Facturas creadas: {facturas_creadas}")
            self.stdout.write(f"   Custodios creados: {custodios_creados}")
            self.stdout.write(f"   Bienes creados: {bienes_creados}")
            if crear_siniestros:
                self.stdout.write(f"   Siniestros para alertas: {siniestros_creados}")
            if enviar_alertas:
                self.stdout.write(f"   Emails enviados a custodios: {emails_enviados}")
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS("\n¡Datos poblados exitosamente!"))

    def _get_or_create_companias(self):
        """Crea las 2 compañías aseguradoras con sus corredores"""
        companias_data = [
            {
                "nombre": "Chubb Seguros",
                "ruc": "1790123456001",
                "direccion": "Av. 12 de Octubre N24-562 y Cordero",
                "telefono": "02-2505050",
                "email": "renataxdalej@gmail.com",
                "broker": {
                    "nombre": "AON Risk Services Ecuador",
                    "ruc": "1792123456001",
                    "email": "renataxdalej@gmail.com",
                    "telefono": "02-2226789",
                },
            },
            {
                "nombre": "Tecniseguros",
                "ruc": "1790654321001",
                "direccion": "Av. Amazonas N35-17 y Juan Pablo Sanz",
                "telefono": "02-2246800",
                "email": "renataxdalej@gmail.com",
                "broker": {
                    "nombre": "Asertec Corredores de Seguros",
                    "ruc": "1792654321001",
                    "email": "renataxdalej@gmail.com",
                    "telefono": "02-2433456",
                },
            },
        ]

        result = []
        for data in companias_data:
            compania, _ = CompaniaAseguradora.objects.get_or_create(
                nombre=data["nombre"],
                defaults={
                    "ruc": data["ruc"],
                    "direccion": data["direccion"],
                    "telefono": data["telefono"],
                    "email": data["email"],
                    "activo": True,
                },
            )
            # Actualizar email si ya existe
            if compania.email != data["email"]:
                compania.email = data["email"]
                compania.save()

            corredor, _ = CorredorSeguros.objects.get_or_create(
                compania_aseguradora=compania,
                nombre=data["broker"]["nombre"],
                defaults={
                    "ruc": data["broker"]["ruc"],
                    "email": data["broker"]["email"],
                    "telefono": data["broker"]["telefono"],
                    "activo": True,
                },
            )
            # Actualizar email si ya existe
            if corredor.email != data["broker"]["email"]:
                corredor.email = data["broker"]["email"]
                corredor.save()

            result.append((compania, corredor))

        return result

    def _get_or_create_tipo_poliza(self):
        tipo, _ = TipoPoliza.objects.get_or_create(
            nombre="Ramos Generales", defaults={"descripcion": "Pólizas de ramos generales", "activo": True}
        )
        return tipo

    def _get_or_create_usuario(self):
        usuario, _ = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@utpl.edu.ec", "is_staff": True, "is_superuser": True}
        )
        return usuario

    def _crear_poliza(self, grupo, compania, corredor, tipo_poliza, usuario, numero, numero_poliza_fijo=None):
        """Crea una póliza asociada a un grupo de ramo"""
        fecha_inicio = date.today() - timedelta(days=random.randint(0, 180))
        fecha_fin = fecha_inicio + timedelta(days=365)

        # Usar número fijo si se proporciona, sino generar uno aleatorio
        numero_poliza = numero_poliza_fijo if numero_poliza_fijo else Poliza.generar_numero_poliza()

        poliza = Poliza.objects.create(
            numero_poliza=numero_poliza,
            compania_aseguradora=compania,
            corredor_seguros=corredor,
            tipo_poliza=tipo_poliza,
            grupo_ramo=grupo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            suma_asegurada=Decimal("0"),  # Se actualizará después
            prima_neta=Decimal("0"),
            prima_total=Decimal("0"),
            coberturas=f"Cobertura integral para {grupo.nombre}",
            estado="vigente",
            es_gran_contribuyente=random.choice([True, False]),
            creado_por=usuario,
        )
        return poliza

    def _crear_detalle_ramo(self, poliza, subgrupo):
        """Crea un detalle de ramo con cálculos correctos"""
        # Generar valores base más bajos y realistas
        suma_asegurada = Decimal(random.choice([5000, 10000, 15000, 25000, 50000, 75000, 100000]))

        # Tasa de prima entre 1% y 5% de la suma asegurada
        tasa = Decimal(random.uniform(0.01, 0.05))
        total_prima = (suma_asegurada * tasa).quantize(Decimal("0.01"))

        # Mínimo de prima $50, máximo $5000
        if total_prima < 50:
            total_prima = Decimal(random.randint(50, 500))
        elif total_prima > 5000:
            total_prima = Decimal(random.randint(1000, 5000))

        # Crear el detalle (los cálculos se hacen automáticamente en save())
        # numero_factura y documento_contable se obtienen de la factura de la póliza
        detalle = DetallePolizaRamo.objects.create(
            poliza=poliza,
            subgrupo_ramo=subgrupo,
            suma_asegurada=suma_asegurada,
            total_prima=total_prima,
            observaciones=f"Cobertura de {subgrupo.nombre}",
        )

        return detalle

    def _crear_factura(
        self, poliza, usuario, subtotal, iva, contrib_super, seg_campesino, retenciones, monto_total, detalles
    ):
        """Crea una factura que cuadre con el desglose de ramos"""

        # Generar número de factura único (6 dígitos)
        num_factura = Factura.generar_numero_factura()

        # Generar documento contable
        doc_contable = f"P{random.randint(50, 60)}-{random.randint(30000, 50000)}"

        # Fechas
        fecha_emision = poliza.fecha_inicio
        fecha_vencimiento = fecha_emision + timedelta(days=30)

        factura = Factura.objects.create(
            poliza=poliza,
            numero_factura=num_factura,
            documento_contable=doc_contable,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            subtotal=subtotal,
            iva=iva,
            contribucion_superintendencia=contrib_super,
            contribucion_seguro_campesino=seg_campesino,
            retenciones=retenciones,
            descuento_pronto_pago=Decimal("0.00"),
            monto_total=monto_total,
            estado="pendiente",
            creado_por=usuario,
        )

        return factura

    def _crear_custodios_y_bienes(self, poliza):
        """Crea custodios y bienes de ejemplo"""
        custodios_creados = 0
        bienes_creados = 0

        # Datos de custodios de ejemplo
        custodios_data = [
            {
                "nombre": "Juan Carlos Pérez López",
                "email": "jperez@empresa.com",
                "departamento": "Sistemas",
                "cargo": "Analista de Sistemas",
            },
            {
                "nombre": "Ana María González Vega",
                "email": "agonzalez@empresa.com",
                "departamento": "Contabilidad",
                "cargo": "Contadora",
            },
            {
                "nombre": "Carlos Alberto Rodríguez Mora",
                "email": "crodriguez@empresa.com",
                "departamento": "Operaciones",
                "cargo": "Jefe de Operaciones",
            },
            {
                "nombre": "Patricia Elena Martínez Ruiz",
                "email": "pmartinez@empresa.com",
                "departamento": "Recursos Humanos",
                "cargo": "Analista RRHH",
            },
            {
                "nombre": "Roberto Daniel Sánchez Torres",
                "email": "rsanchez@empresa.com",
                "departamento": "Ventas",
                "cargo": "Ejecutivo de Ventas",
            },
            # Custodio TEST
            {
                "nombre": "MARIA FERNANDA GUARDERAS ORTIZ TEST",
                "email": "renataxdalej@gmail.com",
                "departamento": "Sistemas",
                "cargo": "Usuario",
            },
        ]

        # Crear custodios
        custodios = []
        for data in custodios_data:
            custodio, created = ResponsableCustodio.objects.get_or_create(
                nombre=data["nombre"],
                defaults={
                    "email": data["email"],
                    "departamento": data["departamento"],
                    "cargo": data["cargo"],
                    "activo": True,
                },
            )
            custodios.append(custodio)
            if created:
                custodios_creados += 1

        # Datos de bienes de ejemplo
        bienes_data = [
            {
                "nombre": "Laptop HP ProBook 450 G8",
                "marca": "HP",
                "modelo": "ProBook 450 G8",
                "serie": "CND1234567",
                "codigo_activo": "02002001001",
                "valor": Decimal("1200.00"),
            },
            {
                "nombre": "Laptop Lenovo ThinkPad T14",
                "marca": "Lenovo",
                "modelo": "ThinkPad T14",
                "serie": "PF2ABC123",
                "codigo_activo": "02002001002",
                "valor": Decimal("1350.00"),
            },
            {
                "nombre": 'Monitor Dell UltraSharp 27"',
                "marca": "Dell",
                "modelo": "U2722D",
                "serie": "CN1234ABCD",
                "codigo_activo": "02002001003",
                "valor": Decimal("450.00"),
            },
            {
                "nombre": "Impresora HP LaserJet Pro",
                "marca": "HP",
                "modelo": "M404dn",
                "serie": "VNB3R12345",
                "codigo_activo": "02002001004",
                "valor": Decimal("380.00"),
            },
            {
                "nombre": "Proyector Epson PowerLite",
                "marca": "Epson",
                "modelo": "E20",
                "serie": "X5WK123456",
                "codigo_activo": "02002001005",
                "valor": Decimal("650.00"),
            },
            # Bien TEST - CASO ESPECÍFICO (Ramo: Incendios, Subramo: Equipo Electrónico)
            {
                "nombre": "LAPTOP DELL V330 TEST - DAÑO TOTAL POR VARIACION DE VOLTAJE",
                "marca": "DELL",
                "modelo": "V330",
                "serie": "MP1NVD1C",
                "codigo_activo": "02002001648",
                "valor": Decimal("1350.00"),
                "custodio_index": 5,  # María Fernanda Guarderas
                "subramo_especifico": True,  # Usa Incendios > Equipo Electrónico
            },
        ]

        # Obtener subgrupo de ramo por defecto de la póliza
        detalle = poliza.detalles_ramo.first()
        subgrupo_ramo_default = detalle.subgrupo_ramo if detalle else None

        # Buscar subramo específico: Incendios > Equipo Electrónico
        subgrupo_equipo_electronico = SubgrupoRamo.objects.filter(
            nombre__icontains="equipo electr", grupo_ramo__nombre__icontains="incendio"
        ).first()

        if not subgrupo_ramo_default and not subgrupo_equipo_electronico:
            self.stdout.write(self.style.WARNING("      No hay subgrupo de ramo disponible para asignar bienes"))
            return custodios_creados, bienes_creados

        # Crear bienes
        for i, data in enumerate(bienes_data):
            custodio_index = data.get("custodio_index", i % len(custodios))
            custodio = custodios[custodio_index] if custodio_index < len(custodios) else custodios[0]

            # Determinar subramo: específico para TEST, default para otros
            if data.get("subramo_especifico") and subgrupo_equipo_electronico:
                subgrupo_ramo = subgrupo_equipo_electronico
            else:
                subgrupo_ramo = subgrupo_ramo_default

            if not subgrupo_ramo:
                continue

            codigo_bien = f"BIEN-{data['codigo_activo']}"

            bien, created = BienAsegurado.objects.get_or_create(
                codigo_bien=codigo_bien,
                defaults={
                    "poliza": poliza,
                    "subgrupo_ramo": subgrupo_ramo,
                    "nombre": data["nombre"],
                    "descripcion": f"Bien asegurado: {data['nombre']}",
                    "marca": data["marca"],
                    "modelo": data["modelo"],
                    "serie": data["serie"],
                    "codigo_activo": data["codigo_activo"],
                    "valor_asegurado": data["valor"],
                    "valor_actual": data["valor"] * Decimal("0.85"),  # Depreciación del 15%
                    "responsable_custodio": custodio,
                    "ubicacion": f"Oficina {custodio.departamento}",
                    "estado": "activo",
                },
            )
            if created:
                bienes_creados += 1
                self.stdout.write(f"      • {data['nombre'][:50]}... -> {custodio.nombre}")

        return custodios_creados, bienes_creados

    def _crear_siniestros_diversos(self):
        """
        Crea siniestros con:
        - 3 custodios diferentes
        - Diferentes ramos (subramos)
        - Estados de documentación pendiente para generar alertas
        """
        siniestros_creados = 0

        # Obtener tipo de siniestro
        tipo_siniestro = TipoSiniestro.objects.filter(nombre__icontains="daño", activo=True).first()
        if not tipo_siniestro:
            tipo_siniestro = TipoSiniestro.objects.filter(activo=True).first()

        # Crear 3 custodios diferentes (todos con el mismo email para pruebas)
        custodios_data = [
            {
                "nombre": "María Fernanda López Castillo",
                "email": "renataxdalej@gmail.com",
                "departamento": "Sistemas",
                "cargo": "Analista de Sistemas",
            },
            {
                "nombre": "Carlos Eduardo Pérez Mendoza",
                "email": "renataxdalej@gmail.com",
                "departamento": "Contabilidad",
                "cargo": "Contador General",
            },
            {
                "nombre": "Ana Gabriela Torres Vega",
                "email": "renataxdalej@gmail.com",
                "departamento": "Operaciones",
                "cargo": "Jefa de Operaciones",
            },
        ]

        custodios = []
        for data in custodios_data:
            custodio, created = ResponsableCustodio.objects.update_or_create(
                nombre=data["nombre"],
                defaults={
                    "email": data["email"],
                    "departamento": data["departamento"],
                    "cargo": data["cargo"],
                    "activo": True,
                },
            )
            custodios.append(custodio)
            self.stdout.write(f"      Custodio: {custodio.nombre} ({custodio.email})")

        # Seleccionar 3 subramos de diferentes ramos para pruebas
        # EEL (Equipo Electrónico - G1), VLI (Vehículos Livianos - G5), APE (Accidentes Estudiantes - G6)
        codigos_seleccionados = ["EEL", "VLI", "APE"]
        subramos = list(
            SubgrupoRamo.objects.filter(activo=True, codigo__in=codigos_seleccionados)
            .select_related("grupo_ramo")
            .order_by("grupo_ramo__orden")
        )

        if not subramos:
            self.stdout.write(self.style.ERROR("      No hay subramos disponibles"))
            return 0

        self.stdout.write(f"      Creando {len(subramos)} siniestros de prueba...\n")

        # Obtener póliza para asociar siniestros
        poliza = Poliza.objects.first()
        if not poliza:
            self.stdout.write(self.style.ERROR("      No hay pólizas disponibles"))
            return 0

        # Catálogo de bienes para los 3 siniestros de prueba
        catalogo_siniestros = {
            "EEL": {  # Equipo Electrónico (G1: Incendio y líneas aliadas)
                "bien": "Servidor Dell PowerEdge R740",
                "marca": "Dell",
                "modelo": "PowerEdge R740",
                "descripcion": "Daño total en servidor por variación de voltaje",
                "monto": Decimal("18000.00"),
            },
            "VLI": {  # Vehículos Livianos (G5: Vehículos)
                "bien": "Camioneta Toyota Hilux 4x4",
                "marca": "Toyota",
                "modelo": "Hilux SR5 4x4",
                "descripcion": "Colisión frontal en vía Loja-Zamora",
                "monto": Decimal("18000.00"),
            },
            "APE": {  # Accidentes personales estudiantes (G6: Accidentes)
                "bien": "Cobertura Estudiantes - Semestre 2026-1",
                "marca": "N/A",
                "modelo": "Póliza Colectiva",
                "descripcion": "Accidente de estudiante durante práctica de laboratorio",
                "monto": Decimal("8000.00"),
            },
        }

        # Crear un siniestro por cada subramo (3 siniestros, 3 custodios, 3 ramos diferentes)
        dias_por_siniestro = [18, 15, 12]  # Días de antigüedad para cada siniestro

        for idx, subramo in enumerate(subramos):
            custodio = custodios[idx % len(custodios)]
            datos = catalogo_siniestros.get(subramo.codigo)

            if not datos:
                continue

            dias_atras = dias_por_siniestro[idx] if idx < len(dias_por_siniestro) else 15
            fecha_registro = timezone.now() - timedelta(days=dias_atras)
            numero_siniestro = Siniestro.generar_numero_siniestro()

            siniestro = Siniestro.objects.create(
                poliza=poliza,
                numero_siniestro=numero_siniestro,
                subramo=subramo,
                tipo_siniestro=tipo_siniestro,
                fecha_siniestro=fecha_registro,
                bien_nombre=datos["bien"],
                bien_modelo=datos["modelo"],
                bien_serie=f"SN{random.randint(100000, 999999)}",
                bien_marca=datos["marca"],
                bien_codigo_activo=f"ACT{random.randint(10000, 99999)}",
                responsable_custodio=custodio,
                ubicacion=f"Oficina {custodio.departamento}",
                causa=datos["descripcion"],
                descripcion_detallada=f"Siniestro: {datos['descripcion']}",
                monto_estimado=datos["monto"],
                estado="documentacion_pendiente",
            )

            # Actualizar fecha_registro
            Siniestro.objects.filter(pk=siniestro.pk).update(fecha_registro=fecha_registro)

            # Crear checklist si existe configuración
            if tipo_siniestro:
                configs = ChecklistSiniestroConfig.objects.filter(tipo_siniestro=tipo_siniestro, activo=True).order_by(
                    "orden"
                )

                for config in configs:
                    ChecklistSiniestro.objects.get_or_create(
                        siniestro=siniestro, config_item=config, defaults={"completado": False}
                    )

            siniestros_creados += 1
            ramo_nombre = subramo.grupo_ramo.nombre if subramo.grupo_ramo else "Sin ramo"
            self.stdout.write(
                f"      • {numero_siniestro} | {custodio.nombre}\n"
                f"        Ramo: {ramo_nombre} > {subramo.nombre}\n"
                f"        Bien: {datos['bien']} | Días: {dias_atras}"
            )

        return siniestros_creados

    def _enviar_alertas_custodios(self):
        """
        Envía emails de documentación pendiente a los custodios.
        Cada custodio recibe un email personalizado con SOLO sus siniestros.
        """
        emails_enviados = 0

        # Obtener siniestros con documentación pendiente
        siniestros_pendientes = Siniestro.objects.filter(
            estado__in=["registrado", "documentacion_pendiente", "notificado_broker"]
        ).select_related("responsable_custodio", "poliza", "subramo", "subramo__grupo_ramo")

        if not siniestros_pendientes.exists():
            self.stdout.write(self.style.WARNING("      No hay siniestros con documentación pendiente"))
            return 0

        # Agrupar siniestros por CUSTODIO (ID), no por email
        # Así cada custodio recibe solo SUS siniestros aunque tengan el mismo email
        custodios_siniestros = {}
        for s in siniestros_pendientes:
            if s.responsable_custodio and s.responsable_custodio.email:
                custodio_id = s.responsable_custodio.id
                if custodio_id not in custodios_siniestros:
                    custodios_siniestros[custodio_id] = {"custodio": s.responsable_custodio, "siniestros": []}
                custodios_siniestros[custodio_id]["siniestros"].append(s)

        self.stdout.write(f"      Enviando a {len(custodios_siniestros)} custodio(s)...")

        for custodio_id, data in custodios_siniestros.items():
            custodio = data["custodio"]
            siniestros = data["siniestros"]
            nombre = custodio.nombre
            email = custodio.email
            departamento = custodio.departamento or "No especificado"

            # Construir asunto personalizado
            asunto = f"[URGENTE] Documentación Pendiente - Siniestro(s) bajo su custodia"

            # Construir mensaje HTML siguiendo el estilo de base_notificacion.html
            mensaje_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentación Pendiente - UTPL Seguros</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: 'Segoe UI', Roboto, Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: linear-gradient(180deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" align="center" style="max-width: 600px; margin: 0 auto; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); border-radius: 20px; overflow: hidden;">
                    
                    <!-- Barra de urgencia -->
                    <tr>
                        <td style="background: linear-gradient(90deg, #ef4444 0%, #dc2626 50%, #ef4444 100%); height: 8px;">&nbsp;</td>
                    </tr>
                    
                    <!-- Header con alerta -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%); padding: 40px; text-align: center;">
                            <div style="display: inline-block; width: 80px; height: 80px; background: rgba(255,255,255,0.95); border-radius: 50%; margin-bottom: 16px; line-height: 80px; font-size: 42px;">
                                📋
                            </div>
                            <p style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: rgba(0,0,0,0.6); text-transform: uppercase; letter-spacing: 3px;">
                                Documentación Pendiente
                            </p>
                            <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #0f172a;">
                                Acción Requerida del Custodio
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Contenido -->
                    <tr>
                        <td style="background: #ffffff; padding: 36px 40px;">
                            
                            <!-- Info del Custodio -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td style="background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%); border: 2px solid #93c5fd; border-radius: 12px; padding: 20px;">
                                        <p style="margin: 0 0 12px 0; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #1d4ed8;">
                                            👤 Información del Custodio
                                        </p>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="padding: 6px 0; font-size: 13px; color: #1e40af; font-weight: 600; width: 100px;">Nombre:</td>
                                                <td style="padding: 6px 0; font-size: 14px; color: #0f172a; font-weight: 700;">{nombre}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; font-size: 13px; color: #1e40af; font-weight: 600;">Departamento:</td>
                                                <td style="padding: 6px 0; font-size: 14px; color: #334155;">{departamento}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Mensaje -->
                            <p style="font-size: 15px; color: #475569; line-height: 1.7; margin: 0 0 20px 0;">
                                Tiene <strong style="color: #dc2626; font-size: 18px;">{len(siniestros)}</strong> siniestro(s) 
                                bajo su responsabilidad que requieren documentación para continuar con el proceso de reclamo.
                            </p>
                            
                            <!-- Documentos Requeridos -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
                                <tr>
                                    <td style="background: linear-gradient(180deg, #fffbeb 0%, #fef3c7 100%); border: 2px solid #fde68a; border-radius: 12px; padding: 20px;">
                                        <p style="margin: 0 0 16px 0; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #92400e;">
                                            📋 Documentos Requeridos
                                        </p>
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="padding: 10px 0; border-bottom: 1px dashed #fde68a;">
                                                    <span style="font-size: 13px; font-weight: 600; color: #92400e;">1. Proforma / Cotización</span><br>
                                                    <span style="font-size: 12px; color: #78350f;">Cotización de reparación o reposición del bien</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 10px 0; border-bottom: 1px dashed #fde68a;">
                                                    <span style="font-size: 13px; font-weight: 600; color: #92400e;">2. Denuncia</span><br>
                                                    <span style="font-size: 12px; color: #78350f;">En casos de robo, pérdida o daño por terceros</span>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 10px 0;">
                                                    <span style="font-size: 13px; font-weight: 600; color: #92400e;">3. Acta Técnica</span><br>
                                                    <span style="font-size: 12px; color: #78350f;">Descripción técnica del daño sufrido</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Título siniestros -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 16px; border-bottom: 2px solid #0070c4; padding-bottom: 10px;">
                                <tr>
                                    <td>
                                        <p style="margin: 0; font-size: 14px; font-weight: 700; color: #064b83; text-transform: uppercase; letter-spacing: 1px;">
                                            📑 Siniestros Pendientes
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Tabla de siniestros -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
"""

            for idx, s in enumerate(siniestros):
                ramo = s.subramo.nombre if s.subramo else "General"
                color_dias = "#dc2626" if s.dias_desde_registro > 15 else "#d97706"
                bg_color = "#ffffff" if idx % 2 == 0 else "#f8fafc"
                mensaje_html += f"""
                                <tr style="background: {bg_color};">
                                    <td style="padding: 16px 20px; border-bottom: 1px solid #e2e8f0;">
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td style="font-size: 15px; font-weight: 700; color: #0f172a;">{s.numero_siniestro}</td>
                                                <td align="right" style="font-size: 14px; font-weight: 700; color: {color_dias};">{s.dias_desde_registro} días</td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="padding-top: 6px; font-size: 13px; color: #475569;">{s.bien_nombre}</td>
                                            </tr>
                                            <tr>
                                                <td colspan="2" style="padding-top: 4px; font-size: 12px; color: #64748b;">Ramo: {ramo}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
"""

            mensaje_html += f"""
                            </table>
                            
                            <!-- Nota de acción -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 24px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-left: 4px solid #dc2626; border-radius: 0 12px 12px 0; padding: 16px 20px;">
                                        <p style="margin: 0 0 4px 0; font-size: 12px; font-weight: 700; color: #b91c1c; text-transform: uppercase; letter-spacing: 1px;">
                                            🔔 Acción Requerida
                                        </p>
                                        <p style="margin: 0; font-size: 14px; color: #991b1b; line-height: 1.5;">
                                            Responda a este correo adjuntando los documentos o contacte al Departamento de Seguros.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); padding: 28px 40px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td align="center" style="padding-bottom: 16px;">
                                        <span style="font-size: 14px; font-weight: 700; color: #ffffff;">🛡️ Seguros UTPL</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 16px; border-top: 1px solid #334155;">
                                        <p style="margin: 0; font-size: 11px; color: #64748b; line-height: 1.6;">
                                            Este mensaje fue generado automáticamente.<br>
                                            © 2026 Universidad Técnica Particular de Loja
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

            # Construir mensaje texto plano
            mensaje_texto = f"""
================================================================================
                    UNIVERSIDAD TÉCNICA PARTICULAR DE LOJA
                       Sistema de Gestión de Seguros
================================================================================

⚠️  ALERTA: DOCUMENTACIÓN PENDIENTE

--------------------------------------------------------------------------------
INFORMACIÓN DEL CUSTODIO:
--------------------------------------------------------------------------------
Nombre:       {nombre}
Departamento: {departamento}
Email:        {email}

--------------------------------------------------------------------------------

Estimado/a {nombre},

Le notificamos que tiene {len(siniestros)} siniestro(s) bajo su responsabilidad
que requieren documentación para continuar con el proceso de reclamo.

================================================================================
DOCUMENTOS QUE DEBE ENVIAR:
================================================================================

1. PROFORMA / COTIZACIÓN
   Cotización de reparación o reposición del bien dañado

2. DENUNCIA
   Requerida en casos de robo, pérdida o daño por terceros

3. ACTA TÉCNICA
   Descripción técnica detallada del daño sufrido

================================================================================
SUS SINIESTROS PENDIENTES:
================================================================================
"""
            for s in siniestros:
                ramo = s.subramo.nombre if s.subramo else "General"
                mensaje_texto += f"""
Nº Siniestro: {s.numero_siniestro}
Bien:         {s.bien_nombre}
Ramo:         {ramo}
Días pend.:   {s.dias_desde_registro} días
--------------------------------------------------------------------------------
"""

            mensaje_texto += f"""
================================================================================
¿CÓMO ENVIAR LA DOCUMENTACIÓN?
================================================================================

Responda directamente a este correo adjuntando los documentos, o acérquese
al Departamento de Seguros de la UTPL.

⚠️  IMPORTANTE: El retraso en la entrega de documentación puede afectar el 
proceso de indemnización.

--------------------------------------------------------------------------------
Sistema de Gestión de Seguros - UTPL
Este es un mensaje automático.
================================================================================
"""

            try:
                # Enviar email
                email_msg = EmailMultiAlternatives(
                    subject=asunto, body=mensaje_texto, from_email=settings.DEFAULT_FROM_EMAIL, to=[email]
                )
                email_msg.attach_alternative(mensaje_html, "text/html")
                email_msg.send(fail_silently=False)

                emails_enviados += 1
                self.stdout.write(
                    self.style.SUCCESS(f"      ✓ Email enviado a {nombre} ({email}) - {len(siniestros)} siniestro(s)")
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"      ✗ Error al enviar a {email}: {str(e)}"))

        return emails_enviados
