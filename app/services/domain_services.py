"""
Servicios de Dominio (Domain Services).
Orquestan la lógica de negocio para crear, actualizar y validar entidades.

FILOSOFÍA:
- Los modelos son "tontos" (solo datos y relaciones).
- Los servicios contienen TODA la lógica de negocio.
- Facilita testing, reutilización desde APIs/Celery, y mantiene el código limpio.

USO:
    # En lugar de:
    factura = Factura(subtotal=1000, iva=150, ...)
    factura.save()  # <-- lógica oculta en save()
    
    # Usar:
    from app.services.domain_services import FacturaService
    factura = FacturaService.crear_factura(subtotal=1000, iva=150, ...)
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone


# ==============================================================================
# DATA CLASSES para resultados estructurados
# ==============================================================================

@dataclass
class ResultadoValidacion:
    """Resultado de una validación de negocio."""
    es_valido: bool
    errores: Dict[str, str] = None
    
    def __post_init__(self):
        if self.errores is None:
            self.errores = {}


@dataclass
class ResultadoOperacion:
    """Resultado de una operación de servicio."""
    exitoso: bool
    objeto: Any = None
    errores: Dict[str, str] = None
    mensaje: str = ""
    
    def __post_init__(self):
        if self.errores is None:
            self.errores = {}


# ==============================================================================
# FACTURA SERVICE
# ==============================================================================

class FacturaService:
    """
    Servicio para gestión de Facturas.
    Centraliza la lógica de cálculos, validaciones y actualizaciones.
    """
    
    @staticmethod
    def _get_config(clave: str, default: Any) -> Any:
        """Obtiene configuración del sistema."""
        from app.models import ConfiguracionSistema
        return ConfiguracionSistema.get_config(clave, default)
    
    @classmethod
    def calcular_contribuciones(cls, subtotal: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Calcula contribuciones de superintendencia y seguro campesino.
        
        Returns:
            Tuple (contribucion_superintendencia, contribucion_seguro_campesino)
        """
        pct_super = cls._get_config('PORCENTAJE_SUPERINTENDENCIA', Decimal('0.035'))
        pct_campesino = cls._get_config('PORCENTAJE_SEGURO_CAMPESINO', Decimal('0.005'))
        
        return (
            subtotal * pct_super,
            subtotal * pct_campesino
        )
    
    @classmethod
    def calcular_descuento_pronto_pago(
        cls,
        subtotal: Decimal,
        fecha_emision: date,
        fecha_primer_pago: Optional[date] = None
    ) -> Decimal:
        """Calcula el descuento por pronto pago si aplica."""
        if not fecha_emision or not fecha_primer_pago:
            return Decimal('0.00')
        
        dias_limite = cls._get_config('DIAS_LIMITE_DESCUENTO_PRONTO_PAGO', 20)
        pct_descuento = cls._get_config('PORCENTAJE_DESCUENTO_PRONTO_PAGO', Decimal('0.05'))
        
        fecha_limite = fecha_emision + timedelta(days=dias_limite)
        
        if fecha_primer_pago <= fecha_limite:
            return subtotal * pct_descuento
        
        return Decimal('0.00')
    
    @classmethod
    def calcular_monto_total(
        cls,
        subtotal: Decimal,
        iva: Decimal,
        contribucion_super: Decimal,
        contribucion_campesino: Decimal,
        retenciones: Decimal = Decimal('0.00'),
        descuento: Decimal = Decimal('0.00')
    ) -> Decimal:
        """Calcula el monto total de la factura."""
        total = (
            subtotal +
            iva +
            contribucion_super +
            contribucion_campesino -
            retenciones -
            descuento
        )
        return max(total, Decimal('0.00'))
    
    @classmethod
    def determinar_estado(
        cls,
        monto_total: Decimal,
        total_pagado: Decimal,
        fecha_vencimiento: date
    ) -> str:
        """Determina el estado de la factura según pagos y vencimiento."""
        hoy = timezone.now().date()
        
        if total_pagado >= monto_total:
            return 'pagada'
        elif total_pagado > Decimal('0.00'):
            return 'parcial'
        elif hoy > fecha_vencimiento:
            return 'vencida'
        else:
            return 'pendiente'
    
    @classmethod
    def aplicar_calculos(cls, factura, fecha_primer_pago: Optional[date] = None) -> None:
        """
        Aplica todos los cálculos a una instancia de Factura (sin guardar).
        
        Args:
            factura: Instancia de Factura
            fecha_primer_pago: Fecha del primer pago aprobado (opcional)
        """
        # Calcular contribuciones
        contrib_super, contrib_campesino = cls.calcular_contribuciones(factura.subtotal)
        factura.contribucion_superintendencia = contrib_super
        factura.contribucion_seguro_campesino = contrib_campesino
        
        # Calcular descuento pronto pago
        factura.descuento_pronto_pago = cls.calcular_descuento_pronto_pago(
            factura.subtotal,
            factura.fecha_emision,
            fecha_primer_pago
        )
        
        # Calcular monto total
        factura.monto_total = cls.calcular_monto_total(
            subtotal=factura.subtotal,
            iva=factura.iva,
            contribucion_super=factura.contribucion_superintendencia,
            contribucion_campesino=factura.contribucion_seguro_campesino,
            retenciones=factura.retenciones or Decimal('0.00'),
            descuento=factura.descuento_pronto_pago
        )
    
    @classmethod
    def actualizar_estado(cls, factura) -> None:
        """Actualiza el estado de la factura basándose en pagos."""
        from app.models import Pago
        
        total_pagado = Pago.objects.filter(
            factura=factura,
            estado='aprobado'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        
        factura.estado = cls.determinar_estado(
            factura.monto_total,
            total_pagado,
            factura.fecha_vencimiento
        )
    
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
        **kwargs
    ) -> ResultadoOperacion:
        """
        Crea una nueva factura con todos los cálculos aplicados.
        
        Returns:
            ResultadoOperacion con la factura creada o errores
        """
        from app.models import Factura
        
        try:
            factura = Factura(
                poliza=poliza,
                numero_factura=numero_factura,
                subtotal=subtotal,
                iva=iva,
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
                **kwargs
            )
            
            # Aplicar cálculos
            cls.aplicar_calculos(factura)
            
            # Guardar (modelo "tonto" - solo persiste)
            factura.save()
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=factura,
                mensaje="Factura creada exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al crear factura: {str(e)}"
            )
    
    @classmethod
    @transaction.atomic
    def actualizar_factura(cls, factura, **campos) -> ResultadoOperacion:
        """
        Actualiza una factura existente recalculando valores.
        
        Args:
            factura: Instancia de Factura a actualizar
            **campos: Campos a actualizar
            
        Returns:
            ResultadoOperacion
        """
        try:
            # Actualizar campos
            for campo, valor in campos.items():
                if hasattr(factura, campo):
                    setattr(factura, campo, valor)
            
            # Obtener fecha de primer pago si existe
            from app.models import Pago
            primer_pago = Pago.objects.filter(
                factura=factura,
                estado='aprobado'
            ).order_by('fecha_pago').first()
            
            fecha_primer_pago = primer_pago.fecha_pago if primer_pago else None
            
            # Recalcular
            cls.aplicar_calculos(factura, fecha_primer_pago)
            cls.actualizar_estado(factura)
            
            # Guardar
            factura.save()
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=factura,
                mensaje="Factura actualizada exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al actualizar factura: {str(e)}"
            )


