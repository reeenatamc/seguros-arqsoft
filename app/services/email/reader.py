"""

Servicio para lectura de correos IMAP - Reportes de Siniestros

Este módulo se conecta a una bandeja de entrada vía IMAP y extrae correos

que cumplan con la política de formato establecida para reportes de siniestros.

Política de formato:

- Asunto: Debe comenzar con [SINIESTRO] seguido de descripción libre

- Cuerpo: Debe contener campos estructurados entre delimitadores

Ejemplo de correo válido:

    Asunto: [SINIESTRO] Portátil no enciende

    Cuerpo:

    --- INICIO REPORTE ---

    RESPONSABLE: Jessica Roxana Yepez Velez

    FECHA_REPORTE: 15/01/2026

    PROBLEMA: Equipo no enciende debido a daño de mainboard

    CAUSA: Mala manipulación

    --- DATOS DEL EQUIPO ---

    PERIFERICO: Portátil

    MARCA: LENOVO

    MODELO: V14

    SERIE: PF22YXND

    --- FIN REPORTE ---

"""

import email
import imaplib
import logging
import re
from dataclasses import dataclass, field  # noqa: F401
from datetime import datetime
from email.header import decode_header
from typing import Any, Dict, List, Optional

from django.conf import settings

# Intentar importar mailparser, si no está disponible usar parsing básico

try:

    import mailparser

    MAILPARSER_AVAILABLE = True

except ImportError:

    MAILPARSER_AVAILABLE = False

logger = logging.getLogger("app")

# ==============================================================================

# EXCEPCIONES PERSONALIZADAS

# ==============================================================================


class IMAPConnectionError(Exception):
    """Error al conectar con el servidor IMAP."""

    pass


class IMAPAuthenticationError(Exception):
    """Error de autenticación con el servidor IMAP."""

    pass


class EmailParsingError(Exception):
    """Error al parsear el contenido del correo."""

    pass


class InvalidReportFormatError(Exception):
    """El correo no cumple con el formato de política establecido."""

    pass


# ==============================================================================

# ESTRUCTURAS DE DATOS

# ==============================================================================


@dataclass
class DatosEquipo:
    """Datos del equipo reportado en el siniestro."""

    periferico: str = ""

    marca: str = ""

    modelo: str = ""

    serie: str = ""

    activo: Optional[str] = None  # Opcional


