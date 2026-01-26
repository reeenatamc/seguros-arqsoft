"""

Servicio de notificaciones al Responsable/Custodio del bien.

Responsabilidad única: notificar al custodio del bien.

"""

from django.utils import timezone

from .base import BaseNotifier


class ResponsableNotifier(BaseNotifier):

    """

    Notificador especializado para comunicaciones con el responsable/custodio.

    USO:

        notifier = ResponsableNotifier()

        notifier.notificar_siniestro_pendiente(siniestro)

    """

    def notificar_siniestro_pendiente(self, siniestro, usuario=None):

        """

        Notifica al responsable/custodio sobre un siniestro pendiente.

        Args:

            siniestro: Instancia del modelo Siniestro

            usuario: Usuario que realiza la acción

        Returns:

            NotificacionEmail o None si no hay email del responsable

        """

        if not siniestro.responsable_custodio or not siniestro.responsable_custodio.email:

            return None

        email_responsable = siniestro.responsable_custodio.email

        nombre_responsable = siniestro.responsable_custodio.nombre

        dias_transcurridos = siniestro.dias_gestion

        asunto = f"Aviso: Siniestro Pendiente - {siniestro.numero_siniestro}"

        bloques = [

            {

                'titulo': 'Información del Siniestro',

                'filas': [

                    {'label': 'Número', 'valor': siniestro.numero_siniestro},

                    {'label': 'Bien Afectado', 'valor': siniestro.bien_nombre},

                    {'label': 'Fecha del Siniestro', 'valor': siniestro.fecha_siniestro.strftime('%d/%m/%Y')},

                    {'label': 'Estado Actual', 'valor': siniestro.get_estado_display()},

                ],

            },

        ]

        contenido_html = self._renderizar_email(

            titulo=asunto,

            intro=[

                f"Estimado(a) {nombre_responsable},",

                f"existe un siniestro registrado bajo su responsabilidad con {dias_transcurridos} días de gestión.",

            ],

            bloques=bloques,

            cta_text='Ver siniestro en el sistema',

            cta_url=f"{self._get_site_url()}/siniestros/{siniestro.id}/detalle/",

            nota='Por favor, comuníquese con el área de seguros para dar seguimiento.',

        )

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número: {siniestro.numero_siniestro}\n"

            f"Bien Afectado: {siniestro.bien_nombre}\n"

            f"Fecha del Siniestro: {siniestro.fecha_siniestro.strftime('%d/%m/%Y')}\n"

            f"Estado Actual: {siniestro.get_estado_display()}\n"

        )

        notificacion = self._crear_notificacion(

            tipo='siniestro_responsable',

            destinatario=email_responsable,

            asunto=asunto,

            contenido=contenido_texto,

            contenido_html=contenido_html,

            siniestro=siniestro,

            usuario=usuario,

        )

        # Actualizar fecha de notificación

        siniestro.fecha_notificacion_responsable = timezone.now().date()

        siniestro.save(update_fields=['fecha_notificacion_responsable'])

        self._enviar_email(notificacion)

        return notificacion

    def notificar_documentacion_pendiente(self, siniestro, usuario=None):

        """

        Recordatorio de documentación pendiente al responsable.

        Args:

            siniestro: Siniestro con documentación pendiente

            usuario: Usuario que realiza la acción

        Returns:

            NotificacionEmail o None

        """

        if not siniestro.responsable_custodio or not siniestro.responsable_custodio.email:

            return None

        email_responsable = siniestro.responsable_custodio.email

        dias = siniestro.dias_desde_registro

        asunto = f"Recordatorio: Documentación Pendiente - {siniestro.numero_siniestro}"

        bloques = [

            {

                'titulo': 'Información del Siniestro',

                'filas': [

                    {'label': 'Número', 'valor': siniestro.numero_siniestro},

                    {'label': 'Bien Afectado', 'valor': siniestro.bien_nombre},

                    {'label': 'Días desde registro', 'valor': dias},

                    {'label': 'Estado', 'valor': 'Documentación Pendiente'},

                ],

            },

        ]

        contenido_html = self._renderizar_email(

            titulo=asunto,

            intro=[

                f"Estimado(a) {siniestro.responsable_custodio.nombre},",

                "le recordamos que el siguiente siniestro tiene documentación pendiente de entrega.",

            ],

            bloques=bloques,

            cta_text='Ver documentos requeridos',

            cta_url=f"{self._get_site_url()}/siniestros/{siniestro.id}/detalle/",

            nota='Por favor, complete la documentación requerida lo antes posible.',

        )

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número: {siniestro.numero_siniestro}\n"

            f"Bien Afectado: {siniestro.bien_nombre}\n"

            f"Días desde registro: {dias}\n"

        )

        notificacion = self._crear_notificacion(

            tipo='siniestro_documentacion',

            destinatario=email_responsable,

            asunto=asunto,

            contenido=contenido_texto,

            contenido_html=contenido_html,

            siniestro=siniestro,

            usuario=usuario,

        )

        self._enviar_email(notificacion)

        return notificacion