# ==============================================================================
# PAGO SERVICE
# ==============================================================================

class PagoService:
    """
    Servicio para gestión de Pagos.
    Maneja validaciones, creación y actualización de facturas relacionadas.
    """
    
    @classmethod
    def validar_monto(cls, factura, monto: Decimal, pago_pk: Optional[int] = None) -> ResultadoValidacion:
        """
        Valida que el monto del pago no exceda el saldo pendiente.
        
        Args:
            factura: Factura asociada
            monto: Monto a validar
            pago_pk: PK del pago (si es actualización)
            
        Returns:
            ResultadoValidacion
        """
        from app.models import Pago
        
        saldo = factura.saldo_pendiente
        
        # Si es actualización, sumar el monto anterior al saldo
        if pago_pk:
            pago_anterior = Pago.objects.filter(pk=pago_pk).first()
            if pago_anterior and pago_anterior.estado == 'aprobado':
                saldo += pago_anterior.monto
        
        # Margen de tolerancia de 1 centavo
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
        """
        Crea un nuevo pago y actualiza la factura si está aprobado.
        
        Returns:
            ResultadoOperacion con el pago creado o errores
        """
        from app.models import Pago
        
        # Validar monto
        if estado == 'aprobado':
            validacion = cls.validar_monto(factura, monto)
            if not validacion.es_valido:
                return ResultadoOperacion(
                    exitoso=False,
                    errores=validacion.errores,
                    mensaje="Validación fallida"
                )
        
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
            
            # Actualizar factura si el pago está aprobado
            if estado == 'aprobado':
                cls._actualizar_factura_por_pago(factura, fecha_pago)
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=pago,
                mensaje="Pago registrado exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al crear pago: {str(e)}"
            )
    
    @classmethod
    @transaction.atomic
    def aprobar_pago(cls, pago) -> ResultadoOperacion:
        """Aprueba un pago y actualiza la factura."""
        if pago.estado == 'aprobado':
            return ResultadoOperacion(
                exitoso=True,
                objeto=pago,
                mensaje="El pago ya está aprobado"
            )
        
        # Validar monto
        validacion = cls.validar_monto(pago.factura, pago.monto, pago.pk)
        if not validacion.es_valido:
            return ResultadoOperacion(
                exitoso=False,
                errores=validacion.errores,
                mensaje="Validación fallida"
            )
        
        try:
            pago.estado = 'aprobado'
            pago.save(update_fields=['estado'])
            
            cls._actualizar_factura_por_pago(pago.factura, pago.fecha_pago)
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=pago,
                mensaje="Pago aprobado exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al aprobar pago: {str(e)}"
            )
    
    @classmethod
    def _actualizar_factura_por_pago(cls, factura, fecha_pago: date) -> None:
        """Actualiza la factura después de un pago aprobado."""
        from app.models import Pago
        
        # Obtener fecha del primer pago
        primer_pago = Pago.objects.filter(
            factura=factura,
            estado='aprobado'
        ).order_by('fecha_pago').first()
        
        fecha_primer_pago = primer_pago.fecha_pago if primer_pago else None
        
        # Recalcular factura
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
        factura = pago.factura
        era_aprobado = pago.estado == 'aprobado'
        
        try:
            pago.delete()
            
            # Recalcular factura si el pago estaba aprobado
            if era_aprobado and factura:
                from app.models import Pago
                
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
            
            return ResultadoOperacion(
                exitoso=True,
                mensaje="Pago eliminado exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al eliminar pago: {str(e)}"
            )


