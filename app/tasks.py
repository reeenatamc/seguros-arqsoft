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

    """

    Actualiza automáticamente los estados de las pólizas.

    Usa PolizaManager para centralizar reglas de negocio.

    """

    from .models import Poliza, ConfiguracionSistema

    try:

        logger.info('Iniciando actualización de estados de pólizas')

        hoy = timezone.now().date()

        dias_alerta = ConfiguracionSistema.get_config('DIAS_ALERTA_VENCIMIENTO_POLIZA', 30)

        fecha_alerta = hoy + timedelta(days=dias_alerta)

        # Marcar vencidas: las que están activas pero ya pasó su fecha_fin

        vencidas = Poliza.objects.activas().filter(

            fecha_fin__lt=hoy

        ).update(estado='vencida')

        # Marcar por_vencer: vigentes que vencen pronto

        por_vencer = Poliza.objects.vigentes().filter(

            fecha_inicio__lte=hoy,

            fecha_fin__gte=hoy,

            fecha_fin__lte=fecha_alerta

        ).update(estado='por_vencer')

        # Restaurar vigentes: las que ya no están por vencer (fecha_fin lejana)

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

# ==================== TAREAS DE BACKUP AUTOMÁTICO ====================

@shared_task(bind=True, max_retries=2)
def backup_automatico(self):

    """

    Tarea programada para crear backups automáticos de la base de datos.

    Se ejecuta según la configuración definida en ConfiguracionBackup.

    """

    from .models import BackupRegistro, ConfiguracionBackup

    from django.core.management import call_command

    from pathlib import Path

    import time

    try:

        # Obtener configuración

        config = ConfiguracionBackup.get_config()

        if not config.activo:

            logger.info('Backup automático desactivado')

            return {'status': 'skipped', 'reason': 'Backup automático desactivado'}

        logger.info('Iniciando backup automático programado')

        inicio = time.time()

        # Crear registro de backup

        backup_registro = BackupRegistro.objects.create(

            nombre=f'backup_auto_{timezone.now().strftime("%Y%m%d_%H%M%S")}',

            ruta='',

            tipo='automatico',

            estado='en_progreso',

            frecuencia=config.frecuencia,

            comprimido=config.comprimir,

            notas='Backup automático programado'

        )

        try:

            # Ejecutar comando de backup

            resultado = call_command(

                'backup_database',

                compress=config.comprimir,

                include_media=config.incluir_media,

                quiet=True

            )

            # Actualizar registro

            duracion = int(time.time() - inicio)

            backup_path = Path(resultado) if resultado else None

            backup_registro.estado = 'completado'

            backup_registro.duracion_segundos = duracion

            if backup_path and backup_path.exists():

                backup_registro.ruta = str(backup_path)

                backup_registro.tamaño = backup_path.stat().st_size

                backup_registro.nombre = backup_path.name

            backup_registro.save()

            # Actualizar última fecha de backup

            config.ultimo_backup = timezone.now()

            config.save()

            # Limpiar backups antiguos

            eliminados = BackupRegistro.limpiar_antiguos(dias_retener=config.dias_retener)

            logger.info(

                f'Backup automático completado: {backup_registro.nombre} '

                f'({backup_registro.tamaño_legible}) en {duracion}s. '

                f'{eliminados} backups antiguos eliminados.'

            )

            # Enviar notificación si está configurado

            if config.notificar_email:

                enviar_notificacion_backup.delay(

                    backup_registro.pk,

                    config.notificar_email,

                    'success'

                )

            return {

                'status': 'success',

                'backup_id': backup_registro.pk,

                'nombre': backup_registro.nombre,

                'tamaño': backup_registro.tamaño_legible,

                'duracion': duracion,

                'backups_eliminados': eliminados

            }

        except Exception as e:

            backup_registro.estado = 'fallido'

            backup_registro.error_mensaje = str(e)

            backup_registro.save()

            if config.notificar_email:

                enviar_notificacion_backup.delay(

                    backup_registro.pk,

                    config.notificar_email,

                    'error'

                )

            raise

    except Exception as e:

        logger.error(f'Error en backup automático: {str(e)}')

        raise self.retry(exc=e, countdown=300)

@shared_task
def enviar_notificacion_backup(backup_id, email, status):

    """

    Envía notificación por email sobre el estado del backup.

    """

    from .models import BackupRegistro

    from django.core.mail import send_mail

    from django.conf import settings

    try:

        backup = BackupRegistro.objects.get(pk=backup_id)

        if status == 'success':

            subject = f'✅ Backup Exitoso - {backup.nombre}'

            message = f'''

Backup del sistema completado exitosamente.

Detalles:

- Nombre: {backup.nombre}

- Tamaño: {backup.tamaño_legible}

- Tipo: {backup.get_tipo_display()}

- Duración: {backup.duracion_segundos} segundos

- Fecha: {backup.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')}

El backup se encuentra en: {backup.ruta}

'''

        else:

            subject = f'❌ Error en Backup - Sistema de Seguros'

            message = f'''

Error durante el backup automático del sistema.

Error: {backup.error_mensaje}

Fecha: {backup.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')}

Por favor, revise la configuración y los logs del sistema.

'''

        send_mail(

            subject=subject,

            message=message,

            from_email=settings.DEFAULT_FROM_EMAIL,

            recipient_list=[email],

            fail_silently=True

        )

    except BackupRegistro.DoesNotExist:

        logger.warning(f'Backup {backup_id} no encontrado para notificación')

    except Exception as e:

        logger.error(f'Error enviando notificación de backup: {str(e)}')

@shared_task
def limpiar_backups_antiguos():

    """

    Tarea programada para limpiar backups antiguos.

    Se ejecuta diariamente.

    """

    from .models import BackupRegistro, ConfiguracionBackup

    try:

        config = ConfiguracionBackup.get_config()

        eliminados = BackupRegistro.limpiar_antiguos(dias_retener=config.dias_retener)

        logger.info(f'Limpieza de backups: {eliminados} archivos eliminados')

        return {'status': 'success', 'eliminados': eliminados}

    except Exception as e:

        logger.error(f'Error en limpieza de backups: {str(e)}')

        return {'status': 'error', 'error': str(e)}

@shared_task
def verificar_integridad_backups():

    """

    Verifica la integridad de los backups existentes.

    Marca como eliminados los que ya no existen físicamente.

    """

    from .models import BackupRegistro

    from pathlib import Path

    try:

        backups = BackupRegistro.objects.filter(estado='completado')

        verificados = 0

        problemas = 0

        for backup in backups:

            if not Path(backup.ruta).exists():

                backup.estado = 'eliminado'

                backup.notas = f'{backup.notas}\nArchivo no encontrado durante verificación.'

                backup.save()

                problemas += 1

            else:

                verificados += 1

        logger.info(

            f'Verificación de backups: {verificados} OK, {problemas} con problemas'

        )

        return {

            'status': 'success',

            'verificados': verificados,

            'problemas': problemas

        }

    except Exception as e:

        logger.error(f'Error verificando backups: {str(e)}')

        return {'status': 'error', 'error': str(e)}
