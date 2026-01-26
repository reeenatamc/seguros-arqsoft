"""
Módulo de Servicios de Cálculo Financiero para el Sistema de Gestión de Seguros.

Este módulo centraliza toda la lógica de cálculo financiero del sistema, implementando
funciones puras y stateless que pueden ser utilizadas desde cualquier contexto:
vistas, APIs REST, tareas asíncronas (Celery), o scripts de migración.

Principios de Diseño:
    1. **Funciones Puras**: Los métodos no tienen efectos secundarios ni modifican
       estado. Reciben inputs y retornan outputs de forma determinista.
    2. **Stateless**: Los servicios no mantienen estado entre llamadas.
    3. **Configuración Dinámica**: Los parámetros financieros (tasas, porcentajes)
       se obtienen de ConfiguracionSistema, permitiendo ajustes sin redespliegue.
    4. **Inyección de Dependencias**: config_provider permite mockear configuración
       para testing aislado.

Servicios Disponibles:
    - FacturaCalculationService: Cálculos de facturas (contribuciones, IVA, totales)
    - DetalleRamoCalculationService: Cálculos de primas y derechos de emisión
    - PolizaCalculationService: Estados de póliza, vencimientos, deducibles

Fórmulas Implementadas:

    Contribuciones Legales::
        superintendencia = subtotal × 3.5%
        seguro_campesino = subtotal × 0.5%

    Prima de Seguro::
        total_prima = suma_asegurada × (tasa / 100)

    Base Imponible::
        base = prima + superintendencia + seguro_campesino + emision

    Monto Total Factura::
        total = subtotal + IVA + contribuciones - retenciones - descuentos

    Deducible Aplicable::
        deducible = max(fijo, monto × porcentaje, mínimo)

    Indemnización::
        indemnización = monto_siniestro - deducible - depreciación

Autor: Equipo de Desarrollo UTPL
Versión: 1.0.0
Última Actualización: Enero 2026

Example:
    Cálculo completo de factura para preview/validación::

        from app.services.calculations import FacturaCalculationService
        from decimal import Decimal
        from datetime import date, timedelta

        resultado = FacturaCalculationService.calcular_factura_completa(
            subtotal=Decimal('1000'),
            iva=Decimal('150'),
            fecha_emision=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=30),
        )
        # resultado = {
        #     'contribucion_superintendencia': Decimal('35.00'),
        #     'contribucion_seguro_campesino': Decimal('5.00'),
        #     'descuento_pronto_pago': Decimal('0.00'),
        #     'monto_total': Decimal('1190.00'),
        #     'estado': 'pendiente'
        # }

    Cálculo de prima para un detalle de ramo::

        from app.services.calculations import DetalleRamoCalculationService

        valores = DetalleRamoCalculationService.calcular_valores_detalle(
            suma_asegurada=Decimal('100000'),
            tasa=Decimal('2.5'),
            es_gran_contribuyente=True,
        )
        # valores contiene: prima, IVA, emisión, retenciones, valor_por_pagar

Note:
    Las tablas de tasas de emisión son configurables desde el panel de
    administración en ConfiguracionSistema.TABLA_TASAS_EMISION.
"""




from decimal import Decimal

from datetime import timedelta

from typing import Optional, Dict, Any

from django.utils import timezone