# ==============================================================================
# POLIZA SERVICE
# ==============================================================================

class PolizaService:
    """
    Servicio para gestión de Pólizas.
    Maneja validaciones y actualización de estados.
    """
    
    @classmethod
    def _get_config(cls, clave: str, default: Any) -> Any:
        from app.models import ConfiguracionSistema
        return ConfiguracionSistema.get_config(clave, default)
    
    @classmethod
    def validar_fechas(
        cls,
        fecha_inicio: date,
        fecha_fin: date,
        numero_poliza: str,
        poliza_pk: Optional[int] = None
    ) -> ResultadoValidacion:
        """
        Valida fechas y evita duplicidad de pólizas con fechas superpuestas.
        
        Returns:
            ResultadoValidacion
        """
        from app.models import Poliza
        
        errores = {}
        
        # Validar que fecha_inicio sea anterior a fecha_fin
        if fecha_inicio >= fecha_fin:
            errores['fecha_fin'] = 'La fecha de fin debe ser posterior a la fecha de inicio.'
        
        # Buscar pólizas superpuestas
        query = Q(numero_poliza=numero_poliza) & (
            Q(fecha_inicio__lte=fecha_fin) &
            Q(fecha_fin__gte=fecha_inicio)
        )
        
        if poliza_pk:
            query &= ~Q(pk=poliza_pk)
        
        polizas_superpuestas = Poliza.objects.filter(query)
        
        if polizas_superpuestas.exists():
            primera = polizas_superpuestas.first()
            errores['fecha_inicio'] = (
                f'Ya existe una póliza con el número "{numero_poliza}" '
                f'que se superpone con las fechas indicadas '
                f'({primera.fecha_inicio} - {primera.fecha_fin}).'
            )
        
        if errores:
            return ResultadoValidacion(es_valido=False, errores=errores)
        
        return ResultadoValidacion(es_valido=True)
    
    @classmethod
    def validar_corredor_compania(
        cls,
        compania_aseguradora,
        corredor
    ) -> ResultadoValidacion:
        """
        Valida que el corredor pertenezca a la compañía aseguradora.
        
        Returns:
            ResultadoValidacion
        """
        if corredor and compania_aseguradora:
            if corredor.compania_aseguradora_id != compania_aseguradora.pk:
                return ResultadoValidacion(
                    es_valido=False,
                    errores={
                        'corredor': (
                            f'El corredor "{corredor.nombre}" no está asociado '
                            f'a la compañía "{compania_aseguradora.nombre}".'
                        )
                    }
                )
        
        return ResultadoValidacion(es_valido=True)
    
    @classmethod
    def determinar_estado(
        cls,
        fecha_inicio: date,
        fecha_fin: date,
        estado_actual: str = None
    ) -> str:
        """Determina el estado de la póliza según fechas."""
        hoy = timezone.now().date()
        dias_alerta = cls._get_config('DIAS_ALERTA_VENCIMIENTO_POLIZA', 30)
        
        if fecha_fin < hoy:
            return 'vencida'
        elif fecha_inicio <= hoy and fecha_fin <= hoy + timedelta(days=dias_alerta):
            return 'por_vencer'
        elif fecha_inicio <= hoy <= fecha_fin:
            return 'vigente'
        elif hoy < fecha_inicio and estado_actual != 'cancelada':
            return 'vigente'
        
        return estado_actual or 'vigente'
    
    @classmethod
    def actualizar_estado(cls, poliza) -> None:
        """Actualiza el estado de la póliza basándose en fechas."""
        if poliza.fecha_inicio and poliza.fecha_fin:
            poliza.estado = cls.determinar_estado(
                poliza.fecha_inicio,
                poliza.fecha_fin,
                poliza.estado
            )
    
    @classmethod
    @transaction.atomic
    def crear_poliza(
        cls,
        numero_poliza: str,
        compania_aseguradora,
        grupo_ramo,
        fecha_inicio: date,
        fecha_fin: date,
        corredor=None,
        **kwargs
    ) -> ResultadoOperacion:
        """
        Crea una nueva póliza con validaciones de negocio.
        
        Returns:
            ResultadoOperacion con la póliza creada o errores
        """
        from app.models import Poliza
        
        # Validar fechas
        val_fechas = cls.validar_fechas(fecha_inicio, fecha_fin, numero_poliza)
        if not val_fechas.es_valido:
            return ResultadoOperacion(
                exitoso=False,
                errores=val_fechas.errores,
                mensaje="Error de validación en fechas"
            )
        
        # Validar corredor-compañía
        val_corredor = cls.validar_corredor_compania(compania_aseguradora, corredor)
        if not val_corredor.es_valido:
            return ResultadoOperacion(
                exitoso=False,
                errores=val_corredor.errores,
                mensaje="Error de validación en corredor"
            )
        
        try:
            poliza = Poliza(
                numero_poliza=numero_poliza,
                compania_aseguradora=compania_aseguradora,
                grupo_ramo=grupo_ramo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                corredor=corredor,
                **kwargs
            )
            
            # Determinar estado inicial
            cls.actualizar_estado(poliza)
            
            poliza.save()
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=poliza,
                mensaje="Póliza creada exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al crear póliza: {str(e)}"
            )
    
    @classmethod
    @transaction.atomic
    def actualizar_poliza(cls, poliza, **campos) -> ResultadoOperacion:
        """
        Actualiza una póliza existente con validaciones.
        
        Args:
            poliza: Instancia de Poliza
            **campos: Campos a actualizar
            
        Returns:
            ResultadoOperacion
        """
        try:
            # Actualizar campos
            for campo, valor in campos.items():
                if hasattr(poliza, campo):
                    setattr(poliza, campo, valor)
            
            # Validar fechas
            val_fechas = cls.validar_fechas(
                poliza.fecha_inicio,
                poliza.fecha_fin,
                poliza.numero_poliza,
                poliza.pk
            )
            if not val_fechas.es_valido:
                return ResultadoOperacion(
                    exitoso=False,
                    errores=val_fechas.errores,
                    mensaje="Error de validación en fechas"
                )
            
            # Validar corredor
            val_corredor = cls.validar_corredor_compania(
                poliza.compania_aseguradora,
                poliza.corredor
            )
            if not val_corredor.es_valido:
                return ResultadoOperacion(
                    exitoso=False,
                    errores=val_corredor.errores,
                    mensaje="Error de validación en corredor"
                )
            
            # Actualizar estado
            cls.actualizar_estado(poliza)
            
            poliza.save()
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=poliza,
                mensaje="Póliza actualizada exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al actualizar póliza: {str(e)}"
            )


