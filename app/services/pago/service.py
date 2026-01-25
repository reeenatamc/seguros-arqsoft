"""
Servicio de Pagos.
Responsabilidad única: Gestión del ciclo de vida de pagos.
"""

from decimal import Decimal
from datetime import date
from typing import Optional

from django.db import transaction

from ..base import BaseService, ResultadoValidacion, ResultadoOperacion


class PagoService(BaseService):
    """
    Servicio para gestión de Pagos.
    
    Responsabilidades:
    - Validar montos de pagos
    - Crear, aprobar y eliminar pagos
    - Actualizar facturas relacionadas
    
    USO:
        from app.services.pago import PagoService
        
        resultado = PagoService.crear_pago(
            factura=factura,
            monto=Decimal('500'),
            fecha_pago=date.today(),
            metodo_pago='transferencia'
        )
    """
    
    @classmethod
    def validar_monto(
        cls,
        factura,
        monto: Decimal,
        pago_pk: Optional[int] = None
    ) -> ResultadoValidacion:
        """Valida que el monto del pago no exceda el saldo pendiente."""
        from app.models import Pago
        
        saldo = factura.saldo_pendiente
        
        if pago_pk:
            pago_anterior = Pago.objects.filter(pk=pago_pk).first()
            if pago_anterior and pago_anterior.estado == 'aprobado':
                saldo += pago_anterior.monto
        
        if monto > saldo + Decimal('0.01'):
            return ResultadoValidacion(
                es_valido=False,
                errores={'monto': f'El monto (${monto}) excede el saldo pendiente (${saldo}).'}
            )
        
        return ResultadoValidacion(es_valido=True)
    
    @classmethod
    @transaction.atomic
    def crear_pago(
        cls,
        factura,
        monto: Decimal,
        fecha_pago: date,
        metodo_pago: str,
        referencia: str = "",
        estado: str = 'pendiente',
        **kwargs
    ) -> ResultadoOperacion:
        """Crea un nuevo pago y actualiza la factura si está aprobado."""
        from app.models import Pago
        
        if estado == 'aprobado':
            validacion = cls.validar_monto(factura, monto)
            if not validacion.es_valido:
                return ResultadoOperacion.desde_validacion(validacion)
        
        try:
            pago = Pago(
                factura=factura,
                monto=monto,
                fecha_pago=fecha_pago,
                metodo_pago=metodo_pago,
                referencia=referencia,
                estado=estado,
                **kwargs
            )
            pago.save()
            
            if estado == 'aprobado':
                cls._actualizar_factura_por_pago(factura, fecha_pago)
            
            return ResultadoOperacion.exito(pago, "Pago registrado exitosamente")
            
        except Exception as e:
            return ResultadoOperacion.fallo(
                {'__all__': str(e)},
                f"Error al crear pago: {str(e)}"
            )
    
    @classmethod
    @transaction.atomic
    def aprobar_pago(cls, pago) -> ResultadoOperacion:
        """Aprueba un pago y actualiza la factura."""
        if pago.estado == 'aprobado':
            return ResultadoOperacion.exito(pago, "El pago ya está aprobado")
        
        validacion = cls.validar_monto(pago.factura, pago.monto, pago.pk)
        if not validacion.es_valido:
            return ResultadoOperacion.desde_validacion(validacion)
        
        try:
            pago.estado = 'aprobado'
            pago.save(update_fields=['estado'])
            
            cls._actualizar_factura_por_pago(pago.factura, pago.fecha_pago)
            
            return ResultadoOperacion.exito(pago, "Pago aprobado exitosamente")
            
        except Exception as e:
            return ResultadoOperacion.fallo(
                {'__all__': str(e)},
                f"Error al aprobar pago: {str(e)}"
            )
    
    @classmethod
    def _actualizar_factura_por_pago(cls, factura, fecha_pago: date) -> None:
        """Actualiza la factura después de un pago aprobado."""
        from app.models import Pago
        from ..factura import FacturaService
        
        primer_pago = Pago.objects.filter(
            factura=factura,
            estado='aprobado'
        ).order_by('fecha_pago').first()
        
        fecha_primer_pago = primer_pago.fecha_pago if primer_pago else None
        
        FacturaService.aplicar_calculos(factura, fecha_primer_pago)
        FacturaService.actualizar_estado(factura)
        
        factura.save(update_fields=[
            'contribucion_superintendencia',
            'contribucion_seguro_campesino',
            'descuento_pronto_pago',
            'monto_total',
            'estado',
        ])
    
    @classmethod
    @transaction.atomic
    def eliminar_pago(cls, pago) -> ResultadoOperacion:
        """Elimina un pago y recalcula la factura."""
        from app.models import Pago
        from ..factura import FacturaService
        
        factura = pago.factura
        era_aprobado = pago.estado == 'aprobado'
        
        try:
            pago.delete()
            
            if era_aprobado and factura:
                primer_pago = Pago.objects.filter(
                    factura=factura,
                    estado='aprobado'
                ).order_by('fecha_pago').first()
                
                fecha_primer_pago = primer_pago.fecha_pago if primer_pago else None
                
                FacturaService.aplicar_calculos(factura, fecha_primer_pago)
                FacturaService.actualizar_estado(factura)
                
                factura.save(update_fields=[
                    'contribucion_superintendencia',
                    'contribucion_seguro_campesino',
                    'descuento_pronto_pago',
                    'monto_total',
                    'estado',
                ])
            
            return ResultadoOperacion.exito(None, "Pago eliminado exitosamente")
            
        except Exception as e:
            return ResultadoOperacion.fallo(
                {'__all__': str(e)},
                f"Error al eliminar pago: {str(e)}"
            )