class FacturaCalculationService:

    """

    Servicio para cálculos de facturas.

    Desacopla la lógica de negocio del método save().

    """

    

    @staticmethod

    def calcular_contribuciones(subtotal: Decimal, config_provider=None) -> Dict[str, Decimal]:

        """

        Calcula las contribuciones de superintendencia y seguro campesino.

        

        Args:

            subtotal: Monto base de la factura

            config_provider: Función para obtener configuración (opcional)

            

        Returns:

            Dict con 'superintendencia' y 'seguro_campesino'

        """

        from app.models import ConfiguracionSistema

        

        if config_provider is None:

            config_provider = ConfiguracionSistema.get_config

        

        pct_super = config_provider('PORCENTAJE_SUPERINTENDENCIA', Decimal('0.035'))

        pct_campesino = config_provider('PORCENTAJE_SEGURO_CAMPESINO', Decimal('0.005'))

        

        return {

            'superintendencia': subtotal * pct_super,

            'seguro_campesino': subtotal * pct_campesino,

        }

    

    @staticmethod

    def calcular_descuento_pronto_pago(

        subtotal: Decimal,

        fecha_emision,

        fecha_primer_pago: Optional[Any] = None,

        config_provider=None

    ) -> Decimal:

        """

        Calcula el descuento por pronto pago.

        

        Args:

            subtotal: Monto base

            fecha_emision: Fecha de emisión de la factura

            fecha_primer_pago: Fecha del primer pago aprobado (opcional)

            config_provider: Función para obtener configuración

            

        Returns:

            Monto del descuento

        """

        from app.models import ConfiguracionSistema

        

        if config_provider is None:

            config_provider = ConfiguracionSistema.get_config

        

        if not fecha_emision or not fecha_primer_pago:

            return Decimal('0.00')

        

        dias_limite = config_provider('DIAS_LIMITE_DESCUENTO_PRONTO_PAGO', 20)

        pct_descuento = config_provider('PORCENTAJE_DESCUENTO_PRONTO_PAGO', Decimal('0.05'))

        

        fecha_limite = fecha_emision + timedelta(days=dias_limite)

        

        if fecha_primer_pago <= fecha_limite:

            return subtotal * pct_descuento

        

        return Decimal('0.00')

    

    @staticmethod

    def calcular_monto_total(

        subtotal: Decimal,

        iva: Decimal,

        contribucion_super: Decimal,

        contribucion_campesino: Decimal,

        retenciones: Decimal = Decimal('0.00'),

        descuento: Decimal = Decimal('0.00')

    ) -> Decimal:

        """

        Calcula el monto total de la factura.

        

        Returns:

            Monto total (nunca negativo)

        """

        total = (

            subtotal +

            iva +

            contribucion_super +

            contribucion_campesino -

            retenciones -

            descuento

        )

        return max(total, Decimal('0.00'))

    

    @staticmethod

    def determinar_estado_factura(

        monto_total: Decimal,

        total_pagado: Decimal,

        fecha_vencimiento,

        fecha_actual=None

    ) -> str:

        """

        Determina el estado de una factura basándose en pagos.

        

        Returns:

            Estado: 'pagada', 'parcial', 'vencida', 'pendiente'

        """

        if fecha_actual is None:

            fecha_actual = timezone.now().date()

        

        if total_pagado >= monto_total:

            return 'pagada'

        elif total_pagado > Decimal('0.00'):

            return 'parcial'

        elif fecha_actual > fecha_vencimiento:

            return 'vencida'

        else:

            return 'pendiente'

    

    @classmethod

    def calcular_factura_completa(

        cls,

        subtotal: Decimal,

        iva: Decimal,

        fecha_emision=None,

        fecha_vencimiento=None,

        fecha_primer_pago=None,

        retenciones: Decimal = Decimal('0.00'),

        total_pagado: Decimal = Decimal('0.00')

    ) -> Dict[str, Any]:

        """

        Calcula todos los valores de una factura en una sola llamada.

        Útil para APIs y operaciones batch.

        

        Returns:

            Dict con todos los valores calculados

        """

        contribuciones = cls.calcular_contribuciones(subtotal)

        

        descuento = Decimal('0.00')

        if fecha_emision and fecha_primer_pago:

            descuento = cls.calcular_descuento_pronto_pago(

                subtotal, fecha_emision, fecha_primer_pago

            )

        

        monto_total = cls.calcular_monto_total(

            subtotal=subtotal,

            iva=iva,

            contribucion_super=contribuciones['superintendencia'],

            contribucion_campesino=contribuciones['seguro_campesino'],

            retenciones=retenciones,

            descuento=descuento

        )

        

        estado = 'pendiente'

        if fecha_vencimiento:

            estado = cls.determinar_estado_factura(

                monto_total, total_pagado, fecha_vencimiento

            )

        

        return {

            'contribucion_superintendencia': contribuciones['superintendencia'],

            'contribucion_seguro_campesino': contribuciones['seguro_campesino'],

            'descuento_pronto_pago': descuento,

            'monto_total': monto_total,

            'estado': estado,

        }