# ==============================================================================
# SINIESTRO SERVICE
# ==============================================================================

class SiniestroService:
    """
    Servicio para gestión de Siniestros.
    Sincroniza campos legacy y valida coherencia con póliza.
    """
    
    @classmethod
    def sincronizar_desde_bien_asegurado(cls, siniestro) -> None:
        """
        Sincroniza los campos legacy del siniestro desde el bien asegurado.
        
        Args:
            siniestro: Instancia de Siniestro
        """
        if siniestro.bien_asegurado_id:
            bien = siniestro.bien_asegurado
            
            # Sincronizar campos legacy
            siniestro.bien_nombre = bien.nombre
            siniestro.bien_modelo = bien.modelo or ''
            siniestro.bien_serie = bien.serie or ''
            siniestro.bien_marca = bien.marca or ''
            siniestro.bien_codigo_activo = bien.codigo_activo or ''
            
            # Sincronizar póliza
            if not siniestro.poliza_id:
                siniestro.poliza = bien.poliza
            
            # Sincronizar responsable si no está especificado
            if not siniestro.responsable_custodio_id and bien.responsable_custodio_id:
                siniestro.responsable_custodio = bien.responsable_custodio
    
    @classmethod
    def validar_bien_asegurado(cls, siniestro) -> ResultadoValidacion:
        """Valida que el siniestro tenga un bien asegurado o campos legacy."""
        if not siniestro.bien_asegurado_id and not siniestro.bien_nombre:
            return ResultadoValidacion(
                es_valido=False,
                errores={
                    'bien_asegurado': 'Debe especificar un bien asegurado o llenar los campos del bien manualmente.'
                }
            )
        return ResultadoValidacion(es_valido=True)
    
    @classmethod
    def validar_fecha_siniestro(cls, siniestro) -> ResultadoValidacion:
        """Valida que la fecha del siniestro no sea futura."""
        if siniestro.fecha_siniestro:
            ahora = timezone.now()
            if siniestro.fecha_siniestro > ahora:
                return ResultadoValidacion(
                    es_valido=False,
                    errores={
                        'fecha_siniestro': 'La fecha del siniestro no puede ser futura.'
                    }
                )
        return ResultadoValidacion(es_valido=True)
    
    @classmethod
    def validar_vigencia_poliza(cls, siniestro) -> ResultadoValidacion:
        """Valida que el siniestro esté dentro del período de vigencia de la póliza."""
        poliza = siniestro.get_poliza() if hasattr(siniestro, 'get_poliza') else siniestro.poliza
        
        if poliza and siniestro.fecha_siniestro:
            fecha_sin = siniestro.fecha_siniestro.date()
            if not (poliza.fecha_inicio <= fecha_sin <= poliza.fecha_fin):
                return ResultadoValidacion(
                    es_valido=False,
                    errores={
                        'fecha_siniestro': (
                            f'El siniestro debe ocurrir dentro del período de vigencia '
                            f'de la póliza ({poliza.fecha_inicio} - {poliza.fecha_fin}).'
                        )
                    }
                )
        return ResultadoValidacion(es_valido=True)
    
    @classmethod
    def validar_siniestro(cls, siniestro) -> ResultadoValidacion:
        """Ejecuta todas las validaciones del siniestro."""
        errores = {}
        
        validaciones = [
            cls.validar_bien_asegurado,
            cls.validar_fecha_siniestro,
            cls.validar_vigencia_poliza,
        ]
        
        for validacion in validaciones:
            resultado = validacion(siniestro)
            if not resultado.es_valido:
                errores.update(resultado.errores)
        
        if errores:
            return ResultadoValidacion(es_valido=False, errores=errores)
        
        return ResultadoValidacion(es_valido=True)
    
    @classmethod
    @transaction.atomic
    def crear_siniestro(
        cls,
        bien_asegurado=None,
        tipo_siniestro=None,
        fecha_siniestro=None,
        **kwargs
    ) -> ResultadoOperacion:
        """
        Crea un nuevo siniestro con sincronización y validaciones.
        
        Returns:
            ResultadoOperacion con el siniestro creado o errores
        """
        from app.models import Siniestro
        
        try:
            siniestro = Siniestro(
                bien_asegurado=bien_asegurado,
                tipo_siniestro=tipo_siniestro,
                fecha_siniestro=fecha_siniestro,
                **kwargs
            )
            
            # Sincronizar campos desde bien asegurado
            cls.sincronizar_desde_bien_asegurado(siniestro)
            
            # Validar
            validacion = cls.validar_siniestro(siniestro)
            if not validacion.es_valido:
                return ResultadoOperacion(
                    exitoso=False,
                    errores=validacion.errores,
                    mensaje="Error de validación"
                )
            
            siniestro.save()
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=siniestro,
                mensaje="Siniestro creado exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al crear siniestro: {str(e)}"
            )
    
    @classmethod
    @transaction.atomic
    def actualizar_siniestro(cls, siniestro, **campos) -> ResultadoOperacion:
        """
        Actualiza un siniestro existente con sincronización y validaciones.
        
        Returns:
            ResultadoOperacion
        """
        try:
            # Actualizar campos
            for campo, valor in campos.items():
                if hasattr(siniestro, campo):
                    setattr(siniestro, campo, valor)
            
            # Sincronizar campos si cambió el bien asegurado
            cls.sincronizar_desde_bien_asegurado(siniestro)
            
            # Validar
            validacion = cls.validar_siniestro(siniestro)
            if not validacion.es_valido:
                return ResultadoOperacion(
                    exitoso=False,
                    errores=validacion.errores,
                    mensaje="Error de validación"
                )
            
            siniestro.save()
            
            return ResultadoOperacion(
                exitoso=True,
                objeto=siniestro,
                mensaje="Siniestro actualizado exitosamente"
            )
            
        except Exception as e:
            return ResultadoOperacion(
                exitoso=False,
                errores={'__all__': str(e)},
                mensaje=f"Error al actualizar siniestro: {str(e)}"
            )


