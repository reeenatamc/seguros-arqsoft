"""
Servicio para lectura de respuestas del broker vía IMAP.

Política de respuesta del broker:
- Asunto: RESPUESTA SINIESTRO SIN-XXXX-XXXX

Flujo:
1. El broker recibe notificación de siniestro
2. Revisa y responde con el asunto estructurado
3. El sistema parsea el email y cambia estado a 'documentacion_lista'
"""

import imaplib
import email
import re
import logging
from email.header import decode_header
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger('app')


@dataclass
class RespuestaBroker:
    """Datos extraídos de una respuesta del broker."""
    email_id: str
    subject: str
    from_address: str
    date: Optional[datetime]
    numero_siniestro: str


class BrokerReaderService:
    """
    Servicio para leer respuestas del broker desde el inbox IMAP.
    
    Busca emails con asunto "RESPUESTA SINIESTRO SIN-XXXX-XXXX"
    """
    
    ASUNTO_RESPUESTA = "RESPUESTA SINIESTRO"
    # Acepta formatos: SIN-2026-0001, SIN-EMAIL-2026-00001, o 6 dígitos (651147)
    PATRON_SINIESTRO = r'(?:SIN-(?:EMAIL-)?\d{4}-\d{4,5}|\d{6})'
    
    def __init__(self):
        """Inicializa el servicio con configuración de settings."""
        self.host = getattr(settings, 'IMAP_HOST', 'imap.gmail.com')
        self.port = getattr(settings, 'IMAP_PORT', 993)
        self.user = getattr(settings, 'IMAP_EMAIL', '')
        self.password = getattr(settings, 'IMAP_PASSWORD', '')
        self._connection: Optional[imaplib.IMAP4_SSL] = None
    
    def esta_configurado(self) -> bool:
        """Verifica si el servicio está correctamente configurado."""
        return bool(self.host and self.user and self.password)
    
    def connect(self) -> bool:
        """Establece conexión con el servidor IMAP."""
        if not self.esta_configurado():
            logger.error("IMAP no configurado. Revisar IMAP_EMAIL y IMAP_PASSWORD en settings.")
            return False
        
        try:
            logger.info(f"Conectando a {self.host}:{self.port}...")
            self._connection = imaplib.IMAP4_SSL(self.host, self.port)
            self._connection.login(self.user, self.password)
            logger.info(f"Conexión IMAP exitosa: {self.user}")
            return True
        except Exception as e:
            logger.error(f"Error conectando a IMAP: {e}")
            return False
    
    def disconnect(self):
        """Cierra la conexión IMAP."""
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except:
                pass
            finally:
                self._connection = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, *args):
        self.disconnect()
    
    def _decode_header(self, header_value: str) -> str:
        """Decodifica un header de email."""
        if not header_value:
            return ''
        decoded = decode_header(header_value)
        result = []
        for part, charset in decoded:
            if isinstance(part, bytes):
                result.append(part.decode(charset or 'utf-8', errors='replace'))
            else:
                result.append(part)
        return ''.join(result)
    
    def _extraer_numero_siniestro(self, subject: str) -> Optional[str]:
        """Extrae el número de siniestro del asunto."""
        match = re.search(self.PATRON_SINIESTRO, subject.upper())
        if match:
            return match.group()
        return None
    
    def buscar_emails_respuestas(self) -> List[bytes]:
        """Busca emails no leídos con asunto de respuesta del broker."""
        if not self._connection:
            return []
        
        try:
            self._connection.select('INBOX')
            # Buscar directamente por asunto para evitar revisar miles de emails
            search_criteria = f'(UNSEEN SUBJECT "{self.ASUNTO_RESPUESTA}")'
            status, messages = self._connection.search(None, search_criteria)
            if status != 'OK':
                return []
            return messages[0].split() if messages[0] else []
        except Exception as e:
            logger.error(f"Error buscando emails: {e}")
            return []
    
    def procesar_email(self, email_id: bytes) -> Optional[RespuestaBroker]:
        """Procesa un email y extrae los datos de la respuesta."""
        if not self._connection:
            return None
        
        try:
            status, msg_data = self._connection.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return None
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            subject = self._decode_header(msg.get('Subject', ''))
            
            # Verificar que sea una respuesta del broker
            if self.ASUNTO_RESPUESTA.upper() not in subject.upper():
                return None
            
            # Extraer número de siniestro
            numero_siniestro = self._extraer_numero_siniestro(subject)
            if not numero_siniestro:
                logger.warning(f"No se encontró número de siniestro en: {subject}")
                return None
            
            logger.info(f"Respuesta del broker encontrada: {subject}")
            
            # Obtener fecha
            date_str = msg.get('Date', '')
            date = None
            if date_str:
                try:
                    date = email.utils.parsedate_to_datetime(date_str)
                except:
                    pass
            
            return RespuestaBroker(
                email_id=email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                subject=subject,
                from_address=msg.get('From', ''),
                date=date,
                numero_siniestro=numero_siniestro
            )
            
        except Exception as e:
            logger.error(f"Error procesando email {email_id}: {e}")
            return None
    
    def vincular_a_siniestro(self, respuesta: RespuestaBroker) -> Tuple[bool, str, Optional[Any]]:
        """
        Vincula la respuesta del broker al siniestro correspondiente.
        Cambia el estado de 'notificado_broker' a 'documentacion_lista'.
        """
        from app.models import Siniestro
        
        try:
            siniestro = Siniestro.objects.filter(
                numero_siniestro=respuesta.numero_siniestro
            ).first()
            
            if not siniestro:
                return False, f"Siniestro {respuesta.numero_siniestro} no encontrado", None
            
            if siniestro.estado != 'notificado_broker':
                return False, f"Siniestro en estado '{siniestro.estado}', no en 'notificado_broker'", siniestro
            
            # Registrar respuesta del broker
            siniestro.registrar_respuesta_broker(email_origen=respuesta.from_address)
            
            logger.info(f"Respuesta del broker registrada para {respuesta.numero_siniestro}")
            return True, "Respuesta del broker registrada", siniestro
            
        except Exception as e:
            logger.error(f"Error vinculando respuesta: {e}")
            return False, str(e), None
    
    def marcar_como_leido(self, email_id: str):
        """Marca un email como leído."""
        if self._connection:
            try:
                eid = email_id.encode() if isinstance(email_id, str) else email_id
                self._connection.store(eid, '+FLAGS', '\\Seen')
            except Exception as e:
                logger.warning(f"Error marcando email como leído: {e}")
    
    def procesar_respuestas(self, marcar_leidos: bool = True) -> Dict[str, Any]:
        """
        Procesa todas las respuestas del broker pendientes.
        """
        resultados = {
            'total_emails': 0,
            'respuestas_encontradas': 0,
            'vinculadas': 0,
            'errores': 0,
            'detalles': []
        }
        
        if not self._connection and not self.connect():
            resultados['errores'] = 1
            resultados['detalles'].append({'error': 'No se pudo conectar al servidor IMAP'})
            return resultados
        
        email_ids = self.buscar_emails_respuestas()
        resultados['total_emails'] = len(email_ids)
        logger.info(f"Encontrados {len(email_ids)} emails no leídos")
        
        for email_id in email_ids:
            respuesta = self.procesar_email(email_id)
            
            if not respuesta:
                continue
            
            resultados['respuestas_encontradas'] += 1
            
            exito, mensaje, siniestro = self.vincular_a_siniestro(respuesta)
            
            detalle = {
                'email_id': respuesta.email_id,
                'subject': respuesta.subject,
                'numero_siniestro': respuesta.numero_siniestro,
                'exito': exito,
                'mensaje': mensaje
            }
            
            if exito:
                resultados['vinculadas'] += 1
                if marcar_leidos:
                    self.marcar_como_leido(respuesta.email_id)
            else:
                resultados['errores'] += 1
            
            resultados['detalles'].append(detalle)
        
        return resultados


def procesar_respuestas_broker() -> Dict[str, Any]:
    """
    Función de conveniencia para procesar respuestas del broker.
    Usada por el task de Celery.
    """
    try:
        with BrokerReaderService() as service:
            return service.procesar_respuestas()
    except Exception as e:
        logger.error(f"Error procesando respuestas del broker: {e}")
        return {'error': str(e)}
