"""

Servicio de Facturación.

Responsabilidad única: Gestión del ciclo de vida de facturas.

"""

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Sum

from ..base import BaseService, ResultadoOperacion, ResultadoValidacion


class FacturaService(BaseService):
    """

    Servicio para gestión de Facturas.

    Responsabilidades:

    - Crear y actualizar facturas

    - Orquestar cálculos (delegados a FacturaCalculationService)

    - Gestionar estados

    USO:

        from app.services.factura import FacturaService

        # Crear factura

        resultado = FacturaService.crear_factura(

            poliza=poliza,

            numero_factura="F-001",

            subtotal=Decimal('1000'),

            ...

        )

        # Actualizar

        resultado = FacturaService.actualizar_factura(factura, subtotal=Decimal('1500'))

    """

    # =========================================================================

    # DELEGACIÓN A CALCULADORA (DRY)

    # =========================================================================

    @staticmethod
    def calcular_contribuciones(subtotal: Decimal):
        """Delega a FacturaCalculationService."""

        from ..calculations import FacturaCalculationService

        resultado = FacturaCalculationService.calcular_contribuciones(subtotal)

        return (resultado["superintendencia"], resultado["seguro_campesino"])

    @staticmethod
    def calcular_descuento_pronto_pago(subtotal: Decimal, fecha_emision, fecha_primer_pago=None) -> Decimal:
        """Delega a FacturaCalculationService."""

        from ..calculations import FacturaCalculationService

        return FacturaCalculationService.calcular_descuento_pronto_pago(subtotal, fecha_emision, fecha_primer_pago)

    @staticmethod
    def calcular_monto_total(
        subtotal: Decimal,
        iva: Decimal,
        contribucion_super: Decimal,
        contribucion_campesino: Decimal,
        retenciones: Decimal = Decimal("0.00"),
        descuento: Decimal = Decimal("0.00"),
    ) -> Decimal:
        """Delega a FacturaCalculationService."""

        from ..calculations import FacturaCalculationService

        return FacturaCalculationService.calcular_monto_total(
            subtotal, iva, contribucion_super, contribucion_campesino, retenciones, descuento
        )

    @staticmethod
    def determinar_estado(monto_total: Decimal, total_pagado: Decimal, fecha_vencimiento) -> str:
        """Delega a FacturaCalculationService."""

        from ..calculations import FacturaCalculationService

        return FacturaCalculationService.determinar_estado_factura(monto_total, total_pagado, fecha_vencimiento)

    # =========================================================================

    # OPERACIONES DE DOMINIO

    # =========================================================================

    @classmethod
    def aplicar_calculos(cls, factura, fecha_primer_pago=None) -> None:
        """

        Aplica todos los cálculos a una instancia de Factura (sin guardar).

        """

        from ..calculations import FacturaCalculationService

        resultado = FacturaCalculationService.calcular_factura_completa(
            subtotal=factura.subtotal,
            iva=factura.iva,
            fecha_emision=factura.fecha_emision,
            fecha_vencimiento=factura.fecha_vencimiento,
            fecha_primer_pago=fecha_primer_pago,
            retenciones=factura.retenciones or Decimal("0.00"),
        )

        factura.contribucion_superintendencia = resultado["contribucion_superintendencia"]

        factura.contribucion_seguro_campesino = resultado["contribucion_seguro_campesino"]

        factura.descuento_pronto_pago = resultado["descuento_pronto_pago"]

        factura.monto_total = resultado["monto_total"]

    @classmethod
    def actualizar_estado(cls, factura) -> None:
        """Actualiza el estado de la factura basándose en pagos."""

        from app.models import Pago

        total_pagado = Pago.objects.filter(factura=factura, estado="aprobado").aggregate(total=Sum("monto"))[
            "total"
        ] or Decimal("0.00")

        factura.estado = cls.determinar_estado(factura.monto_total, total_pagado, factura.fecha_vencimiento)

    @classmethod
    @transaction.atomic
    def crear_factura(
        cls,
        poliza,
        numero_factura: str,
        subtotal: Decimal,
        iva: Decimal,
        fecha_emision: date,
        fecha_vencimiento: date,
        **kwargs,
    ) -> ResultadoOperacion:
        """Crea una nueva factura con todos los cálculos aplicados."""

        from app.models import Factura

        try:

            factura = Factura(
                poliza=poliza,
                numero_factura=numero_factura,
                subtotal=subtotal,
                iva=iva,
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
                **kwargs,
            )

            cls.aplicar_calculos(factura)

            factura.save()

            return ResultadoOperacion.exito(factura, "Factura creada exitosamente")

        except Exception as e:

            return ResultadoOperacion.fallo({"__all__": str(e)}, f"Error al crear factura: {str(e)}")

    @classmethod
    @transaction.atomic
    def actualizar_factura(cls, factura, **campos) -> ResultadoOperacion:
        """Actualiza una factura existente recalculando valores."""

        try:

            for campo, valor in campos.items():

                if hasattr(factura, campo):

                    setattr(factura, campo, valor)

            from app.models import Pago

            primer_pago = Pago.objects.filter(factura=factura, estado="aprobado").order_by("fecha_pago").first()

            fecha_primer_pago = primer_pago.fecha_pago if primer_pago else None

            cls.aplicar_calculos(factura, fecha_primer_pago)

            cls.actualizar_estado(factura)

            factura.save()

            return ResultadoOperacion.exito(factura, "Factura actualizada exitosamente")

        except Exception as e:

            return ResultadoOperacion.fallo({"__all__": str(e)}, f"Error al actualizar factura: {str(e)}")
