"""
Servicio de Dominio para Gestión de Pólizas.

Este módulo implementa la capa de servicio para la entidad Póliza, encapsulando
toda la lógica de negocio relacionada con el ciclo de vida de pólizas de seguros.
Sigue el patrón de Servicio de Dominio para desacoplar la lógica del framework.

Responsabilidades del Servicio:
    1. **Validación de Fechas**: Verifica coherencia temporal y evita superposiciones
       de pólizas con el mismo número en períodos que se cruzan.

    2. **Validación de Relaciones**: Asegura que el corredor pertenezca a la
       compañía aseguradora seleccionada.

    3. **Gestión de Estados**: Determina automáticamente el estado de la póliza
       (vigente, por_vencer, vencida, cancelada) basándose en fechas.

    4. **Operaciones CRUD**: Proporciona métodos transaccionales para crear
       y actualizar pólizas con validaciones integradas.

Patrones de Diseño:
    - Service Layer: Encapsula lógica de negocio fuera del modelo
    - Result Pattern: Retorna ResultadoOperacion en lugar de excepciones
    - Factory Methods: Construcción de resultados (exito/fallo)
    - Transaction Script: Operaciones atómicas con @transaction.atomic

Ejemplo de Uso:
    Crear una póliza::

        from app.services.poliza import PolizaService
        from datetime import date, timedelta

        resultado = PolizaService.crear_poliza(
            numero_poliza="POL-2026-001",
            compania_aseguradora=compania,
            grupo_ramo=grupo,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            corredor=corredor,
            suma_asegurada=Decimal("1000000.00")
        )

        if resultado.exitoso:
            poliza = resultado.objeto
            print(f"Póliza creada: {poliza.numero_poliza}")
        else:
            for campo, error in resultado.errores.items():
                print(f"Error en {campo}: {error}")

Autor: Equipo de Desarrollo UTPL
Versión: 1.0.0
Última Actualización: Enero 2026
"""
from datetime import date
from typing import Any, Optional

from django.db import transaction
from django.db.models import Q

from ..base import BaseService, ResultadoOperacion, ResultadoValidacion