@dataclass
class ReporteSiniestro:
    """Estructura de datos de un reporte de siniestro extraído del correo."""

    email_id: str

    subject: str

    from_address: str

    date: Optional[datetime]

    responsable: str

    fecha_reporte: str

    problema: str

    causa: str

    equipo: DatosEquipo

    raw_body: str = ""

    attachments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el reporte a diccionario."""

        return {
            "email_id": self.email_id,
            "subject": self.subject,
            "from_address": self.from_address,
            "date": self.date.isoformat() if self.date else None,
            "responsable": self.responsable,
            "fecha_reporte": self.fecha_reporte,
            "problema": self.problema,
            "causa": self.causa,
            "periferico": self.equipo.periferico,
            "marca": self.equipo.marca,
            "modelo": self.equipo.modelo,
            "serie": self.equipo.serie,
            "activo": self.equipo.activo,
            "raw_body": self.raw_body,
            "attachments": self.attachments,
        }


# ==============================================================================

# CLASE PRINCIPAL

# ==============================================================================


class EmailReaderService:
    """

    Servicio para leer y procesar correos de siniestros desde una bandeja IMAP.

    Uso:

        service = EmailReaderService()

        reportes = service.process_siniestro_emails(limit=10)

        for reporte in reportes:

            print(reporte.to_dict())

    """

    # Delimitadores del formato de política

    INICIO_REPORTE = "--- INICIO REPORTE ---"

    FIN_REPORTE = "--- FIN REPORTE ---"

    DATOS_EQUIPO = "--- DATOS DEL EQUIPO ---"

    # Campos requeridos en el reporte

    CAMPOS_REQUERIDOS = ["RESPONSABLE", "FECHA_REPORTE", "PROBLEMA", "CAUSA"]

    CAMPOS_EQUIPO = ["PERIFERICO", "MARCA", "MODELO", "SERIE"]

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        email_address: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = True,
    ):
        """

        Inicializa el servicio de lectura de correos.

        Args:

            host: Servidor IMAP (default: settings.IMAP_HOST)

            port: Puerto IMAP (default: settings.IMAP_PORT)

            email_address: Dirección de correo (default: settings.IMAP_EMAIL)

            password: Contraseña o App Password (default: settings.IMAP_PASSWORD)

            use_ssl: Usar conexión SSL (default: True)

        """

        self.host = host or getattr(settings, "IMAP_HOST", "imap.gmail.com")

        self.port = port or getattr(settings, "IMAP_PORT", 993)

        self.email_address = email_address or getattr(settings, "IMAP_EMAIL", "")

        self.password = password or getattr(settings, "IMAP_PASSWORD", "")

        self.use_ssl = use_ssl

        self.subject_tag = getattr(settings, "SINIESTRO_EMAIL_SUBJECT_TAG", "[SINIESTRO]")

        self._connection: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> None:
        """

        Establece conexión con el servidor IMAP.

        Raises:

            IMAPConnectionError: Si no se puede conectar al servidor

            IMAPAuthenticationError: Si las credenciales son inválidas

        """

        try:

            logger.info(f"Conectando a {self.host}:{self.port}...")

            if self.use_ssl:

                self._connection = imaplib.IMAP4_SSL(self.host, self.port)

            else:

                self._connection = imaplib.IMAP4(self.host, self.port)

            logger.info("Conexión establecida, autenticando...")

        except (imaplib.IMAP4.error, OSError, TimeoutError) as e:

            raise IMAPConnectionError(f"No se pudo conectar a {self.host}:{self.port}. Error: {str(e)}")

        try:

            self._connection.login(self.email_address, self.password)

            logger.info(f"Autenticación exitosa para {self.email_address}")

        except imaplib.IMAP4.error as e:

            raise IMAPAuthenticationError(
                f"Error de autenticación para {self.email_address}. " f"Verifica las credenciales. Error: {str(e)}"
            )

    def disconnect(self) -> None:
        """Cierra la conexión IMAP de forma segura."""

        if self._connection:

            try:

                self._connection.close()

                self._connection.logout()

                logger.info("Conexión IMAP cerrada correctamente")

            except Exception as e:

                logger.warning(f"Error al cerrar conexión IMAP: {e}")

            finally:

                self._connection = None

    def __enter__(self):
        """Context manager - conectar."""

        self.connect()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - desconectar."""

        self.disconnect()

        return False

    def search_siniestro_emails(self, folder: str = "INBOX", unseen_only: bool = False) -> List[bytes]:
        """

        Busca correos que contengan [SINIESTRO] en el asunto.

        Args:

            folder: Carpeta a buscar (default: INBOX)

            unseen_only: Solo buscar correos no leídos

        Returns:

            Lista de IDs de correos encontrados

        """

        if not self._connection:

            raise IMAPConnectionError("No hay conexión activa. Llama a connect() primero.")

        # Seleccionar carpeta

        status, _ = self._connection.select(folder)

        if status != "OK":

            raise IMAPConnectionError(f"No se pudo seleccionar la carpeta {folder}")

        # Construir criterio de búsqueda

        # Nota: IMAP no soporta búsqueda con caracteres especiales en SUBJECT directamente

        # Buscamos todos y filtramos después

        if unseen_only:

            search_criteria = "UNSEEN"

        else:

            search_criteria = "ALL"

        status, messages = self._connection.search(None, search_criteria)

        if status != "OK":

            return []

        email_ids = messages[0].split()

        logger.info(f"Encontrados {len(email_ids)} correos en {folder}")

        return email_ids

    def fetch_email(self, email_id: bytes) -> Dict[str, Any]:
        """

        Obtiene y parsea un correo específico.

        Args:

            email_id: ID del correo a obtener

        Returns:

            Diccionario con los datos del correo

        """

        if not self._connection:

            raise IMAPConnectionError("No hay conexión activa.")

        status, msg_data = self._connection.fetch(email_id, "(RFC822)")

        if status != "OK":

            raise EmailParsingError(f"No se pudo obtener el correo {email_id}")

        raw_email = msg_data[0][1]

        if MAILPARSER_AVAILABLE:

            return self._parse_with_mailparser(raw_email, email_id)

        else:

            return self._parse_with_email_lib(raw_email, email_id)

    def _parse_with_mailparser(self, raw_email: bytes, email_id: bytes) -> Dict[str, Any]:
        """Parsea el correo usando la librería mail-parser."""

        try:

            mail = mailparser.parse_from_bytes(raw_email)

            return {
                "email_id": email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                "subject": mail.subject or "",
                "from": mail.from_[0][1] if mail.from_ else "",
                "from_name": mail.from_[0][0] if mail.from_ else "",
                "date": mail.date,
                "body_text": mail.text_plain[0] if mail.text_plain else "",
                "body_html": mail.text_html[0] if mail.text_html else "",
                "attachments": [
                    {
                        "filename": att.get("filename", ""),
                        "content_type": att.get("mail_content_type", ""),
                        "payload": att.get("payload", b""),
                    }
                    for att in mail.attachments
                ],
            }

        except Exception as e:

            raise EmailParsingError(f"Error parseando correo con mailparser: {e}")

    def _parse_with_email_lib(self, raw_email: bytes, email_id: bytes) -> Dict[str, Any]:
        """Parsea el correo usando la librería estándar email."""

        try:

            msg = email.message_from_bytes(raw_email)

            # Decodificar asunto

            subject = ""

            subject_header = msg.get("Subject", "")

            if subject_header:

                decoded = decode_header(subject_header)

                subject = "".join(
                    part.decode(charset or "utf-8") if isinstance(part, bytes) else part for part, charset in decoded
                )

            # Obtener remitente

            from_header = msg.get("From", "")

            # Obtener fecha

            date_str = msg.get("Date", "")

            date = None

            if date_str:

                try:

                    date = email.utils.parsedate_to_datetime(date_str)

                except Exception:

                    pass

            # Extraer cuerpo del mensaje

            body_text = ""

            body_html = ""

            attachments = []

            if msg.is_multipart():

                for part in msg.walk():

                    content_type = part.get_content_type()

                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Capturar adjuntos y también imágenes inline
                    if "attachment" in content_disposition or content_type.startswith("image/"):
                        import base64

                        payload_data = part.get_payload(decode=True)

                        # Si decode=True no funcionó, intentar decodificar Base64 manualmente
                        if payload_data is None:
                            payload_data = part.get_payload()
                            if isinstance(payload_data, str):
                                try:
                                    payload_data = base64.b64decode(payload_data)
                                except:
                                    payload_data = None

                        # Verificar si el payload existe y tiene tamaño razonable
                        if payload_data and len(payload_data) > 100:
                            # Headers válidos de imágenes binarias
                            valid_headers = [
                                b"\xff\xd8\xff",  # JPEG (cualquier variante)
                                b"\x89PNG",  # PNG
                                b"RIFF",  # WEBP
                                b"GIF8",  # GIF
                            ]

                            # Verificar si YA es una imagen válida
                            is_valid_image = any(payload_data.startswith(h) for h in valid_headers)

                            # Si no es imagen válida, puede ser Base64 (texto ASCII)
                            if not is_valid_image:
                                # Patrones Base64 comunes para imágenes
                                # /9j/ = JPEG, iVBOR = PNG, UklG = WEBP, R0lG = GIF
                                b64_patterns = [b"/9j/", b"iVBOR", b"UklG", b"R0lG"]
                                looks_like_base64 = any(payload_data.startswith(p) for p in b64_patterns)

                                if looks_like_base64:
                                    try:
                                        decoded = base64.b64decode(payload_data)
                                        if any(decoded.startswith(h) for h in valid_headers):
                                            payload_data = decoded
                                    except:
                                        pass

                            attachments.append(
                                {
                                    "filename": part.get_filename() or f"imagen.{content_type.split('/')[-1]}",
                                    "content_type": content_type,
                                    "payload": payload_data,
                                }
                            )

                    elif content_type == "text/plain":

                        payload = part.get_payload(decode=True)

                        if payload:

                            charset = part.get_content_charset() or "utf-8"

                            body_text = payload.decode(charset, errors="replace")

                    elif content_type == "text/html":

                        payload = part.get_payload(decode=True)

                        if payload:

                            charset = part.get_content_charset() or "utf-8"

                            body_html = payload.decode(charset, errors="replace")

            else:

                payload = msg.get_payload(decode=True)

                if payload:

                    charset = msg.get_content_charset() or "utf-8"

                    if msg.get_content_type() == "text/html":

                        body_html = payload.decode(charset, errors="replace")

                    else:

                        body_text = payload.decode(charset, errors="replace")

            return {
                "email_id": email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                "subject": subject,
                "from": from_header,
                "from_name": "",
                "date": date,
                "body_text": body_text,
                "body_html": body_html,
                "attachments": attachments,
            }

        except Exception as e:

            raise EmailParsingError(f"Error parseando correo: {e}")

    def extract_report_data(self, body_text: str) -> Dict[str, str]:
        """

        Extrae los datos estructurados del cuerpo del correo.

        Busca el contenido entre los delimitadores y parsea los campos

        CAMPO: valor.

        Args:

            body_text: Texto plano del cuerpo del correo

        Returns:

            Diccionario con los campos extraídos

        Raises:

            InvalidReportFormatError: Si el formato no es válido

        """

        # Buscar delimitadores

        inicio_match = body_text.find(self.INICIO_REPORTE)

        fin_match = body_text.find(self.FIN_REPORTE)

        if inicio_match == -1 or fin_match == -1:

            raise InvalidReportFormatError(
                f"El correo no contiene los delimitadores requeridos: "
                f"'{self.INICIO_REPORTE}' y '{self.FIN_REPORTE}'"
            )

        # Extraer contenido entre delimitadores

        report_content = body_text[inicio_match + len(self.INICIO_REPORTE) : fin_match]

        # Parsear campos CAMPO: valor

        data = {}

        pattern = r"^([A-Z_]+):\s*(.+?)$"

        for line in report_content.split("\n"):

            line = line.strip()

            if not line or line == self.DATOS_EQUIPO:

                continue

            match = re.match(pattern, line)

            if match:

                campo = match.group(1).strip()

                valor = match.group(2).strip()

                data[campo] = valor

        return data

    def validate_report_data(self, data: Dict[str, str]) -> List[str]:
        """

        Valida que el reporte contenga todos los campos requeridos.

        Args:

            data: Diccionario con los datos extraídos

        Returns:

            Lista de campos faltantes (vacía si todo está bien)

        """

        missing = []

        for campo in self.CAMPOS_REQUERIDOS:

            if campo not in data or not data[campo]:

                missing.append(campo)

        for campo in self.CAMPOS_EQUIPO:

            if campo not in data or not data[campo]:

                missing.append(campo)

        return missing

    def parse_siniestro_email(self, email_data: Dict[str, Any]) -> Optional[ReporteSiniestro]:
        """

        Convierte los datos del correo en un ReporteSiniestro.

        Args:

            email_data: Datos del correo obtenidos con fetch_email

        Returns:

            ReporteSiniestro si el correo es válido, None si no cumple el formato

        """

        subject = email_data.get("subject", "")

        # Verificar que el asunto contenga el tag de siniestro

        if self.subject_tag not in subject:

            logger.debug(f"Correo ignorado - no contiene {self.subject_tag}: {subject}")

            return None

        body_text = email_data.get("body_text", "")

        if not body_text:

            logger.warning(f"Correo sin cuerpo de texto: {subject}")

            return None

        try:

            # Extraer datos del reporte

            data = self.extract_report_data(body_text)

            # Validar campos requeridos

            missing = self.validate_report_data(data)

            if missing:

                logger.warning(f"Correo con campos faltantes: {subject}. " f"Campos faltantes: {', '.join(missing)}")

                # Continuamos pero registramos la advertencia

            # Construir objeto de reporte

            equipo = DatosEquipo(
                periferico=data.get("PERIFERICO", ""),
                marca=data.get("MARCA", ""),
                modelo=data.get("MODELO", ""),
                serie=data.get("SERIE", ""),
                activo=data.get("ACTIVO"),
            )

            reporte = ReporteSiniestro(
                email_id=email_data.get("email_id", ""),
                subject=subject,
                from_address=email_data.get("from", ""),
                date=email_data.get("date"),
                responsable=data.get("RESPONSABLE", ""),
                fecha_reporte=data.get("FECHA_REPORTE", ""),
                problema=data.get("PROBLEMA", ""),
                causa=data.get("CAUSA", ""),
                equipo=equipo,
                raw_body=body_text,
                attachments=email_data.get("attachments", []),
            )

            return reporte

        except InvalidReportFormatError as e:

            logger.warning(f"Formato inválido en correo '{subject}': {e}")

            return None

        except Exception as e:

            logger.error(f"Error procesando correo '{subject}': {e}")

            return None

    def process_siniestro_emails(
        self, folder: str = "INBOX", limit: Optional[int] = None, unseen_only: bool = False, mark_as_read: bool = False
    ) -> List[ReporteSiniestro]:
        """

        Procesa todos los correos de siniestros en la bandeja.

        Esta es la función principal que orquesta todo el proceso:

        1. Busca correos en la carpeta especificada

        2. Filtra los que contienen [SINIESTRO] en el asunto

        3. Extrae y valida los datos de cada correo

        4. Retorna lista de reportes procesados

        Args:

            folder: Carpeta a procesar (default: INBOX)

            limit: Máximo de correos a procesar (None = todos)

            unseen_only: Solo procesar correos no leídos

            mark_as_read: Marcar correos procesados como leídos

        Returns:

            Lista de ReporteSiniestro con los datos extraídos

        """

        reportes = []

        procesados = 0

        ignorados = 0

        errores = 0

        # Buscar correos

        email_ids = self.search_siniestro_emails(folder, unseen_only)

        if not email_ids:

            logger.info("No se encontraron correos para procesar")

            return reportes

        # Aplicar límite si se especificó

        if limit:

            email_ids = email_ids[-limit:]  # Los más recientes

        total = len(email_ids)

        logger.info(f"Procesando {total} correos...")

        for i, email_id in enumerate(email_ids, 1):

            try:

                # Obtener correo

                email_data = self.fetch_email(email_id)

                # Parsear como reporte de siniestro

                reporte = self.parse_siniestro_email(email_data)

                if reporte:

                    reportes.append(reporte)

                    procesados += 1

                    logger.info(
                        f"[{i}/{total}] ✓ Procesado: {reporte.subject[:50]}... " f"(Serie: {reporte.equipo.serie})"
                    )

                    # Marcar como leído si se solicita

                    if mark_as_read and self._connection:

                        self._connection.store(email_id, "+FLAGS", "\\Seen")

                else:

                    ignorados += 1

            except Exception as e:

                errores += 1

                logger.error(f"[{i}/{total}] ✗ Error: {e}")

        logger.info(f"\nResumen: {procesados} procesados, {ignorados} ignorados, {errores} errores")

        return reportes


