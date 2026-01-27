"""
Servicio para leer y procesar recibos de indemnización desde el inbox IMAP.
Busca emails con asunto "RECIBO DE INDEMNIZACIÓN" y parsea el PDF adjunto.
"""

import email
import imaplib
import logging
import re
from dataclasses import dataclass
from email.header import decode_header
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from django.conf import settings
from django.utils import timezone

if TYPE_CHECKING:
    from app.models import Siniestro

logger = logging.getLogger(__name__)


@dataclass
class ReciboIndemnizacion:
    """Datos extraídos de un recibo de indemnización."""

    email_id: bytes
    from_address: str
    subject: str
    date: Optional[str]
    numero_reclamo: Optional[str] = None
    numero_serie: Optional[str] = None
    codigo_activo: Optional[str] = None
    valor_indemnizacion: Optional[float] = None  # LA SUMA DE (monto neto final)
    perdida_bruta: Optional[float] = None  # Valor Pérdida Bruta
    deducible: Optional[float] = None  # Deducible aplicado
    depreciacion: Optional[float] = None  # Depreciación aplicada
    pdf_content: Optional[bytes] = None
    pdf_filename: Optional[str] = None


class RecibosIndemnizacionService:
    """
    Servicio para procesar recibos de indemnización desde el inbox IMAP.
    """

    ASUNTO_RECIBO = "RECIBO DE INDEMNIZACIÓN"

    def __init__(self):
        self._connection: Optional[imaplib.IMAP4_SSL] = None
        self._host = getattr(settings, "EMAIL_IMAP_HOST", "imap.gmail.com")
        self._port = getattr(settings, "EMAIL_IMAP_PORT", 993)
        self._user = getattr(settings, "EMAIL_HOST_USER", "")
        self._password = getattr(settings, "EMAIL_HOST_PASSWORD", "")

    def connect(self) -> bool:
        """Establece conexión IMAP."""
        try:
            self._connection = imaplib.IMAP4_SSL(self._host, self._port)
            self._connection.login(self._user, self._password)
            logger.info("Conexión IMAP establecida para recibos")
            return True
        except Exception as e:
            logger.error(f"Error conectando IMAP: {e}")
            return False

    def disconnect(self):
        """Cierra la conexión IMAP."""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def buscar_emails_recibos(self) -> List[bytes]:
        """Busca emails no leídos con asunto de recibo de indemnización."""
        if not self._connection:
            return []

        try:
            self._connection.select("INBOX")
            # Buscar por asunto - usar versión sin acentos para compatibilidad IMAP
            # También buscar la versión con acentos usando CHARSET UTF-8
            search_criteria = '(UNSEEN SUBJECT "RECIBO DE INDEMNIZACION")'
            status, messages = self._connection.search("UTF-8", search_criteria)

            if status != "OK" or not messages[0]:
                # Intentar con charset por defecto
                search_criteria = '(UNSEEN SUBJECT "RECIBO")'
                status, messages = self._connection.search(None, search_criteria)

            if status != "OK":
                return []

            return messages[0].split() if messages[0] else []
        except Exception as e:
            logger.error(f"Error buscando emails de recibos: {e}")
            return []

    def procesar_email(self, email_id: bytes) -> Optional[ReciboIndemnizacion]:
        """Procesa un email y extrae los datos del recibo."""
        if not self._connection:
            return None

        try:
            status, msg_data = self._connection.fetch(email_id, "(RFC822)")
            if status != "OK":
                return None

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decodificar asunto
            subject_parts = decode_header(msg.get("Subject", ""))
            subject = ""
            for part, encoding in subject_parts:
                if isinstance(part, bytes):
                    subject += part.decode(encoding or "utf-8", errors="replace")
                else:
                    subject += str(part)

            # Verificar que sea un recibo de indemnización (aceptar con o sin acento)
            subject_lower = subject.lower()
            if "recibo" not in subject_lower or "indemnizaci" not in subject_lower:
                return None

            # Obtener remitente
            from_address = msg.get("From", "")

            # Obtener fecha
            date_str = msg.get("Date", "")

            recibo = ReciboIndemnizacion(email_id=email_id, from_address=from_address, subject=subject, date=date_str)

            # Buscar adjunto PDF
            for part in msg.walk():
                content_type = part.get_content_type()
                filename = part.get_filename()

                if content_type == "application/pdf" or (filename and filename.lower().endswith(".pdf")):
                    pdf_data = part.get_payload(decode=True)
                    if pdf_data:
                        recibo.pdf_content = pdf_data
                        recibo.pdf_filename = filename or "recibo.pdf"

                        # Parsear el PDF
                        datos_pdf = self._parsear_pdf(pdf_data)
                        if datos_pdf:
                            recibo.numero_reclamo = datos_pdf.get("numero_reclamo")
                            recibo.numero_serie = datos_pdf.get("numero_serie")
                            recibo.codigo_activo = datos_pdf.get("codigo_activo")
                            recibo.valor_indemnizacion = datos_pdf.get("valor_indemnizacion")
                            recibo.perdida_bruta = datos_pdf.get("perdida_bruta")
                            recibo.deducible = datos_pdf.get("deducible")
                            recibo.depreciacion = datos_pdf.get("depreciacion")
                        break

            return recibo

        except Exception as e:
            logger.error(f"Error procesando email {email_id}: {e}")
            return None

    def _parsear_pdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extrae datos del PDF del recibo de indemnización.
        Busca: número de reclamo, serie, código activo, valor.
        """
        try:
            import io

            import pdfplumber

            datos = {}

            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""

            if not text:
                logger.warning("No se pudo extraer texto del PDF")
                return datos

            logger.debug(f"Texto extraído del PDF:\n{text[:500]}...")

            # Patrones de búsqueda
            # Número de reclamo (ej: 651147, RECLAMO: 651147, No. Reclamo: 651147)
            patron_reclamo = r"(?:RECLAMO|No\.?\s*Reclamo|CLAIM|Siniestro\s*(?:No\.?|#)?)[:\s]*(\d{5,})"
            match = re.search(patron_reclamo, text, re.IGNORECASE)
            if match:
                datos["numero_reclamo"] = match.group(1)
            else:
                # Buscar número de 6 dígitos suelto cerca de palabras clave
                patron_alt = r"(\d{6,})"
                matches = re.findall(patron_alt, text)
                if matches:
                    datos["numero_reclamo"] = matches[0]

            # Serie (ej: SE: MP1NVD1C, Serie: MP1NVD1C)
            patron_serie = r"(?:SE|SERIE|S/N)[:\s]*([A-Z0-9]{6,})"
            match = re.search(patron_serie, text, re.IGNORECASE)
            if match:
                datos["numero_serie"] = match.group(1)

            # Código de activo (ej: AC: 02002001648, Activo: 02002001648)
            patron_activo = r"(?:AC|ACTIVO|COD\.?\s*ACTIVO)[:\s]*(\d{8,})"
            match = re.search(patron_activo, text, re.IGNORECASE)
            if match:
                datos["codigo_activo"] = match.group(1)

            # Valor de indemnización - Buscar valores monetarios por línea
            # El PDF tiene formato: "Texto descriptivo    1,350.00"
            # NOTA: pdfplumber a veces extrae números con espacios (ej: "5 98.84" en vez de "598.84")

            # Procesar línea por línea para extraer valores
            for line in text.split("\n"):
                line_upper = line.upper().strip()

                # Buscar valor monetario al final de la línea
                # Incluye espacios opcionales entre dígitos (formato: "5 98.84" o "1,350.00")
                match_valor = re.search(r"([\d\s,]+\.\d{2})\s*$", line)
                if not match_valor:
                    continue

                # Quitar comas Y espacios del número
                valor_str = match_valor.group(1).replace(",", "").replace(" ", "")
                try:
                    valor = float(valor_str)
                except (ValueError, TypeError):
                    continue

                # LA SUMA DE - monto final a indemnizar (prioridad máxima)
                if "LA SUMA DE" in line_upper or "RECIBI DE" in line_upper:
                    datos["valor_indemnizacion"] = valor

                # Pérdida Bruta
                elif "PERDIDA BRUTA" in line_upper or "PÉRDIDA BRUTA" in line_upper:
                    datos["perdida_bruta"] = valor

                # Deducible
                elif "DEDUCIBLE" in line_upper:
                    datos["deducible"] = valor

                # Depreciación (puede estar escrito Depeciación)
                elif "DEPRECIACI" in line_upper or "DEPECIAC" in line_upper:
                    datos["depreciacion"] = valor

                # Valor Pérdida Neta (antes de depreciación)
                elif "PERDIDA NETA" in line_upper or "PÉRDIDA NETA" in line_upper:
                    datos["perdida_neta"] = valor

            logger.info(f"Datos extraídos del PDF: {datos}")
            return datos

        except ImportError:
            logger.error("pdfplumber no está instalado. Instalar con: pip install pdfplumber")
            return {}
        except Exception as e:
            logger.error(f"Error parseando PDF: {e}")
            return {}

    def vincular_con_siniestro(self, recibo: ReciboIndemnizacion) -> Optional["Siniestro"]:
        """
        Vincula el recibo con el siniestro correspondiente.
        Busca por número de reclamo, serie o código de activo.
        """
        from app.models import BienAsegurado, Siniestro

        siniestro = None

        # 1. Buscar por número de reclamo (numero_siniestro)
        if recibo.numero_reclamo:
            siniestro = Siniestro.objects.filter(numero_siniestro=recibo.numero_reclamo).first()

            if siniestro:
                logger.info(f"Siniestro encontrado por número de reclamo: {recibo.numero_reclamo}")
                return siniestro

        # 2. Buscar por serie del bien
        if recibo.numero_serie:
            bien = BienAsegurado.objects.filter(serie=recibo.numero_serie).first()
            if bien:
                siniestro = Siniestro.objects.filter(bien_asegurado=bien, estado="enviado_aseguradora").first()

                if siniestro:
                    logger.info(f"Siniestro encontrado por serie: {recibo.numero_serie}")
                    return siniestro

        # 3. Buscar por código de activo
        if recibo.codigo_activo:
            bien = BienAsegurado.objects.filter(codigo_bien=recibo.codigo_activo).first()
            if bien:
                siniestro = Siniestro.objects.filter(bien_asegurado=bien, estado="enviado_aseguradora").first()

                if siniestro:
                    logger.info(f"Siniestro encontrado por código activo: {recibo.codigo_activo}")
                    return siniestro

        logger.warning(
            f"No se encontró siniestro para el recibo: reclamo={recibo.numero_reclamo}, serie={recibo.numero_serie}, activo={recibo.codigo_activo}"
        )
        return None

    def marcar_como_leido(self, email_id: bytes):
        """Marca un email como leído."""
        if self._connection:
            try:
                self._connection.store(email_id, "+FLAGS", "\\Seen")
            except Exception as e:
                logger.error(f"Error marcando email como leído: {e}")


def procesar_recibos_indemnizacion() -> Dict[str, Any]:
    """
    Función principal para procesar recibos de indemnización.
    Busca emails, parsea PDFs y actualiza siniestros.
    """
    from app.models import Siniestro

    resultado = {"procesados": 0, "vinculados": 0, "errores": 0, "detalles": []}

    service = RecibosIndemnizacionService()

    if not service.connect():
        resultado["errores"] = 1
        resultado["detalles"].append("Error de conexión IMAP")
        return resultado

    try:
        email_ids = service.buscar_emails_recibos()
        logger.info(f"Encontrados {len(email_ids)} emails de recibos")

        for email_id in email_ids:
            resultado["procesados"] += 1

            recibo = service.procesar_email(email_id)
            if not recibo:
                resultado["detalles"].append(f"No se pudo procesar email {email_id}")
                continue

            # Vincular con siniestro
            siniestro = service.vincular_con_siniestro(recibo)

            if siniestro:
                # Actualizar estado del siniestro usando el método del modelo
                try:
                    from django.core.files.base import ContentFile

                    # Preparar el archivo PDF
                    archivo = None
                    if recibo.pdf_content:
                        filename = recibo.pdf_filename or f"recibo_{siniestro.numero_siniestro}.pdf"
                        archivo = ContentFile(recibo.pdf_content, name=filename)

                    # Usar el método del modelo que guarda todo correctamente
                    siniestro.registrar_recibo_indemnizacion(
                        archivo=archivo,
                        email_origen=recibo.from_address,
                        monto_indemnizado=recibo.valor_indemnizacion,
                        perdida_bruta=recibo.perdida_bruta,
                        deducible=recibo.deducible,
                        depreciacion=recibo.depreciacion,
                    )

                    resultado["vinculados"] += 1
                    resultado["detalles"].append(
                        f"Siniestro {siniestro.numero_siniestro} actualizado a recibo_recibido"
                    )

                    # Marcar email como leído
                    service.marcar_como_leido(email_id)

                except Exception as e:
                    logger.error(f"Error actualizando siniestro: {e}")
                    resultado["errores"] += 1
            else:
                resultado["detalles"].append(f"Recibo no vinculado: reclamo={recibo.numero_reclamo}")

    finally:
        service.disconnect()

    return resultado
