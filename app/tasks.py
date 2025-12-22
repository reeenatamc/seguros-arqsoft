from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from .models import Poliza, Factura, Siniestro
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generar_alertas_automaticas(self):
    """
    Tarea periódica que genera alertas para pólizas, facturas y siniestros.
    Se ejecuta diariamente a las 8:00 AM.
    """
    try:
        logger.info('Iniciando generación de alertas automáticas')
        call_command('generar_alertas', tipo='todas')
        logger.info('Generación de alertas completada exitosamente')
        return 'Alertas generadas exitosamente'
    except Exception as e:
        logger.error(f'Error al generar alertas: {str(e)}')
        raise


@shared_task(bind=True)
def enviar_alertas_email(self):
    """
    Tarea periódica que envía las alertas pendientes por correo electrónico.
    Se ejecuta dos veces al día (8:30 AM y 2:00 PM).
    """
    try:
        logger.info('Iniciando envío de alertas por email')
        call_command('enviar_alertas_email', max=100)
        logger.info('Envío de alertas por email completado')
        return 'Alertas enviadas por email exitosamente'
    except Exception as e:
        logger.error(f'Error al enviar alertas por email: {str(e)}')
        raise


@shared_task(bind=True)
def actualizar_estados_polizas(self):
    """
    Tarea periódica que actualiza el estado de todas las pólizas.
    Se ejecuta diariamente a las 7:00 AM.
    """
    try:
        logger.info('Iniciando actualización de estados de pólizas')
        
        polizas = Poliza.objects.all()
        actualizadas = 0
        
        for poliza in polizas:
            estado_anterior = poliza.estado
            poliza.actualizar_estado()
            
            if estado_anterior != poliza.estado:
                poliza.save()
                actualizadas += 1
        
        mensaje = f'Se actualizaron {actualizadas} pólizas de {polizas.count()} totales'
        logger.info(mensaje)
        return mensaje
    except Exception as e:
        logger.error(f'Error al actualizar estados de pólizas: {str(e)}')
        raise


@shared_task(bind=True)
def actualizar_estados_facturas(self):
    """
    Tarea periódica que actualiza el estado de todas las facturas.
    Se ejecuta cada 6 horas.
    """
    try:
        logger.info('Iniciando actualización de estados de facturas')
        
        facturas = Factura.objects.exclude(estado='pagada')
        actualizadas = 0
        
        for factura in facturas:
            estado_anterior = factura.estado
            factura.actualizar_estado()
            
            if estado_anterior != factura.estado:
                factura.save()
                actualizadas += 1
        
        mensaje = f'Se actualizaron {actualizadas} facturas de {facturas.count()} totales'
        logger.info(mensaje)
        return mensaje
    except Exception as e:
        logger.error(f'Error al actualizar estados de facturas: {str(e)}')
        raise


@shared_task(bind=True)
def generar_reporte_siniestros_mensual(self):
    """
    Tarea que genera un reporte mensual de siniestros.
    Puede ser ejecutada manualmente o programada mensualmente.
    """
    try:
        logger.info('Iniciando generación de reporte mensual de siniestros')
        call_command('generar_reporte_siniestros', periodo='mensual')
        logger.info('Reporte mensual de siniestros generado exitosamente')
        return 'Reporte mensual generado exitosamente'
    except Exception as e:
        logger.error(f'Error al generar reporte mensual: {str(e)}')
        raise


@shared_task(bind=True)
def limpiar_alertas_antiguas(self, dias=90):
    """
    Tarea que elimina alertas antiguas ya atendidas.
    Por defecto elimina alertas de más de 90 días.
    """
    try:
        logger.info(f'Iniciando limpieza de alertas antiguas (más de {dias} días)')
        
        from datetime import timedelta
        from .models import Alerta
        
        fecha_limite = timezone.now() - timedelta(days=dias)
        alertas_antiguas = Alerta.objects.filter(
            estado='atendida',
            fecha_creacion__lt=fecha_limite
        )
        
        cantidad = alertas_antiguas.count()
        alertas_antiguas.delete()
        
        mensaje = f'Se eliminaron {cantidad} alertas antiguas'
        logger.info(mensaje)
        return mensaje
    except Exception as e:
        logger.error(f'Error al limpiar alertas antiguas: {str(e)}')
        raise
