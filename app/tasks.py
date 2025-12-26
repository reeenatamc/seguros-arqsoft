from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from django.db.models import F, Q, Case, When, Value, CharField
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generar_alertas_automaticas(self):
    try:
        logger.info('Iniciando generación de alertas automáticas')
        call_command('generar_alertas', tipo='todas')
        logger.info('Generación de alertas completada exitosamente')
        return {'status': 'success', 'message': 'Alertas generadas exitosamente'}
    except Exception as e:
        logger.error(f'Error al generar alertas: {str(e)}')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def enviar_alertas_email(self):
    try:
        logger.info('Iniciando envío de alertas por email')
        call_command('enviar_alertas_email', max=100)
        logger.info('Envío de alertas por email completado')
        return {'status': 'success', 'message': 'Alertas enviadas por email exitosamente'}
    except Exception as e:
        logger.error(f'Error al enviar alertas por email: {str(e)}')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def actualizar_estados_polizas(self):
    from .models import Poliza, ConfiguracionSistema
    
    try:
        logger.info('Iniciando actualización de estados de pólizas')
        
        hoy = timezone.now().date()
        dias_alerta = ConfiguracionSistema.get_config('DIAS_ALERTA_VENCIMIENTO_POLIZA', 30)
        fecha_alerta = hoy + timedelta(days=dias_alerta)
        
        vencidas = Poliza.objects.filter(
            fecha_fin__lt=hoy,
            estado__in=['vigente', 'por_vencer']
        ).update(estado='vencida')
        
        por_vencer = Poliza.objects.filter(
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy,
            fecha_fin__lte=fecha_alerta,
            estado='vigente'
        ).update(estado='por_vencer')
        
        vigentes = Poliza.objects.filter(
            fecha_inicio__lte=hoy,
            fecha_fin__gt=fecha_alerta,
            estado__in=['vencida', 'por_vencer']
        ).exclude(estado='cancelada').update(estado='vigente')
        
        mensaje = f'Actualizadas: {vencidas} vencidas, {por_vencer} por vencer, {vigentes} vigentes'
        logger.info(mensaje)
        
        return {
            'status': 'success',
            'vencidas': vencidas,
            'por_vencer': por_vencer,
            'vigentes': vigentes
        }
    except Exception as e:
        logger.error(f'Error al actualizar estados de pólizas: {str(e)}')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def actualizar_estados_facturas(self):
    from .models import Factura
    from django.db.models import Sum, Subquery, OuterRef
    from decimal import Decimal
    
    try:
        logger.info('Iniciando actualización de estados de facturas')
        hoy = timezone.now().date()
        
        vencidas = Factura.objects.filter(
            estado__in=['pendiente', 'parcial'],
            fecha_vencimiento__lt=hoy
        ).update(estado='vencida')
        
        facturas_pendientes = Factura.objects.filter(
            estado__in=['pendiente', 'parcial', 'vencida']
        ).prefetch_related('pagos')
        
        facturas_pagadas = []
        facturas_parciales = []
        facturas_pendientes_ids = []
        
        for factura in facturas_pendientes:
            total_pagado = factura.pagos.filter(estado='aprobado').aggregate(
                total=Sum('monto')
            )['total'] or Decimal('0.00')
            
            if total_pagado >= factura.monto_total:
                facturas_pagadas.append(factura.pk)
            elif total_pagado > Decimal('0.00'):
                facturas_parciales.append(factura.pk)
            elif factura.fecha_vencimiento >= hoy:
                facturas_pendientes_ids.append(factura.pk)
        
        pagadas_count = Factura.objects.filter(pk__in=facturas_pagadas).update(estado='pagada')
        parciales_count = Factura.objects.filter(pk__in=facturas_parciales).update(estado='parcial')
        pendientes_count = Factura.objects.filter(pk__in=facturas_pendientes_ids).update(estado='pendiente')
        
        mensaje = f'Actualizadas: {vencidas} vencidas, {pagadas_count} pagadas, {parciales_count} parciales'
        logger.info(mensaje)
        
        return {
            'status': 'success',
            'vencidas': vencidas,
            'pagadas': pagadas_count,
            'parciales': parciales_count,
            'pendientes': pendientes_count
        }
    except Exception as e:
        logger.error(f'Error al actualizar estados de facturas: {str(e)}')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def generar_reporte_siniestros_mensual(self):
    try:
        logger.info('Iniciando generación de reporte mensual de siniestros')
        call_command('generar_reporte_siniestros', periodo='mensual')
        logger.info('Reporte mensual de siniestros generado exitosamente')
        return {'status': 'success', 'message': 'Reporte mensual generado exitosamente'}
    except Exception as e:
        logger.error(f'Error al generar reporte mensual: {str(e)}')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def limpiar_alertas_antiguas(self, dias=90):
    from .models import Alerta
    
    try:
        logger.info(f'Iniciando limpieza de alertas antiguas (más de {dias} días)')
        
        fecha_limite = timezone.now() - timedelta(days=dias)
        cantidad = Alerta.objects.filter(
            estado='atendida',
            fecha_creacion__lt=fecha_limite
        ).delete()[0]
        
        mensaje = f'Se eliminaron {cantidad} alertas antiguas'
        logger.info(mensaje)
        
        return {'status': 'success', 'eliminadas': cantidad}
    except Exception as e:
        logger.error(f'Error al limpiar alertas antiguas: {str(e)}')
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def actualizar_descuentos_pronto_pago(self):
    from .models import Factura
    from decimal import Decimal
    
    try:
        logger.info('Actualizando descuentos por pronto pago')
        
        facturas = Factura.objects.filter(estado='pendiente')
        actualizadas = 0
        
        for factura in facturas:
            descuento_anterior = factura.descuento_pronto_pago
            factura.calcular_descuento_pronto_pago()
            
            if descuento_anterior != factura.descuento_pronto_pago:
                factura.calcular_monto_total()
                Factura.objects.filter(pk=factura.pk).update(
                    descuento_pronto_pago=factura.descuento_pronto_pago,
                    monto_total=factura.monto_total
                )
                actualizadas += 1
        
        return {'status': 'success', 'actualizadas': actualizadas}
    except Exception as e:
        logger.error(f'Error al actualizar descuentos: {str(e)}')
        raise
