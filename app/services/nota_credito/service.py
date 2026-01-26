"""

Servicio de Notas de Crédito.

Responsabilidad única: Gestión de notas de crédito sobre facturas.

"""

from decimal import Decimal

from typing import Optional

from django.db.models import Sum

from ..base import BaseService, ResultadoValidacion, ResultadoOperacion

class NotaCreditoService(BaseService):

    """

    Servicio para gestión de Notas de Crédito.

    Responsabilidades:

    - Validar que el monto no exceda el saldo de la factura

    USO:

        from app.services.nota_credito import NotaCreditoService

        validacion = NotaCreditoService.validar_monto(

            factura=factura,

            monto=Decimal('100')

        )

    """

    @classmethod
    def validar_monto(

        cls,

        factura,

        monto: Decimal,

        nota_pk: Optional[int] = None

    ) -> ResultadoValidacion:

        """Valida que el monto total de notas de crédito no exceda la factura."""

        from app.models import NotaCredito

        notas_existentes = NotaCredito.objects.filter(

            factura=factura,

            estado__in=['emitida', 'aplicada']

        )

        if nota_pk:

            notas_existentes = notas_existentes.exclude(pk=nota_pk)

        total_notas = notas_existentes.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        if total_notas + monto > factura.monto_total:

            return ResultadoValidacion(

                es_valido=False,

                errores={

                    'monto': 'El monto total de notas de crédito no puede exceder el monto de la factura.'

                }

            )

        return ResultadoValidacion(es_valido=True)
