"""

Servicios del dominio Documento.

Validación de documentos y generación de archivos Word/PDF.

"""

from .generacion import DocumentosService
from .service import DocumentoService

__all__ = [
    "DocumentoService",  # Validación de relaciones
    "DocumentosService",  # Generación de Word/PDF
]
