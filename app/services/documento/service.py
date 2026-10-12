"""

Servicio de Documentos.

Responsabilidad única: Gestión de documentos asociados a entidades.

"""

from ..base import BaseService, ResultadoValidacion


class DocumentoService(BaseService):
    """

    Servicio para gestión de Documentos.

    Responsabilidades:

    - Validar coherencia de relaciones documento-entidad

    - Validar tipos de documento

    USO:

        from app.services.documento import DocumentoService

        validacion = DocumentoService.validar_relaciones(

            tipo_documento='poliza',

            poliza_id=1,

            siniestro_id=None,

            factura_id=None

        )

    """

    @classmethod
    def validar_relaciones(
        cls, tipo_documento: str, poliza_id: int | None, siniestro_id: int | None, factura_id: int | None
    ) -> ResultadoValidacion:
        """Valida que el documento tenga al menos una relación y sea coherente."""

        errores = {}

        # Debe tener al menos una relación

        if not any([poliza_id, siniestro_id, factura_id]):

            errores["__all__"] = "El documento debe estar asociado al menos a una póliza, siniestro o factura."

        # Coherencia tipo-relación

        if tipo_documento == "poliza" and not poliza_id:

            errores["tipo_documento"] = 'Un documento de tipo "Póliza" debe estar asociado a una póliza.'

        if tipo_documento == "factura" and not factura_id:

            errores["tipo_documento"] = 'Un documento de tipo "Factura" debe estar asociado a una factura.'

        if errores:

            return ResultadoValidacion(es_valido=False, errores=errores)

        return ResultadoValidacion(es_valido=True)
