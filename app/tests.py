from django.test import TestCase
from decimal import Decimal
from app.models import (
    Poliza, DetallePolizaRamo, Ramo, CompaniaAseguradora,
    TipoPoliza, CorredorSeguros, ConfiguracionSistema
)
from django.utils import timezone
from datetime import timedelta


class DetallePolizaRamoCalculosTest(TestCase):
    """
    Tests unitarios para validar los cálculos del modelo DetallePolizaRamo.
    Verifica que las contribuciones, impuestos y retenciones se calculen correctamente.
    """

    @classmethod
    def setUpTestData(cls):
        """Configuración inicial de datos para todos los tests"""

        # Crear configuraciones del sistema
        ConfiguracionSistema.objects.create(
            clave='PORCENTAJE_SUPERINTENDENCIA',
            valor='0.035',
            tipo='decimal',
            descripcion='Porcentaje de contribución a la Superintendencia'
        )
        ConfiguracionSistema.objects.create(
            clave='PORCENTAJE_SEGURO_CAMPESINO',
            valor='0.005',
            tipo='decimal',
            descripcion='Porcentaje de seguro campesino'
        )

        # Crear compañía aseguradora
        cls.compania = CompaniaAseguradora.objects.create(
            nombre='Seguros Unidos',
            ruc='1234567890001',
            direccion='Av. Principal 123',
            telefono='022345678',
            email='contacto@segurosunidos.com'
        )

        # Crear corredor de seguros
        cls.corredor = CorredorSeguros.objects.create(
            nombre='Juan Pérez',
            ruc='1234567890001',
            telefono='0998765432',
            email='juan.perez@broker.com'
        )

        # Crear tipo de póliza
        cls.tipo_poliza = TipoPoliza.objects.create(
            nombre='Seguros Generales',
            descripcion='Póliza de seguros generales'
        )

        # Crear ramos
        cls.ramo_incendio = Ramo.objects.create(
            codigo='INC',
            nombre='Incendio',
            descripcion='Ramo de incendio y líneas aliadas'
        )

        cls.ramo_lucro = Ramo.objects.create(
            codigo='LC',
            nombre='Lucro Cesante',
            descripcion='Ramo de lucro cesante'
        )

        # Crear póliza Gran Contribuyente
        cls.poliza_gc = Poliza.objects.create(
            numero_poliza='POL-GC-001',
            compania_aseguradora=cls.compania,
            corredor_seguros=cls.corredor,
            tipo_poliza=cls.tipo_poliza,
            suma_asegurada=Decimal('1000000.00'),
            coberturas='Cobertura completa de prueba',
            es_gran_contribuyente=True,
            fecha_inicio=timezone.now().date(),
            fecha_fin=timezone.now().date() + timedelta(days=365),
            estado='vigente'
        )

        # Crear póliza No Gran Contribuyente
        cls.poliza_no_gc = Poliza.objects.create(
            numero_poliza='POL-NOGC-001',
            compania_aseguradora=cls.compania,
            corredor_seguros=cls.corredor,
            tipo_poliza=cls.tipo_poliza,
            suma_asegurada=Decimal('500000.00'),
            coberturas='Cobertura básica de prueba',
            es_gran_contribuyente=False,
            fecha_inicio=timezone.now().date(),
            fecha_fin=timezone.now().date() + timedelta(days=365),
            estado='vigente'
        )

    def test_calculo_incendio_gran_contribuyente(self):
        """
        Test Caso 1: Incendio Gran Contribuyente
        Prima: 150,000
        Emisión: 9
        Esperados:
        - contribucion_superintendencia = 5,250 (3.5%)
        - seguro_campesino = 750 (0.5%)
        - base_imponible = 156,009
        - iva = 23,401.35 (15%)
        - total_facturado = 179,410.35
        - retencion_iva = 23,401.35 (100% IVA)
        - valor_por_pagar = 156,009
        """
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_gc,
            ramo=self.ramo_incendio,
            total_prima=Decimal('150000.00'),
            emision=Decimal('9.00'),
            suma_asegurada=Decimal('1000000.00')
        )

        # Verificar contribución superintendencia (3.5%)
        self.assertAlmostEqual(
            float(detalle.contribucion_superintendencia),
            5250.00,
            places=2,
            msg="Contribución superintendencia incorrecta"
        )

        # Verificar seguro campesino (0.5%)
        self.assertAlmostEqual(
            float(detalle.seguro_campesino),
            750.00,
            places=2,
            msg="Seguro campesino incorrecto"
        )

        # Verificar base imponible
        self.assertAlmostEqual(
            float(detalle.base_imponible),
            156009.00,
            places=2,
            msg="Base imponible incorrecta"
        )

        # Verificar IVA (15%)
        self.assertAlmostEqual(
            float(detalle.iva),
            23401.35,
            places=2,
            msg="IVA incorrecto"
        )

        # Verificar total facturado
        self.assertAlmostEqual(
            float(detalle.total_facturado),
            179410.35,
            places=2,
            msg="Total facturado incorrecto"
        )

        # Verificar retención prima (1%)
        self.assertAlmostEqual(
            float(detalle.retencion_prima),
            1500.00,
            places=2,
            msg="Retención prima incorrecta"
        )

        # Verificar retención IVA (100% del IVA)
        self.assertAlmostEqual(
            float(detalle.retencion_iva),
            23401.35,
            places=2,
            msg="Retención IVA incorrecta"
        )

        # Verificar valor por pagar
        self.assertAlmostEqual(
            float(detalle.valor_por_pagar),
            154509.00,
            places=2,
            msg="Valor por pagar incorrecto"
        )

    def test_calculo_lucro_cesante_gran_contribuyente(self):
        """
        Test Caso 2: Lucro Cesante Gran Contribuyente
        Prima: 14,000
        Emisión: 0
        Esperados:
        - contribucion_superintendencia = 490
        - seguro_campesino = 70
        - base_imponible = 14,560
        - iva = 2,184
        - total_facturado = 16,744
        """
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_gc,
            ramo=self.ramo_lucro,
            total_prima=Decimal('14000.00'),
            emision=Decimal('0.00'),
            suma_asegurada=Decimal('100000.00')
        )

        # Verificar contribución superintendencia (3.5%)
        self.assertAlmostEqual(
            float(detalle.contribucion_superintendencia),
            490.00,
            places=2,
            msg="Contribución superintendencia incorrecta"
        )

        # Verificar seguro campesino (0.5%)
        self.assertAlmostEqual(
            float(detalle.seguro_campesino),
            70.00,
            places=2,
            msg="Seguro campesino incorrecto"
        )

        # Verificar base imponible
        self.assertAlmostEqual(
            float(detalle.base_imponible),
            14560.00,
            places=2,
            msg="Base imponible incorrecta"
        )

        # Verificar IVA (15%)
        self.assertAlmostEqual(
            float(detalle.iva),
            2184.00,
            places=2,
            msg="IVA incorrecto"
        )

        # Verificar total facturado
        self.assertAlmostEqual(
            float(detalle.total_facturado),
            16744.00,
            places=2,
            msg="Total facturado incorrecto"
        )

        # Verificar retención prima (1%)
        self.assertAlmostEqual(
            float(detalle.retencion_prima),
            140.00,
            places=2,
            msg="Retención prima incorrecta"
        )

        # Verificar retención IVA (100% del IVA)
        self.assertAlmostEqual(
            float(detalle.retencion_iva),
            2184.00,
            places=2,
            msg="Retención IVA incorrecta"
        )

        # Verificar valor por pagar
        expected_valor_pagar = 16744.00 - 140.00 - 2184.00
        self.assertAlmostEqual(
            float(detalle.valor_por_pagar),
            expected_valor_pagar,
            places=2,
            msg="Valor por pagar incorrecto"
        )

    def test_calculo_sin_gran_contribuyente(self):
        """
        Test Caso 3: Sin Gran Contribuyente
        Esperados:
        - retencion_prima = 0
        - retencion_iva = 0
        - valor_por_pagar = total_facturado
        """
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_no_gc,
            ramo=self.ramo_incendio,
            total_prima=Decimal('50000.00'),
            emision=Decimal('5.00'),
            suma_asegurada=Decimal('500000.00')
        )

        # Verificar que no hay retención de prima
        self.assertEqual(
            detalle.retencion_prima,
            Decimal('0.00'),
            msg="Retención prima debe ser 0 para no gran contribuyente"
        )

        # Verificar que no hay retención de IVA
        self.assertEqual(
            detalle.retencion_iva,
            Decimal('0.00'),
            msg="Retención IVA debe ser 0 para no gran contribuyente"
        )

        # Verificar que valor por pagar = total facturado
        self.assertEqual(
            detalle.valor_por_pagar,
            detalle.total_facturado,
            msg="Valor por pagar debe ser igual al total facturado"
        )

    def test_calculo_base_imponible_formula(self):
        """
        Test adicional: Verificar la fórmula de base imponible
        Base Imponible = Prima + Contribución Superintendencia + Seguro Campesino + Emisión
        """
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_gc,
            ramo=self.ramo_incendio,
            total_prima=Decimal('100000.00'),
            emision=Decimal('10.00'),
            suma_asegurada=Decimal('800000.00')
        )

        # Calcular manualmente
        contrib_super = Decimal('100000.00') * Decimal('0.035')  # 3,500
        seguro_camp = Decimal('100000.00') * Decimal('0.005')     # 500
        base_esperada = Decimal('100000.00') + contrib_super + seguro_camp + Decimal('10.00')

        self.assertAlmostEqual(
            float(detalle.base_imponible),
            float(base_esperada),
            places=2,
            msg="Base imponible no cumple con la fórmula esperada"
        )

    def test_calculo_iva_15_porciento(self):
        """
        Test adicional: Verificar que IVA sea exactamente 15% de base imponible
        """
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_no_gc,
            ramo=self.ramo_lucro,
            total_prima=Decimal('20000.00'),
            emision=Decimal('0.00'),
            suma_asegurada=Decimal('150000.00')
        )

        iva_esperado = detalle.base_imponible * Decimal('0.15')

        self.assertAlmostEqual(
            float(detalle.iva),
            float(iva_esperado),
            places=2,
            msg="IVA debe ser exactamente 15% de la base imponible"
        )

    def test_retencion_iva_100_porciento_gran_contribuyente(self):
        """
        Test adicional: Verificar que retención IVA sea 100% del IVA para gran contribuyente
        """
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_gc,
            ramo=self.ramo_incendio,
            total_prima=Decimal('75000.00'),
            emision=Decimal('7.50'),
            suma_asegurada=Decimal('600000.00')
        )

        self.assertEqual(
            detalle.retencion_iva,
            detalle.iva,
            msg="Retención IVA debe ser igual al IVA (100%) para gran contribuyente"
        )

    def test_retencion_prima_1_porciento_gran_contribuyente(self):
        """
        Test adicional: Verificar que retención prima sea 1% de la prima para gran contribuyente
        """
        prima = Decimal('85000.00')
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_gc,
            ramo=self.ramo_lucro,
            total_prima=prima,
            emision=Decimal('0.00'),
            suma_asegurada=Decimal('700000.00')
        )

        retencion_esperada = prima * Decimal('0.01')

        self.assertAlmostEqual(
            float(detalle.retencion_prima),
            float(retencion_esperada),
            places=2,
            msg="Retención prima debe ser 1% de la prima para gran contribuyente"
        )

    def test_valor_por_pagar_formula(self):
        """
        Test adicional: Verificar fórmula de valor por pagar
        Valor por Pagar = Total Facturado - Retención Prima - Retención IVA
        """
        detalle = DetallePolizaRamo.objects.create(
            poliza=self.poliza_gc,
            ramo=self.ramo_incendio,
            total_prima=Decimal('120000.00'),
            emision=Decimal('12.00'),
            suma_asegurada=Decimal('900000.00')
        )

        valor_esperado = (
            detalle.total_facturado -
            detalle.retencion_prima -
            detalle.retencion_iva
        )

        self.assertAlmostEqual(
            float(detalle.valor_por_pagar),
            float(valor_esperado),
            places=2,
            msg="Valor por pagar no cumple con la fórmula esperada"
        )