# ==============================================================================

# FUNCIONES DE CONVENIENCIA

# ==============================================================================


def leer_correos_siniestros(
    limit: int = 10, unseen_only: bool = False, mark_as_read: bool = False
) -> List[Dict[str, Any]]:
    """

    Función de conveniencia para leer correos de siniestros.

    Args:

        limit: Máximo de correos a procesar

        unseen_only: Solo correos no leídos

        mark_as_read: Marcar como leídos después de procesar

    Returns:

        Lista de diccionarios con los datos de cada siniestro

    Example:

        >>> from app.services.email_reader import leer_correos_siniestros

        >>> siniestros = leer_correos_siniestros(limit=5)

        >>> for sin in siniestros:

        ...     print(sin['responsable'], sin['serie'])

    """

    try:

        with EmailReaderService() as service:

            reportes = service.process_siniestro_emails(limit=limit, unseen_only=unseen_only, mark_as_read=mark_as_read)

            return [r.to_dict() for r in reportes]

    except IMAPConnectionError as e:

        logger.error(f"Error de conexión IMAP: {e}")

        raise

    except IMAPAuthenticationError as e:

        logger.error(f"Error de autenticación IMAP: {e}")

        raise

    except Exception as e:

        logger.error(f"Error inesperado: {e}")

        raise


