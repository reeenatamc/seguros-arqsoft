"""

Servicio de Notificaciones por Email.

Gestiona el envío de notificaciones automáticas relacionadas con siniestros,

pólizas, facturas y alertas del sistema.

"""

from django.core.mail import send_mail, EmailMultiAlternatives

from django.template.loader import render_to_string

from django.utils import timezone

from django.conf import settings

from datetime import timedelta

from app.models import (

    Siniestro, Poliza, Factura, NotificacionEmail,

    ConfiguracionSistema

)


class NotificacionesService:

    """Servicio para gestión de notificaciones por email"""

    @staticmethod
    def _crear_notificacion(tipo, destinatario, asunto, contenido,

                            siniestro=None, poliza=None, factura=None,

                            cc=None, contenido_html=None, usuario=None):

        """Crea un registro de notificación en la base de datos"""

        return NotificacionEmail.objects.create(

            tipo=tipo,

            destinatario=destinatario,

            cc=cc or '',

            asunto=asunto,

            contenido=contenido,

            contenido_html=contenido_html or '',

            siniestro=siniestro,

            poliza=poliza,

            factura=factura,

            creado_por=usuario,

        )

    @staticmethod
    def _enviar_email(notificacion):

        """Envía el email y actualiza el estado de la notificación"""

        try:

            cc_list = [e.strip() for e in notificacion.cc.split(',') if e.strip()]

            if notificacion.contenido_html:

                # Email con contenido HTML

                email = EmailMultiAlternatives(

                    subject=notificacion.asunto,

                    body=notificacion.contenido,

                    from_email=settings.DEFAULT_FROM_EMAIL,

                    to=[notificacion.destinatario],

                    cc=cc_list if cc_list else None,

                )

                email.attach_alternative(notificacion.contenido_html, "text/html")

                email.send(fail_silently=False)

            else:

                # Email de texto plano

                send_mail(

                    subject=notificacion.asunto,

                    message=notificacion.contenido,

                    from_email=settings.DEFAULT_FROM_EMAIL,

                    recipient_list=[notificacion.destinatario],

                    fail_silently=False,

                )

            notificacion.marcar_como_enviado()

            return True

        except Exception as e:

            notificacion.registrar_error(str(e))

            return False

    @classmethod
    def notificar_siniestro_a_broker(cls, siniestro, usuario=None):

        """

        Notifica un siniestro al broker (NO a la aseguradora directamente),

        usando la plantilla de correo profesional reutilizable.

        Args:

            siniestro: Instancia del modelo Siniestro

            usuario: Usuario que realiza la acción

        Returns:

            NotificacionEmail: La notificación creada

        """

        from django.conf import settings

        from django.template.loader import render_to_string

        # Obtener email del broker desde el siniestro o la póliza

        email_broker = siniestro.email_broker

        if not email_broker and siniestro.poliza.corredor_seguros:

            email_broker = siniestro.poliza.corredor_seguros.email

        if not email_broker:

            raise ValueError("No se encontró email del broker para notificar")

        asunto = f"Notificación de Siniestro - {siniestro.numero_siniestro}"

        context = {

            "titulo": asunto,

            "intro": [

                "Se ha registrado un nuevo siniestro que requiere su gestión ante la aseguradora.",

            ],

            "bloques": [

                {

                    "titulo": "Información del Siniestro",

                    "filas": [

                        {"label": "Número de Siniestro", "valor": siniestro.numero_siniestro},

                        {

                            "label": "Tipo",

                            "valor": siniestro.tipo_siniestro.get_nombre_display()

                            if siniestro.tipo_siniestro

                            else "N/A",

                        },

                        {

                            "label": "Fecha del Siniestro",

                            "valor": siniestro.fecha_siniestro.strftime("%d/%m/%Y %H:%M"),

                        },

                        {"label": "Ubicación", "valor": siniestro.ubicacion},

                    ],

                },

                {

                    "titulo": "Bien Afectado",

                    "filas": [

                        {"label": "Nombre", "valor": siniestro.bien_nombre},

                        {"label": "Marca", "valor": siniestro.bien_marca or "N/A"},

                        {"label": "Modelo", "valor": siniestro.bien_modelo or "N/A"},

                        {"label": "Serie", "valor": siniestro.bien_serie or "N/A"},

                        {

                            "label": "Código de Activo",

                            "valor": siniestro.bien_codigo_activo or "N/A",

                        },

                    ],

                },

                {

                    "titulo": "Póliza Asociada",

                    "filas": [

                        {"label": "Número de Póliza", "valor": siniestro.poliza.numero_poliza},

                        {

                            "label": "Aseguradora",

                            "valor": siniestro.poliza.compania_aseguradora.nombre,

                        },

                        {

                            "label": "Vigencia",

                            "valor": f"{siniestro.poliza.fecha_inicio.strftime('%d/%m/%Y')} - "

                            f"{siniestro.poliza.fecha_fin.strftime('%d/%m/%Y')}",

                        },

                    ],

                },

            ],

            "cta_text": "Ver siniestro en el sistema",

            "cta_url": getattr(settings, "SITE_URL", "") + f"/siniestros/{siniestro.id}/detalle/",

            "nota": "Este correo es informativo. Por favor, continúe la gestión según los procedimientos internos.",

        }

        contenido_html = render_to_string("emails/base_notificacion.html", context)

        # Versión texto plano (fallback)

        contenido_texto = (

            f"Notificación de Siniestro - {siniestro.numero_siniestro}\n\n"

            f"Número de Siniestro: {siniestro.numero_siniestro}\n"

            f"Tipo: {siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else 'N/A'}\n"

            f"Fecha del Siniestro: {siniestro.fecha_siniestro.strftime('%d/%m/%Y %H:%M')}\n"

            f"Ubicación: {siniestro.ubicacion}\n"

        )

        notificacion = cls._crear_notificacion(

            tipo="siniestro_broker",

            destinatario=email_broker,

            asunto=asunto,

            contenido=contenido_texto.strip(),

            contenido_html=contenido_html,

            siniestro=siniestro,

            usuario=usuario,

        )

        # Actualizar fecha de notificación en el siniestro

        siniestro.fecha_notificacion_broker = timezone.now()

        # Calcular fecha de respuesta esperada (5 días hábiles ≈ 7 días calendario)

        siniestro.fecha_respuesta_esperada = timezone.now().date() + timedelta(days=7)

        siniestro.save(update_fields=['fecha_notificacion_broker', 'fecha_respuesta_esperada'])

        # Intentar enviar

        cls._enviar_email(notificacion)

        return notificacion

    @classmethod
    def notificar_siniestro_a_usuario(cls, siniestro, usuario=None):

        """

        Notifica al usuario que registró el siniestro (reportante).

        """

        if not usuario or not usuario.email:

            return None

        from django.conf import settings

        from django.template.loader import render_to_string

        asunto = f"Confirmación de Registro de Siniestro - {siniestro.numero_siniestro}"

        context = {

            "titulo": asunto,

            "intro": [

                f"Estimado(a) {usuario.get_full_name() or usuario.username},",

                "hemos registrado correctamente su reporte de siniestro. A continuación, el resumen:",

            ],

            "bloques": [

                {

                    "titulo": "Información del Siniestro",

                    "filas": [

                        {"label": "Número", "valor": siniestro.numero_siniestro},

                        {

                            "label": "Tipo",

                            "valor": siniestro.tipo_siniestro.get_nombre_display()

                            if siniestro.tipo_siniestro

                            else "N/A",

                        },

                        {

                            "label": "Fecha del Siniestro",

                            "valor": siniestro.fecha_siniestro.strftime("%d/%m/%Y %H:%M"),

                        },

                        {"label": "Bien Afectado", "valor": siniestro.bien_nombre},

                    ],

                },

                {

                    "titulo": "Información de la Póliza",

                    "filas": [

                        {"label": "Número de Póliza", "valor": siniestro.poliza.numero_poliza},

                        {

                            "label": "Aseguradora",

                            "valor": siniestro.poliza.compania_aseguradora.nombre,

                        },

                    ],

                },

            ],

            "cta_text": "Ver siniestro en el sistema",

            "cta_url": getattr(settings, "SITE_URL", "") + f"/siniestros/{siniestro.id}/detalle/",

            "nota": "Nuestro equipo de gestión de seguros dará seguimiento a su caso.",

        }

        contenido_html = render_to_string("emails/base_notificacion.html", context)

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número: {siniestro.numero_siniestro}\n"

            f"Tipo: {siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else 'N/A'}\n"

            f"Fecha del Siniestro: {siniestro.fecha_siniestro.strftime('%d/%m/%Y %H:%M')}\n"

            f"Bien Afectado: {siniestro.bien_nombre}\n"

        )

        notificacion = cls._crear_notificacion(

            tipo="siniestro_usuario",

            destinatario=usuario.email,

            asunto=asunto,

            contenido=contenido_texto.strip(),

            contenido_html=contenido_html,

            siniestro=siniestro,

            usuario=usuario,

        )

        cls._enviar_email(notificacion)

        return notificacion

    @classmethod
    def notificar_responsable_bien(cls, siniestro, usuario=None):

        """

        Notifica al responsable/custodio del bien sobre el siniestro.

        Se usa cuando han pasado más de 15 días sin resolver.

        Args:

            siniestro: Instancia del modelo Siniestro

            usuario: Usuario que realiza la acción

        Returns:

            NotificacionEmail: La notificación creada o None si no hay email

        """

        if not siniestro.responsable_custodio or not siniestro.responsable_custodio.email:

            return None

        email_responsable = siniestro.responsable_custodio.email

        from django.conf import settings

        from django.template.loader import render_to_string

        asunto = f"Aviso: Siniestro Pendiente - {siniestro.numero_siniestro}"

        dias_transcurridos = siniestro.dias_gestion

        context = {

            "titulo": asunto,

            "intro": [

                f"Estimado(a) {siniestro.responsable_custodio.nombre},",

                f"existe un siniestro registrado bajo su responsabilidad con {dias_transcurridos} días de gestión.",

            ],

            "bloques": [

                {

                    "titulo": "Información del Siniestro",

                    "filas": [

                        {"label": "Número", "valor": siniestro.numero_siniestro},

                        {"label": "Bien Afectado", "valor": siniestro.bien_nombre},

                        {

                            "label": "Fecha del Siniestro",

                            "valor": siniestro.fecha_siniestro.strftime("%d/%m/%Y"),

                        },

                        {

                            "label": "Estado Actual",

                            "valor": siniestro.get_estado_display(),

                        },

                    ],

                },

            ],

            "cta_text": "Ver siniestro en el sistema",

            "cta_url": getattr(settings, "SITE_URL", "") + f"/siniestros/{siniestro.id}/detalle/",

            "nota": "Por favor, comuníquese con el área de seguros para dar seguimiento.",

        }

        contenido_html = render_to_string("emails/base_notificacion.html", context)

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número: {siniestro.numero_siniestro}\n"

            f"Bien Afectado: {siniestro.bien_nombre}\n"

            f"Fecha del Siniestro: {siniestro.fecha_siniestro.strftime('%d/%m/%Y')}\n"

            f"Estado Actual: {siniestro.get_estado_display()}\n"

        )

        notificacion = cls._crear_notificacion(

            tipo="siniestro_responsable",

            destinatario=email_responsable,

            asunto=asunto,

            contenido=contenido_texto.strip(),

            contenido_html=contenido_html,

            siniestro=siniestro,

            usuario=usuario,

        )

        # Actualizar fecha de notificación

        siniestro.fecha_notificacion_responsable = timezone.now().date()

        siniestro.save(update_fields=['fecha_notificacion_responsable'])

        cls._enviar_email(notificacion)

        return notificacion

    @classmethod
    def notificar_cierre_siniestro(cls, siniestro, usuario=None):

        """

        Notifica el cierre de un siniestro al responsable y gerencia.

        Args:

            siniestro: Instancia del modelo Siniestro

            usuario: Usuario que realiza la acción

        Returns:

            list: Lista de notificaciones creadas

        """

        notificaciones = []

        # Determinar destinatarios

        destinatarios = []

        # Responsable del bien (cliente interno)

        if siniestro.responsable_custodio and siniestro.responsable_custodio.email:

            destinatarios.append(siniestro.responsable_custodio.email)

        # Gerencia: correo configurado en ConfiguracionSistema

        email_gerente = ConfiguracionSistema.get_config('EMAIL_GERENTE_SINIESTROS', None)

        if email_gerente:

            destinatarios.append(email_gerente)

        from django.conf import settings

        from django.template.loader import render_to_string

        asunto = f"Cierre de Siniestro - {siniestro.numero_siniestro}"

        context = {

            "titulo": asunto,

            "intro": [

                "Se comunica el cierre del siguiente siniestro:",

            ],

            "bloques": [

                {

                    "titulo": "Información del Siniestro",

                    "filas": [

                        {"label": "Número", "valor": siniestro.numero_siniestro},

                        {"label": "Bien Afectado", "valor": siniestro.bien_nombre},

                        {

                            "label": "Fecha del Siniestro",

                            "valor": siniestro.fecha_siniestro.strftime("%d/%m/%Y"),

                        },

                        {

                            "label": "Estado Final",

                            "valor": siniestro.get_estado_display(),

                        },

                    ],

                },

                {

                    "titulo": "Resumen Financiero",

                    "filas": [

                        {

                            "label": "Monto Estimado",

                            "valor": f"${siniestro.monto_estimado:,.2f}",

                        },

                        {

                            "label": "Monto Indemnizado",

                            "valor": f"${(siniestro.monto_indemnizado or 0):,.2f}",

                        },

                        {

                            "label": "Valor Pagado",

                            "valor": f"${(siniestro.valor_pagado or 0):,.2f}",

                        },

                        {

                            "label": "Días de Gestión",

                            "valor": siniestro.dias_gestion,

                        },

                        {

                            "label": "Fecha de Liquidación",

                            "valor": (

                                siniestro.fecha_liquidacion.strftime("%d/%m/%Y")

                                if siniestro.fecha_liquidacion

                                else "N/A"

                            ),

                        },

                        {

                            "label": "Fecha de Pago",

                            "valor": (

                                siniestro.fecha_pago.strftime("%d/%m/%Y")

                                if siniestro.fecha_pago

                                else "N/A"

                            ),

                        },

                    ],

                },

            ],

            "cta_text": "Ver siniestro en el sistema",

            "cta_url": getattr(settings, "SITE_URL", "") + f"/siniestros/{siniestro.id}/detalle/",

            "nota": "Este reporte de cierre se genera automáticamente para fines de control y archivo.",

        }

        contenido_html = render_to_string("emails/base_notificacion.html", context)

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número: {siniestro.numero_siniestro}\n"

            f"Bien Afectado: {siniestro.bien_nombre}\n"

            f"Fecha del Siniestro: {siniestro.fecha_siniestro.strftime('%d/%m/%Y')}\n"

            f"Estado Final: {siniestro.get_estado_display()}\n"

            f"Monto Estimado: ${siniestro.monto_estimado:,.2f}\n"

            f"Monto Indemnizado: ${siniestro.monto_indemnizado or 0:,.2f}\n"

            f"Valor Pagado: ${siniestro.valor_pagado or 0:,.2f}\n"

        )

        for destinatario in destinatarios:

            notificacion = cls._crear_notificacion(

                tipo="siniestro_cierre",

                destinatario=destinatario,

                asunto=asunto,

                contenido=contenido_texto.strip(),

                contenido_html=contenido_html,

                siniestro=siniestro,

                usuario=usuario,

            )

            cls._enviar_email(notificacion)

            notificaciones.append(notificacion)

        return notificaciones

    @classmethod
    def verificar_alertas_siniestros(cls):

        """

        Verifica siniestros que requieren alertas automáticas.

        Diseñado para ejecutarse como tarea periódica (Celery).

        Returns:

            dict: Resumen de alertas generadas

        """

        resultados = {

            'alertas_respuesta': 0,

            'alertas_responsable': 0,

            'alertas_deposito': 0,

            'alertas_documentacion': 0,

            'errores': [],

        }

        # Siniestros con alerta de respuesta pendiente

        siniestros_sin_respuesta = Siniestro.objects.filter(

            estado='enviado_aseguradora',

            fecha_envio_aseguradora__isnull=False,

            fecha_respuesta_aseguradora__isnull=True,

        )

        for siniestro in siniestros_sin_respuesta:

            if siniestro.alerta_respuesta_aseguradora:

                try:

                    # Crear alerta

                    cls._crear_alerta_respuesta(siniestro)

                    resultados['alertas_respuesta'] += 1

                except Exception as e:

                    resultados['errores'].append(f"Siniestro {siniestro.numero_siniestro}: {str(e)}")

        # Siniestros que requieren notificar al responsable

        siniestros_pendientes = Siniestro.objects.filter(

            estado__in=['registrado', 'documentacion_pendiente', 'enviado_aseguradora', 'en_evaluacion'],

            fecha_notificacion_responsable__isnull=True,

        )

        for siniestro in siniestros_pendientes:

            if siniestro.alerta_notificar_responsable:

                try:

                    cls.notificar_responsable_bien(siniestro)

                    resultados['alertas_responsable'] += 1

                except Exception as e:

                    resultados['errores'].append(f"Siniestro {siniestro.numero_siniestro}: {str(e)}")

        # Siniestros con documentación pendiente: recordar cada 8 días

        siniestros_doc_pendiente = Siniestro.objects.filter(

            estado='documentacion_pendiente',

        )

        for siniestro in siniestros_doc_pendiente:

            dias = siniestro.dias_desde_registro

            if dias > 0 and dias % 8 == 0:

                try:

                    cls.notificar_documentacion_pendiente(siniestro)

                    resultados['alertas_documentacion'] += 1

                except Exception as e:

                    resultados['errores'].append(f"Siniestro {siniestro.numero_siniestro}: {str(e)}")

        # Siniestros con depósito pendiente

        siniestros_firmados = Siniestro.objects.filter(

            fecha_firma_indemnizacion__isnull=False,

            fecha_pago__isnull=True,

        )

        for siniestro in siniestros_firmados:

            if siniestro.alerta_deposito_pendiente:

                try:

                    cls._crear_alerta_deposito(siniestro)

                    resultados['alertas_deposito'] += 1

                except Exception as e:

                    resultados['errores'].append(f"Siniestro {siniestro.numero_siniestro}: {str(e)}")

        return resultados

    @classmethod
    def _crear_alerta_respuesta(cls, siniestro):

        """Crea una notificación de alerta por respuesta pendiente"""

        # Verificar si ya se envió una alerta reciente

        alerta_reciente = NotificacionEmail.objects.filter(

            tipo='alerta_respuesta',

            siniestro=siniestro,

            fecha_creacion__gte=timezone.now() - timedelta(days=2)

        ).exists()

        if alerta_reciente:

            return None

        email_broker = siniestro.email_broker or (

            siniestro.poliza.corredor_seguros.email if siniestro.poliza.corredor_seguros else None

        )

        if not email_broker:

            return None

        from django.template.loader import render_to_string

        asunto = f"ALERTA: Respuesta Pendiente - Siniestro {siniestro.numero_siniestro}"

        dias_espera = siniestro.dias_espera_respuesta

        context = {

            "titulo": asunto,

            "intro": [

                "El siguiente siniestro ha excedido el tiempo de espera para respuesta de la aseguradora.",

            ],

            "bloques": [

                {

                    "titulo": "Detalle de la Alerta",

                    "filas": [

                        {"label": "Número de Siniestro", "valor": siniestro.numero_siniestro},

                        {

                            "label": "Fecha de Envío a Aseguradora",

                            "valor": siniestro.fecha_envio_aseguradora.strftime("%d/%m/%Y"),

                        },

                        {

                            "label": "Días transcurridos desde envío",

                            "valor": dias_espera,

                        },

                    ],

                },

            ],

            "nota": "Por favor, dar seguimiento urgente con la aseguradora.",

        }

        contenido_html = render_to_string("emails/base_notificacion.html", context)

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número de Siniestro: {siniestro.numero_siniestro}\n"

            f"Días transcurridos desde envío: {dias_espera}\n"

        )

        notificacion = cls._crear_notificacion(

            tipo="alerta_respuesta",

            destinatario=email_broker,

            asunto=asunto,

            contenido=contenido_texto.strip(),

            contenido_html=contenido_html,

            siniestro=siniestro,

        )

        cls._enviar_email(notificacion)

        return notificacion

    @classmethod
    def _crear_alerta_deposito(cls, siniestro):

        """Crea una notificación de alerta por depósito pendiente"""

        # Verificar si ya se envió una alerta reciente

        alerta_reciente = NotificacionEmail.objects.filter(

            tipo='alerta_deposito',

            siniestro=siniestro,

            fecha_creacion__gte=timezone.now() - timedelta(days=1)

        ).exists()

        if alerta_reciente:

            return None

        email_broker = siniestro.email_broker or (

            siniestro.poliza.corredor_seguros.email if siniestro.poliza.corredor_seguros else None

        )

        if not email_broker:

            return None

        from django.template.loader import render_to_string

        asunto = f"ALERTA: Depósito Pendiente - Siniestro {siniestro.numero_siniestro}"

        horas_transcurridas = int(

            (timezone.now() - siniestro.fecha_firma_indemnizacion).total_seconds() / 3600

        )

        context = {

            "titulo": asunto,

            "intro": [

                "El siniestro tiene el recibo de indemnización firmado pero aún no se ha registrado el depósito.",

            ],

            "bloques": [

                {

                    "titulo": "Detalle de la Alerta",

                    "filas": [

                        {"label": "Número de Siniestro", "valor": siniestro.numero_siniestro},

                        {

                            "label": "Fecha de firma",

                            "valor": siniestro.fecha_firma_indemnizacion.strftime("%d/%m/%Y %H:%M"),

                        },

                        {

                            "label": "Horas transcurridas desde firma",

                            "valor": horas_transcurridas,

                        },

                        {"label": "Límite de depósito (horas)", "valor": 72},

                    ],

                },

            ],

            "nota": "Por favor, dar seguimiento al depósito de la indemnización.",

        }

        contenido_html = render_to_string("emails/base_notificacion.html", context)

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número de Siniestro: {siniestro.numero_siniestro}\n"

            f"Horas transcurridas desde firma: {horas_transcurridas}\n"

        )

        notificacion = cls._crear_notificacion(

            tipo="alerta_deposito",

            destinatario=email_broker,

            asunto=asunto,

            contenido=contenido_texto.strip(),

            contenido_html=contenido_html,

            siniestro=siniestro,

        )

        cls._enviar_email(notificacion)

        return notificacion

    @classmethod
    def notificar_vencimiento_poliza(cls, poliza, dias_antes=30, usuario=None):

        """

        Notifica sobre el próximo vencimiento de una póliza.

        Args:

            poliza: Instancia del modelo Poliza

            dias_antes: Días de anticipación para la notificación

            usuario: Usuario que realiza la acción

        Returns:

            NotificacionEmail: La notificación creada o None

        """

        email_broker = poliza.corredor_seguros.email if poliza.corredor_seguros else None

        if not email_broker:

            return None

        from django.template.loader import render_to_string

        asunto = f"Aviso de Vencimiento - Póliza {poliza.numero_poliza}"

        context = {

            "titulo": asunto,

            "intro": [

                "La siguiente póliza está próxima a vencer.",

            ],

            "bloques": [

                {

                    "titulo": "Información de la Póliza",

                    "filas": [

                        {"label": "Número", "valor": poliza.numero_poliza},

                        {

                            "label": "Aseguradora",

                            "valor": poliza.compania_aseguradora.nombre,

                        },

                        {"label": "Tipo", "valor": poliza.tipo_poliza.nombre},

                        {

                            "label": "Suma Asegurada",

                            "valor": f"${poliza.suma_asegurada:,.2f}",

                        },

                    ],

                },

                {

                    "titulo": "Vigencia",

                    "filas": [

                        {

                            "label": "Fecha de Inicio",

                            "valor": poliza.fecha_inicio.strftime("%d/%m/%Y"),

                        },

                        {

                            "label": "Fecha de Vencimiento",

                            "valor": poliza.fecha_fin.strftime("%d/%m/%Y"),

                        },

                        {

                            "label": "Días para vencer",

                            "valor": poliza.dias_para_vencer,

                        },

                    ],

                },

            ],

            "nota": "Por favor, iniciar el proceso de renovación con la debida anticipación.",

        }

        contenido_html = render_to_string("emails/base_notificacion.html", context)

        contenido_texto = (

            f"{asunto}\n\n"

            f"Número: {poliza.numero_poliza}\n"

            f"Aseguradora: {poliza.compania_aseguradora.nombre}\n"

            f"Tipo: {poliza.tipo_poliza.nombre}\n"

            f"Fecha de Vencimiento: {poliza.fecha_fin.strftime('%d/%m/%Y')}\n"

        )

        notificacion = cls._crear_notificacion(

            tipo="poliza_vencimiento",

            destinatario=email_broker,

            asunto=asunto,

            contenido=contenido_texto.strip(),

            contenido_html=contenido_html,

            poliza=poliza,

            usuario=usuario,

        )

        cls._enviar_email(notificacion)

        return notificacion

    @classmethod
    def reenviar_notificacion(cls, notificacion_id):

        """

        Reintenta enviar una notificación fallida.

        Args:

            notificacion_id: ID de la notificación a reenviar

        Returns:

            bool: True si se envió correctamente

        """

        try:

            notificacion = NotificacionEmail.objects.get(pk=notificacion_id)

            if notificacion.estado in ['fallido', 'pendiente']:

                return cls._enviar_email(notificacion)

            return False

        except NotificacionEmail.DoesNotExist:

            return False
