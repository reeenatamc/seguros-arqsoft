"""
Módulo de Señales Django para el Sistema de Gestión de Seguros.

Este módulo implementa señales (signals) de Django para automatizar flujos
de trabajo y notificaciones basados en eventos del ciclo de vida de los modelos.

Señales Implementadas:
    1. **siniestro_pre_save**: Captura el estado anterior del siniestro antes
       de guardar para detectar cambios de estado sin consultas adicionales.

    2. **siniestro_post_save**: Automatiza notificaciones según el evento:
       - Al crear: Notifica al broker y al usuario reportante
       - Al cerrar/liquidar: Notifica a gerencia y responsable

Flujo de Notificaciones Automáticas:
    Cuando se crea un siniestro::

        1. Se detecta created=True en post_save
        2. Se notifica al broker vía NotificacionesService
        3. Se notifica al usuario reportante por email

    Cuando se cierra/liquida un siniestro::

        1. Se compara estado anterior (guardado en pre_save) con nuevo estado
        2. Si el nuevo estado es 'liquidado' o 'cerrado', se notifica cierre
        3. Se evitan notificaciones duplicadas verificando estado previo

Patrón de Diseño:
    Se utiliza el patrón Observer de Django para desacoplar la lógica de
    notificaciones del modelo Siniestro, manteniendo el principio de
    responsabilidad única (SRP).

Autor: Equipo de Desarrollo UTPL
Versión: 1.0.0
Última Actualización: Enero 2026
"""

from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import ConfiguracionSistema, Siniestro
from .services.alertas import NotificacionesService


@receiver(pre_save, sender=Siniestro)
def siniestro_pre_save(sender, instance: Siniestro, **kwargs):
    """

    Guarda el estado anterior del siniestro en la instancia para poder

    detectar cambios de estado en post_save sin consultas adicionales.

    """

    if not instance.pk:

        instance._previous_estado = None

    else:

        try:

            prev = sender.objects.only("estado").get(pk=instance.pk)

            instance._previous_estado = prev.estado

        except sender.DoesNotExist:

            instance._previous_estado = None


@receiver(post_save, sender=Siniestro)
def siniestro_post_save(sender, instance: Siniestro, created: bool, **kwargs):
    """

    Automatiza notificaciones de flujo para siniestros:

    - Al crear: notificar automáticamente al broker y al usuario reportante.

    - Al cerrar/liquidar: notificar a gerencia y responsable/cliente.

    """

    # 1) Al crear siniestro

    if created:

        try:

            # Notificar al broker

            NotificacionesService.notificar_siniestro_a_broker(
                siniestro=instance, usuario=getattr(instance, "creado_por", None)
            )

        except Exception:

            # Evitar que un fallo de email rompa el flujo de guardado

            pass

        # Notificar al usuario reportante (si tiene email)

        reportante = getattr(instance, "creado_por", None)

        if reportante and reportante.email:

            try:

                NotificacionesService.notificar_siniestro_a_usuario(
                    siniestro=instance,
                    usuario=reportante,
                )

            except Exception:

                pass

        return

    # 2) En actualizaciones: detectar paso a 'liquidado' o 'cerrado'

    previous_estado = getattr(instance, "_previous_estado", None)

    nuevo_estado = instance.estado

    if previous_estado in ("liquidado", "cerrado"):

        # Ya estaba cerrado/liquidado antes; no repetir notificación

        return

    if nuevo_estado in ("liquidado", "cerrado"):

        try:

            NotificacionesService.notificar_cierre_siniestro(
                siniestro=instance,
                usuario=getattr(instance, "creado_por", None),
            )

        except Exception:

            pass