# ==============================================================================
# DOCUMENTO SERVICE
# ==============================================================================

class DocumentoService:
    """
    Servicio para gestión de Documentos.
    Valida coherencia de relaciones y tipos.
    """
    
    @classmethod
    def validar_relaciones(
        cls,
        tipo_documento: str,
        poliza_id: Optional[int],
        siniestro_id: Optional[int],
        factura_id: Optional[int]
    ) -> ResultadoValidacion:
        """Valida que el documento tenga al menos una relación y sea coherente."""
        errores = {}
        
        # Debe tener al menos una relación
        if not any([poliza_id, siniestro_id, factura_id]):
            errores['__all__'] = 'El documento debe estar asociado al menos a una póliza, siniestro o factura.'
        
        # Coherencia tipo-relación
        if tipo_documento == 'poliza' and not poliza_id:
            errores['tipo_documento'] = 'Un documento de tipo "Póliza" debe estar asociado a una póliza.'
        
        if tipo_documento == 'factura' and not factura_id:
            errores['tipo_documento'] = 'Un documento de tipo "Factura" debe estar asociado a una factura.'
        
        if errores:
            return ResultadoValidacion(es_valido=False, errores=errores)
        
        return ResultadoValidacion(es_valido=True)


# ==============================================================================
# NOTA CREDITO SERVICE
# ==============================================================================

class NotaCreditoService:
    """
    Servicio para gestión de Notas de Crédito.
    Valida que el monto no exceda el saldo de la factura.
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
        from django.db.models import Sum
        
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


# ==============================================================================
# BIEN ASEGURADO SERVICE
# ==============================================================================

class BienAseguradoService:
    """
    Servicio para gestión de Bienes Asegurados.
    Valida coherencia entre subgrupo y grupo de póliza.
    """
    
    @classmethod
    def validar_subgrupo_poliza(cls, poliza, subgrupo_ramo) -> ResultadoValidacion:
        """Valida que el subgrupo pertenezca al grupo de la póliza."""
        if poliza and subgrupo_ramo:
            if hasattr(poliza, 'grupo_ramo') and poliza.grupo_ramo:
                if subgrupo_ramo.grupo_ramo_id != poliza.grupo_ramo_id:
                    return ResultadoValidacion(
                        es_valido=False,
                        errores={
                            'subgrupo_ramo': (
                                f'El subgrupo "{subgrupo_ramo.nombre}" no pertenece '
                                f'al grupo "{poliza.grupo_ramo.nombre}" de la póliza.'
                            )
                        }
                    )
        
        return ResultadoValidacion(es_valido=True)
