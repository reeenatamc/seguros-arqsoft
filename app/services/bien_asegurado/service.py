"""

Servicio de Bienes Asegurados.

Responsabilidad única: Gestión de bienes asegurados y su relación con pólizas.

"""

from ..base import BaseService, ResultadoValidacion, ResultadoOperacion

class BienAseguradoService(BaseService):

    """

    Servicio para gestión de Bienes Asegurados.

    Responsabilidades:

    - Validar coherencia entre subgrupo y grupo de póliza

    USO:

        from app.services.bien_asegurado import BienAseguradoService

        validacion = BienAseguradoService.validar_subgrupo_poliza(

            poliza=poliza,

            subgrupo_ramo=subgrupo

        )

    """

    @classmethod
    def validar_subgrupo_poliza(cls, poliza, subgrupo_ramo) -> ResultadoValidacion:

        """Valida que el subgrupo pertenezca al grupo de la póliza."""

        if poliza and subgrupo_ramo:

            if hasattr(poliza, 'grupo_ramo') and poliza.grupo_ramo:

                if subgrupo_ramo.grupo_ramo_id != poliza.grupo_ramo_id:

                    return ResultadoValidacion(

                        es_valido=False,

                        errores={

                            'subgrupo_ramo': (

                                f'El subgrupo "{subgrupo_ramo.nombre}" no pertenece '

                                f'al grupo "{poliza.grupo_ramo.nombre}" de la póliza.'

                            )

                        }

                    )

        return ResultadoValidacion(es_valido=True)