class DetalleRamoCalculationService:

    """

    Servicio para cálculos de detalles de ramo/póliza.

    Mueve la lógica de derechos de emisión a configuración dinámica.

    """

    

    @staticmethod

    def get_tabla_tasas_emision(config_provider=None) -> list:

        """

        Obtiene la tabla de tasas de emisión desde configuración.

        

        Returns:

            Lista de tuplas (limite_superior, valor_emision)

        """

        from app.models import ConfiguracionSistema

        

        if config_provider is None:

            config_provider = ConfiguracionSistema.get_config

        

        # Intentar obtener desde configuración

        tabla_config = config_provider('TABLA_TASAS_EMISION', None)

        

        if tabla_config and isinstance(tabla_config, list):

            return tabla_config

        

        # Valores por defecto (pueden ser editados en admin)

        return [

            {'limite': 250, 'tasa': '0.50'},

            {'limite': 500, 'tasa': '1.00'},

            {'limite': 1000, 'tasa': '3.00'},

            {'limite': 2000, 'tasa': '5.00'},

            {'limite': 4000, 'tasa': '7.00'},

            {'limite': None, 'tasa': '9.00'},  # None = sin límite

        ]

    

    @classmethod

    def calcular_derechos_emision(cls, valor_prima: Decimal, config_provider=None) -> Decimal:

        """

        Calcula los derechos de emisión según tabla escalonada configurable.

        

        Args:

            valor_prima: Prima sobre la que calcular

            config_provider: Función para obtener configuración

            

        Returns:

            Valor de derechos de emisión

        """

        tabla = cls.get_tabla_tasas_emision(config_provider)

        

        for rango in tabla:

            limite = rango.get('limite')

            tasa = Decimal(str(rango.get('tasa', '0')))

            

            if limite is None or valor_prima <= Decimal(str(limite)):

                return tasa

        

        # Fallback al último valor si no hay match

        return Decimal(str(tabla[-1].get('tasa', '9.00')))

    

    @classmethod

    def calcular_valores_detalle(

        cls,

        suma_asegurada: Decimal,

        tasa: Decimal,

        es_gran_contribuyente: bool = False,

        config_provider=None

    ) -> Dict[str, Decimal]:

        """

        Calcula todos los valores de un detalle de ramo.

        

        Args:

            suma_asegurada: Suma asegurada del bien

            tasa: Tasa aplicable

            es_gran_contribuyente: Si aplican retenciones

            config_provider: Función para obtener configuración

            

        Returns:

            Dict con todos los valores calculados

        """

        from app.models import ConfiguracionSistema

        

        if config_provider is None:

            config_provider = ConfiguracionSistema.get_config

        

        # Calcular prima

        total_prima = suma_asegurada * (tasa / Decimal('100'))

        

        # Obtener porcentajes de configuración

        pct_super = config_provider('PORCENTAJE_SUPERINTENDENCIA', Decimal('0.035'))

        pct_campesino = config_provider('PORCENTAJE_SEGURO_CAMPESINO', Decimal('0.005'))

        pct_iva = config_provider('PORCENTAJE_IVA', Decimal('0.15'))

        

        # Calcular contribuciones

        contrib_super = total_prima * pct_super

        seguro_campesino = total_prima * pct_campesino

        

        # Calcular derechos de emisión

        emision = cls.calcular_derechos_emision(total_prima, config_provider)

        

        # Base imponible

        base_imponible = total_prima + contrib_super + seguro_campesino + emision

        

        # IVA

        iva = base_imponible * pct_iva

        

        # Total facturado

        total_facturado = base_imponible + iva

        

        # Retenciones (solo para grandes contribuyentes)

        if es_gran_contribuyente:

            retencion_prima = total_prima * Decimal('0.01')

            retencion_iva = iva  # 100% del IVA

        else:

            retencion_prima = Decimal('0.00')

            retencion_iva = Decimal('0.00')

        

        # Valor por pagar

        valor_por_pagar = total_facturado - retencion_prima - retencion_iva

        

        return {

            'total_prima': total_prima,

            'contribucion_superintendencia': contrib_super,

            'seguro_campesino': seguro_campesino,

            'emision': emision,

            'base_imponible': base_imponible,

            'iva': iva,

            'total_facturado': total_facturado,

            'retencion_prima': retencion_prima,

            'retencion_iva': retencion_iva,

            'valor_por_pagar': valor_por_pagar,

        }