class PolizaService(BaseService):
    """

    Servicio para gestión de Pólizas.

    Responsabilidades:

    - Validar fechas y evitar superposiciones

    - Validar relación corredor-compañía

    - Gestionar estados de póliza

    - Crear y actualizar pólizas

    USO:

        from app.services.poliza import PolizaService

        resultado = PolizaService.crear_poliza(

            numero_poliza="POL-001",

            compania_aseguradora=compania,

            grupo_ramo=grupo,

            fecha_inicio=date.today(),

            fecha_fin=date.today() + timedelta(days=365)

        )

    """

    # =========================================================================

    # VALIDACIONES

    # =========================================================================

    @classmethod
    def validar_fechas(
        cls, fecha_inicio: date, fecha_fin: date, numero_poliza: str, poliza_pk: Optional[int] = None
    ) -> ResultadoValidacion:
        """Valida fechas y evita duplicidad de pólizas con fechas superpuestas."""

        from app.models import Poliza

        errores = {}

        if fecha_inicio >= fecha_fin:

            errores["fecha_fin"] = "La fecha de fin debe ser posterior a la fecha de inicio."

        query = Q(numero_poliza=numero_poliza) & (Q(fecha_inicio__lte=fecha_fin) & Q(fecha_fin__gte=fecha_inicio))

        if poliza_pk:

            query &= ~Q(pk=poliza_pk)

        polizas_superpuestas = Poliza.objects.filter(query)

        if polizas_superpuestas.exists():

            primera = polizas_superpuestas.first()

            errores["fecha_inicio"] = (
                f'Ya existe una póliza con el número "{numero_poliza}" '
                f"que se superpone con las fechas indicadas "
                f"({primera.fecha_inicio} - {primera.fecha_fin})."
            )

        if errores:

            return ResultadoValidacion(es_valido=False, errores=errores)

        return ResultadoValidacion(es_valido=True)

    @classmethod
    def validar_corredor_compania(cls, compania_aseguradora, corredor) -> ResultadoValidacion:
        """Valida que el corredor pertenezca a la compañía aseguradora."""

        if corredor and compania_aseguradora:

            if corredor.compania_aseguradora_id != compania_aseguradora.pk:

                return ResultadoValidacion(
                    es_valido=False,
                    errores={
                        "corredor": (
                            f'El corredor "{corredor.nombre}" no está asociado '
                            f'a la compañía "{compania_aseguradora.nombre}".'
                        )
                    },
                )

        return ResultadoValidacion(es_valido=True)

    # =========================================================================

    # ESTADO

    # =========================================================================

    @classmethod
    def determinar_estado(cls, fecha_inicio: date, fecha_fin: date, estado_actual: str = None) -> str:
        """Delega a PolizaCalculationService."""

        from ..calculations import PolizaCalculationService

        dias_alerta = cls._get_config("DIAS_ALERTA_VENCIMIENTO_POLIZA", 30)

        return PolizaCalculationService.determinar_estado_poliza(
            fecha_inicio, fecha_fin, dias_alerta=dias_alerta, estado_actual=estado_actual
        )

    @classmethod
    def actualizar_estado(cls, poliza) -> None:
        """Actualiza el estado de la póliza basándose en fechas."""

        if poliza.fecha_inicio and poliza.fecha_fin:

            poliza.estado = cls.determinar_estado(poliza.fecha_inicio, poliza.fecha_fin, poliza.estado)

    # =========================================================================

    # OPERACIONES CRUD

    # =========================================================================

    @classmethod
    @transaction.atomic
    def crear_poliza(
        cls,
        numero_poliza: str,
        compania_aseguradora,
        grupo_ramo,
        fecha_inicio: date,
        fecha_fin: date,
        corredor=None,
        **kwargs,
    ) -> ResultadoOperacion:
        """Crea una nueva póliza con validaciones de negocio."""

        from app.models import Poliza

        val_fechas = cls.validar_fechas(fecha_inicio, fecha_fin, numero_poliza)

        if not val_fechas.es_valido:

            return ResultadoOperacion.desde_validacion(val_fechas, "Error de validación en fechas")

        val_corredor = cls.validar_corredor_compania(compania_aseguradora, corredor)

        if not val_corredor.es_valido:

            return ResultadoOperacion.desde_validacion(val_corredor, "Error de validación en corredor")

        try:

            poliza = Poliza(
                numero_poliza=numero_poliza,
                compania_aseguradora=compania_aseguradora,
                grupo_ramo=grupo_ramo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                corredor=corredor,
                **kwargs,
            )

            cls.actualizar_estado(poliza)

            poliza.save()

            return ResultadoOperacion.exito(poliza, "Póliza creada exitosamente")

        except Exception as e:

            return ResultadoOperacion.fallo({"__all__": str(e)}, f"Error al crear póliza: {str(e)}")

    @classmethod
    @transaction.atomic
    def actualizar_poliza(cls, poliza, **campos) -> ResultadoOperacion:
        """Actualiza una póliza existente con validaciones."""

        try:

            for campo, valor in campos.items():

                if hasattr(poliza, campo):

                    setattr(poliza, campo, valor)

            val_fechas = cls.validar_fechas(poliza.fecha_inicio, poliza.fecha_fin, poliza.numero_poliza, poliza.pk)

            if not val_fechas.es_valido:

                return ResultadoOperacion.desde_validacion(val_fechas, "Error de validación en fechas")

            val_corredor = cls.validar_corredor_compania(poliza.compania_aseguradora, poliza.corredor)

            if not val_corredor.es_valido:

                return ResultadoOperacion.desde_validacion(val_corredor, "Error de validación en corredor")

            cls.actualizar_estado(poliza)

            poliza.save()

            return ResultadoOperacion.exito(poliza, "Póliza actualizada exitosamente")

        except Exception as e:

            return ResultadoOperacion.fallo({"__all__": str(e)}, f"Error al actualizar póliza: {str(e)}")
