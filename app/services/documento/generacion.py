"""

Servicio de Generación de Documentos.

Gestiona la generación de documentos Word, PDF y firma electrónica.

"""

import hashlib

import os

from io import BytesIO, StringIO

from datetime import datetime

from django.conf import settings

from django.utils import timezone

from django.http import HttpResponse

from django.contrib.staticfiles import finders

from app.models import Siniestro, AdjuntoSiniestro, ConfiguracionSistema

try:

    # Usamos plantillas Word con docxtpl

    from docxtpl import DocxTemplate, InlineImage

    from docx.shared import Mm

    DOCX_AVAILABLE = True

except ImportError:

    DOCX_AVAILABLE = False


class DocumentosService:

    """Servicio para generación y gestión de documentos"""

    @staticmethod
    def _verificar_docx():

        """Verifica que docxtpl esté disponible"""

        if not DOCX_AVAILABLE:

            raise ImportError(

                "La librería docxtpl no está instalada. "

                "Ejecute: pip install docxtpl"

            )

    @staticmethod
    def _get_template_path(filename):

        """

        Busca la plantilla .docx en ubicaciones conocidas.

        Prioridad:

          1) Staticfiles: 'docx/<filename>'

          2) <BASE_DIR>/templates/docx/<filename>

          3) <BASE_DIR>/doc_templates/word/<filename>  (para compatibilidad)

        """

        # 1) Buscar en static (recomendado)

        candidate = finders.find(f'docx/{filename}')

        if candidate and os.path.exists(candidate):

            return candidate

        # 2) Directorio de templates del proyecto

        candidate = os.path.join(settings.BASE_DIR, 'templates', 'docx', filename)

        if os.path.exists(candidate):

            return candidate

        # 3) Directorio de plantillas legacy en la raíz

        candidate = os.path.join(settings.BASE_DIR, 'doc_templates', 'word', filename)

        if os.path.exists(candidate):

            return candidate

        raise FileNotFoundError(

            f"No se encontró la plantilla Word '{filename}'. "

            f"Ubícala en 'templates/docx/' o en 'doc_templates/word/'."

        )

    @staticmethod
    def _formatear_fecha_es(fecha, con_hora=False):

        """

        Devuelve una fecha en español, sin depender del locale del sistema.

        Ej:

          20 de enero de 2026

          20/01/2026 14:35

        """

        if not fecha:

            return ""

        meses = [

            "enero", "febrero", "marzo", "abril", "mayo", "junio",

            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",

        ]

        mes_nombre = meses[fecha.month - 1]

        if con_hora:

            return f"{fecha.day:02d}/{fecha.month:02d}/{fecha.year} {fecha.hour:02d}:{fecha.minute:02d}"

        # Formato tipo "20 de enero de 2026"

        return f"{fecha.day} de {mes_nombre} de {fecha.year}"

    @classmethod
    def generar_carta_formal_siniestro(cls, siniestro, destinatario_nombre=None,

                                        destinatario_cargo=None):

        """

        Genera una carta formal de notificación de siniestro usando

        una plantilla Word (.docx) con docxtpl.

        La plantilla debe llamarse 'plantilla_carta_siniestro.docx'.

        """

        cls._verificar_docx()

        # 1. Cargar la plantilla diseñada estéticamente

        # Usamos el nombre actual del archivo: 'carta_formal.docx'

        ruta_plantilla = cls._get_template_path('carta_formal.docx')

        doc = DocxTemplate(ruta_plantilla)

        # 2. Preparar el contexto (diccionario de datos)

        firmante_nombre = ConfiguracionSistema.get_config('FIRMANTE_CARTA_NOMBRE', '')

        firmante_cargo = ConfiguracionSistema.get_config('FIRMANTE_CARTA_CARGO', '')

        context = {

            # Fechas en español

            'fecha_actual': cls._formatear_fecha_es(timezone.now()),

            'destinatario_nombre': destinatario_nombre or "A quien corresponda",

            'destinatario_cargo': destinatario_cargo or "",

            'nro_siniestro': siniestro.numero_siniestro,

            'nro_poliza': siniestro.poliza.numero_poliza,

            'fecha_siniestro': cls._formatear_fecha_es(siniestro.fecha_siniestro),

            # Datos del cuadro resumen

            'tipo_siniestro': siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else "N/A",

            'ubicacion': siniestro.ubicacion,

            'bien_afectado': siniestro.bien_nombre,

            'marca_modelo': f"{siniestro.bien_marca or ''} {siniestro.bien_modelo or ''}".strip(),

            'serie': siniestro.bien_serie or "N/A",

            'monto_estimado': f"${siniestro.monto_estimado:,.2f}",

            'descripcion': siniestro.descripcion_detallada,

            'causa': siniestro.causa,

            # Aliases genéricos

            'tipo_equipo': siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else "N/A",

            'marca': siniestro.bien_marca or "",

            'modelo': siniestro.bien_modelo or "",

            'activo': siniestro.bien_codigo_activo or "",

            'responsable': getattr(siniestro.responsable_custodio, "nombre", "") or "",

            'descripcion_incidente': siniestro.descripcion_detallada,

            # === Aliases EXACTOS para tu plantilla Word ===

            # Encabezado

            'codigo_oficio': siniestro.numero_siniestro,

            'aseguradora_nombre': siniestro.poliza.compania_aseguradora.nombre,

            # Detalle del equipo

            'bien_tipo': siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else "N/A",

            'bien_marca': siniestro.bien_marca or "",

            'bien_modelo': siniestro.bien_modelo or "",

            'bien_serie': siniestro.bien_serie or "",

            'bien_activo': siniestro.bien_codigo_activo or "",

            # Responsable y causa

            'responsable_nombre': getattr(siniestro.responsable_custodio, "nombre", "") or "",

            'causa_siniestro': siniestro.causa,

            # Firmante (configurable en ConfiguracionSistema)

            'firmante_nombre': firmante_nombre or getattr(siniestro.responsable_custodio, "nombre", "") or "",

            'firmante_cargo': firmante_cargo or (

                getattr(siniestro.responsable_custodio, "cargo", "") if hasattr(siniestro.responsable_custodio, "cargo") else ""

            ),

        }

        # 3. Renderizar plantilla

        doc.render(context)

        # 4. Guardar en buffer

        buffer = BytesIO()

        doc.save(buffer)

        buffer.seek(0)

        return buffer

    @classmethod
    def generar_recibo_indemnizacion(cls, siniestro):

        """

        Genera un recibo de indemnización usando una plantilla Word (.docx).

        La plantilla debe llamarse 'plantilla_recibo_indemnizacion.docx'.

        """

        cls._verificar_docx()

        # 1. Cargar plantilla

        ruta_plantilla = cls._get_template_path('plantilla_recibo_indemnizacion.docx')

        doc = DocxTemplate(ruta_plantilla)

        monto_indemnizacion = (

            siniestro.monto_indemnizado

            or getattr(siniestro, 'valor_indemnizacion_calculado', None)

            or 0

        )

        # 2. Contexto para la plantilla

        firmante_nombre = ConfiguracionSistema.get_config('FIRMANTE_CARTA_NOMBRE', '')

        firmante_cargo = ConfiguracionSistema.get_config('FIRMANTE_CARTA_CARGO', '')

        context = {

            'nro_recibo': f"{siniestro.numero_siniestro}-IND",

            'fecha_actual': timezone.now().strftime('%d de %B de %Y'),

            # Datos Tabla Superior

            'nro_siniestro': siniestro.numero_siniestro,

            'nro_poliza': siniestro.poliza.numero_poliza,

            'aseguradora': siniestro.poliza.compania_aseguradora.nombre,

            'bien': siniestro.bien_nombre,

            'fecha_siniestro': siniestro.fecha_siniestro.strftime('%d/%m/%Y'),

            'monto_indemnizar': f"${monto_indemnizacion:,.2f}",

            # Datos Desglose (Cálculos)

            'val_reclamo': f"${(siniestro.valor_reclamo or 0):,.2f}",

            'val_deducible': f"${(siniestro.deducible or 0):,.2f}",

            'val_depreciacion': f"${(siniestro.depreciacion or 0):,.2f}",

            'total_final': f"${monto_indemnizacion:,.2f}",

            # Texto legal dinámico

            'monto_texto': f"${monto_indemnizacion:,.2f}",

            'aseguradora_nombre': siniestro.poliza.compania_aseguradora.nombre,

            # Firmante en el recibo

            'firmante_nombre': firmante_nombre,

            'firmante_cargo': firmante_cargo,

        }

        # 3. Renderizar

        doc.render(context)

        # 4. Guardar en buffer

        buffer = BytesIO()

        doc.save(buffer)

        buffer.seek(0)

        return buffer

    @staticmethod
    def calcular_hash_archivo(archivo):

        """

        Calcula el hash SHA256 de un archivo.

        Args:

            archivo: Archivo a procesar (FileField o path)

        Returns:

            str: Hash SHA256 en hexadecimal

        """

        hasher = hashlib.sha256()

        if hasattr(archivo, 'chunks'):

            # Es un FileField de Django

            for chunk in archivo.chunks():

                hasher.update(chunk)

        elif hasattr(archivo, 'read'):

            # Es un archivo abierto

            for chunk in iter(lambda: archivo.read(4096), b''):

                hasher.update(chunk)

        elif isinstance(archivo, (str, bytes)):

            if isinstance(archivo, str):

                archivo = archivo.encode()

            hasher.update(archivo)

        else:

            raise ValueError("Tipo de archivo no soportado")

        return hasher.hexdigest()

    @classmethod
    def aplicar_firma_electronica(cls, adjunto, usuario, ip=None):

        """

        Aplica una firma electrónica a un documento adjunto.

        Args:

            adjunto: Instancia de AdjuntoSiniestro

            usuario: Usuario que firma

            ip: Dirección IP del firmante (opcional)

        Returns:

            AdjuntoSiniestro: El adjunto actualizado

        """

        if not adjunto.archivo:

            raise ValueError("El adjunto no tiene archivo asociado")

        if adjunto.firmado:

            raise ValueError("El documento ya está firmado")

        # Calcular hash del archivo

        hash_firma = cls.calcular_hash_archivo(adjunto.archivo)

        # Actualizar el adjunto

        adjunto.hash_firma = hash_firma

        adjunto.firmado = True

        adjunto.fecha_firma = timezone.now()

        adjunto.firmado_por = usuario

        adjunto.ip_firma = ip

        adjunto.save()

        return adjunto

    @classmethod
    def verificar_firma(cls, adjunto):

        """

        Verifica la integridad de un documento firmado.

        Args:

            adjunto: Instancia de AdjuntoSiniestro

        Returns:

            dict: Resultado de la verificación

        """

        if not adjunto.firmado or not adjunto.hash_firma:

            return {

                'valido': False,

                'mensaje': 'El documento no tiene firma electrónica',

            }

        if not adjunto.archivo:

            return {

                'valido': False,

                'mensaje': 'El archivo no existe',

            }

        # Calcular hash actual

        hash_actual = cls.calcular_hash_archivo(adjunto.archivo)

        # Comparar

        es_valido = hash_actual == adjunto.hash_firma

        return {

            'valido': es_valido,

            'mensaje': 'Firma válida - Documento íntegro' if es_valido else 'ALERTA: El documento ha sido modificado',

            'hash_original': adjunto.hash_firma,

            'hash_actual': hash_actual,

            'fecha_firma': adjunto.fecha_firma,

            'firmado_por': adjunto.firmado_por.get_full_name() if adjunto.firmado_por else 'Desconocido',

        }

    @classmethod
    def descargar_carta_siniestro(cls, siniestro):

        """

        Genera y retorna una respuesta HTTP con la carta de siniestro.

        Args:

            siniestro: Instancia del modelo Siniestro

        Returns:

            HttpResponse: Respuesta con el archivo Word

        """

        buffer = cls.generar_carta_formal_siniestro(siniestro)

        response = HttpResponse(

            buffer.getvalue(),

            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        )

        response['Content-Disposition'] = f'attachment; filename="carta_siniestro_{siniestro.numero_siniestro}.docx"'

        return response

    @classmethod
    def descargar_recibo_indemnizacion(cls, siniestro):

        """

        Genera y retorna una respuesta HTTP con el recibo de indemnización.

        Args:

            siniestro: Instancia del modelo Siniestro

        Returns:

            HttpResponse: Respuesta con el archivo Word

        """

        buffer = cls.generar_recibo_indemnizacion(siniestro)

        response = HttpResponse(

            buffer.getvalue(),

            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        )

        response['Content-Disposition'] = f'attachment; filename="recibo_indemnizacion_{siniestro.numero_siniestro}.docx"'

        return response

    @classmethod
    def crear_adjunto_desde_buffer(cls, siniestro, buffer, tipo_adjunto, nombre, usuario):

        """

        Crea un AdjuntoSiniestro desde un buffer de documento.

        Args:

            siniestro: Instancia del Siniestro

            buffer: BytesIO con el contenido del archivo

            tipo_adjunto: Tipo de adjunto

            nombre: Nombre del documento

            usuario: Usuario que crea el adjunto

        Returns:

            AdjuntoSiniestro: El adjunto creado

        """

        from django.core.files.base import ContentFile

        contenido = buffer.getvalue()

        archivo = ContentFile(contenido, name=f"{nombre}.docx")

        adjunto = AdjuntoSiniestro.objects.create(

            siniestro=siniestro,

            tipo_adjunto=tipo_adjunto,

            nombre=nombre,

            archivo=archivo,

            subido_por=usuario,

            requiere_firma=tipo_adjunto in ['carta_formal', 'recibo_indemnizacion'],

        )

        return adjunto