def guardar_reporte_en_bd(reporte: ReporteSiniestro, intentar_crear_siniestro: bool = True):
    """

    Guarda un reporte de siniestro en la base de datos.

    Args:

        reporte: ReporteSiniestro extraído del correo

        intentar_crear_siniestro: Si True, intenta crear el siniestro automáticamente

    Returns:

        tuple: (SiniestroEmail, Siniestro o None, mensaje)

    """

    from django.core.files.base import ContentFile

    from app.models import AdjuntoSiniestro, SiniestroEmail

    # Verificar si ya existe un registro con este email_id

    existente = SiniestroEmail.objects.filter(email_id=reporte.email_id).first()

    if existente:

        logger.info(f"Correo ya procesado anteriormente: {reporte.email_id}")

        return existente, existente.siniestro_creado, "Correo ya procesado anteriormente"

    # Crear registro de SiniestroEmail

    siniestro_email = SiniestroEmail.objects.create(
        email_id=reporte.email_id,
        email_subject=reporte.subject,
        email_from=reporte.from_address,
        email_date=reporte.date,
        email_body=reporte.raw_body,
        responsable_nombre=reporte.responsable,
        fecha_reporte=reporte.fecha_reporte,
        problema=reporte.problema,
        causa=reporte.causa,
        periferico=reporte.equipo.periferico,
        marca=reporte.equipo.marca,
        modelo=reporte.equipo.modelo,
        serie=reporte.equipo.serie,
        codigo_activo=reporte.equipo.activo or "",
    )

    logger.info(f"Registro SiniestroEmail creado: {siniestro_email.id}")

    # Intentar crear siniestro automáticamente

    siniestro = None

    mensaje = "Guardado como pendiente de revisión"

    if intentar_crear_siniestro:

        siniestro, mensaje = siniestro_email.crear_siniestro_automatico()

        if siniestro:

            logger.info(f"Siniestro creado automáticamente: {siniestro.numero_siniestro}")

            # Guardar imágenes adjuntas del email como AdjuntoSiniestro
            import base64

            adjuntos_guardados = 0
            for adjunto in reporte.attachments:
                filename = adjunto.get("filename", "adjunto")
                content_type = adjunto.get("content_type", "")
                payload = adjunto.get("payload")

                # Solo procesar imágenes
                if payload and content_type.startswith("image/"):
                    try:
                        # Decodificar Base64 si es necesario
                        image_data = payload

                        # Headers válidos de imágenes binarias
                        valid_headers = [
                            b"\xff\xd8\xff",  # JPEG
                            b"\x89PNG",  # PNG
                            b"RIFF",  # WEBP
                            b"GIF8",  # GIF
                        ]

                        # Verificar si ya es binario válido
                        is_valid_binary = any(image_data.startswith(h) for h in valid_headers)

                        # Si no es binario válido, intentar decodificar Base64
                        if not is_valid_binary:
                            try:
                                # Puede ser bytes que representan texto Base64
                                if isinstance(image_data, bytes):
                                    image_data = base64.b64decode(image_data)
                                elif isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data.encode())
                            except Exception as decode_err:
                                logger.warning(f"No se pudo decodificar Base64: {decode_err}")

                        adjunto_siniestro = AdjuntoSiniestro(
                            siniestro=siniestro,
                            tipo_adjunto="fotos",
                            nombre=filename,
                            descripcion="Imagen adjunta del reporte por email",
                        )
                        adjunto_siniestro.archivo.save(filename, ContentFile(image_data), save=True)
                        adjuntos_guardados += 1
                        logger.info(f"Adjunto guardado: {filename}")
                    except Exception as e:
                        logger.warning(f"Error guardando adjunto {filename}: {e}")

            if adjuntos_guardados > 0:
                logger.info(f"Se guardaron {adjuntos_guardados} imágenes adjuntas")

        else:

            logger.warning(f"No se pudo crear siniestro automáticamente: {mensaje}")

    return siniestro_email, siniestro, mensaje


