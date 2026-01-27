"""
Servicios de Email.
Lectura de correos IMAP para:
- Reportes de siniestros (del custodio)
- Respuestas del broker
- Recibos de indemnización (de la aseguradora)
"""

from .broker_reader import BrokerReaderService, procesar_respuestas_broker
from .reader import EmailReaderService
from .recibos_reader import RecibosIndemnizacionService, procesar_recibos_indemnizacion

__all__ = [
    "EmailReaderService",
    "BrokerReaderService",
    "procesar_respuestas_broker",
    "RecibosIndemnizacionService",
    "procesar_recibos_indemnizacion",
]
