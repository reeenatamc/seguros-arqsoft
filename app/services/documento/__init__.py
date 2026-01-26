"""

Servicios del dominio Documento.

Validación de documentos y generación de archivos Word/PDF.

"""


from .service import DocumentoService

from .generacion import DocumentosService


__all__ = [

    'DocumentoService',      # Validación de relaciones

    'DocumentosService',     # Generación de Word/PDF

]