class PolizaCalculationService:

    """

    Servicio para cálculos y estado de pólizas.

    """

    

    @staticmethod

    def determinar_estado_poliza(

        fecha_inicio,

        fecha_fin,

        fecha_actual=None,

        dias_alerta: int = 30,

        estado_actual: str = None

    ) -> str:

        """

        Determina el estado de una póliza basándose en fechas.

        

        Args:

            fecha_inicio: Fecha de inicio de vigencia

            fecha_fin: Fecha de fin de vigencia

            fecha_actual: Fecha de referencia (default: hoy)

            dias_alerta: Días antes de vencimiento para alerta

            estado_actual: Estado actual (para preservar 'cancelada')

            

        Returns:

            Estado: 'vencida', 'por_vencer', 'vigente'

        """

        if fecha_actual is None:

            fecha_actual = timezone.now().date()

        

        if not fecha_inicio or not fecha_fin:

            return 'vigente'

        

        if fecha_fin < fecha_actual:

            return 'vencida'

        elif fecha_inicio <= fecha_actual and fecha_fin <= fecha_actual + timedelta(days=dias_alerta):

            return 'por_vencer'

        elif fecha_inicio <= fecha_actual <= fecha_fin:

            return 'vigente'

        elif fecha_actual < fecha_inicio and estado_actual != 'cancelada':

            return 'vigente'

        

        return estado_actual or 'vigente'

    

    @staticmethod

    def calcular_dias_para_vencer(fecha_fin, fecha_actual=None) -> int:

        """Calcula los días restantes hasta el vencimiento."""

        if fecha_actual is None:

            fecha_actual = timezone.now().date()

        

        if not fecha_fin:

            return 0

        

        return (fecha_fin - fecha_actual).days

    

    @staticmethod

    def calcular_deducible_aplicable(

        monto_siniestro: Decimal,

        deducible_fijo: Decimal = Decimal('0.00'),

        porcentaje_deducible: Decimal = Decimal('0.00'),

        deducible_minimo: Decimal = Decimal('0.00')

    ) -> Decimal:

        """

        Calcula el deducible aplicable para un monto de siniestro dado.

        

        La lógica es: el mayor entre el deducible fijo y el calculado por porcentaje,

        respetando el mínimo establecido.

        

        Args:

            monto_siniestro: Monto estimado del siniestro

            deducible_fijo: Deducible fijo de la póliza

            porcentaje_deducible: Porcentaje de deducible (0-100)

            deducible_minimo: Deducible mínimo aplicable

            

        Returns:

            El deducible aplicable

        """

        # Calcular deducible por porcentaje si aplica

        if porcentaje_deducible > 0:

            deducible_porcentaje = (porcentaje_deducible / 100) * monto_siniestro

            # Aplicar mínimo al porcentaje si existe

            if deducible_minimo > 0:

                deducible_porcentaje = max(deducible_porcentaje, deducible_minimo)

            # Retornar el mayor entre fijo y porcentaje

            return max(deducible_fijo, deducible_porcentaje)

        

        # Si no hay porcentaje, usar el deducible fijo

        return deducible_fijo

    

    @staticmethod

    def calcular_monto_indemnizacion(

        monto_siniestro: Decimal,

        deducible: Decimal,

        depreciacion: Decimal = Decimal('0.00')

    ) -> Decimal:

        """

        Calcula el monto a indemnizar después de deducciones.

        

        Args:

            monto_siniestro: Monto estimado del siniestro

            deducible: Deducible aplicable

            depreciacion: Depreciación del bien

            

        Returns:

            Monto a indemnizar (mínimo 0)

        """

        resultado = monto_siniestro - deducible - depreciacion

        return max(resultado, Decimal('0.00'))