def procesar_y_guardar_correos(
    limit: int = 10, unseen_only: bool = False, mark_as_read: bool = False, crear_siniestros: bool = True
) -> Dict[str, Any]:
    """

    Lee correos de siniestros y los guarda en la base de datos.

    Args:

        limit: Máximo de correos a procesar

        unseen_only: Solo correos no leídos

        mark_as_read: Marcar como leídos después de procesar

        crear_siniestros: Intentar crear siniestros automáticamente

    Returns:

        Diccionario con estadísticas del procesamiento

    """

    resultados = {
        "total_procesados": 0,
        "siniestros_creados": 0,
        "pendientes_revision": 0,
        "ya_existentes": 0,
        "errores": 0,
        "detalles": [],
    }

    try:

        with EmailReaderService() as service:

            reportes = service.process_siniestro_emails(limit=limit, unseen_only=unseen_only, mark_as_read=mark_as_read)

            for reporte in reportes:

                try:

                    siniestro_email, siniestro, mensaje = guardar_reporte_en_bd(
                        reporte, intentar_crear_siniestro=crear_siniestros
                    )

                    resultados["total_procesados"] += 1

                    if siniestro:

                        resultados["siniestros_creados"] += 1

                    elif siniestro_email.estado_procesamiento == "pendiente":

                        resultados["pendientes_revision"] += 1

                    if "ya procesado" in mensaje.lower():

                        resultados["ya_existentes"] += 1

                    resultados["detalles"].append(
                        {
                            "email_id": reporte.email_id,
                            "subject": reporte.subject,
                            "serie": reporte.equipo.serie,
                            "estado": siniestro_email.estado_procesamiento,
                            "siniestro_id": siniestro.id if siniestro else None,
                            "mensaje": mensaje,
                        }
                    )

                except Exception as e:

                    resultados["errores"] += 1

                    resultados["detalles"].append(
                        {
                            "email_id": reporte.email_id,
                            "subject": reporte.subject,
                            "serie": reporte.equipo.serie,
                            "estado": "error",
                            "siniestro_id": None,
                            "mensaje": str(e),
                        }
                    )

                    logger.error(f"Error guardando reporte: {e}")

            return resultados

    except Exception as e:

        logger.error(f"Error en procesar_y_guardar_correos: {e}")

        raise
