"""

Servicio de Siniestros.

Responsabilidad única: Gestión del ciclo de vida de siniestros.

"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ..base import BaseService, ResultadoOperacion, ResultadoValidacion


class SiniestroService(BaseService):
    """

    Servicio para gestión de Siniestros.

    Responsabilidades:

    - Sincronizar campos desde bien asegurado

    - Validar coherencia con póliza

    - Generar números de siniestro

    - Crear y actualizar siniestros

    USO:

        from app.services.siniestro import SiniestroService

        resultado = SiniestroService.crear_siniestro(

            bien_asegurado=bien,

            tipo_siniestro=tipo,

            fecha_siniestro=timezone.now()

        )

    """

    # =========================================================================

    # SINCRONIZACIÓN

    # =========================================================================

    @classmethod
    def sincronizar_desde_bien_asegurado(cls, siniestro) -> None:
        """Sincroniza los campos legacy del siniestro desde el bien asegurado."""

        if siniestro.bien_asegurado_id:

            bien = siniestro.bien_asegurado

            siniestro.bien_nombre = bien.nombre

            siniestro.bien_modelo = bien.modelo or ""

            siniestro.bien_serie = bien.serie or ""

            siniestro.bien_marca = bien.marca or ""

            siniestro.bien_codigo_activo = bien.codigo_activo or ""

            if not siniestro.poliza_id:

                siniestro.poliza = bien.poliza

            if not siniestro.responsable_custodio_id and bien.responsable_custodio_id:

                siniestro.responsable_custodio = bien.responsable_custodio

    # =========================================================================

    # VALIDACIONES

    # =========================================================================

    @classmethod
    def validar_bien_asegurado(cls, siniestro) -> ResultadoValidacion:
        """Valida que el siniestro tenga un bien asegurado o campos legacy."""

        if not siniestro.bien_asegurado_id and not siniestro.bien_nombre:

            return ResultadoValidacion(
                es_valido=False,
                errores={
                    "bien_asegurado": "Debe especificar un bien asegurado o llenar los campos del bien manualmente."
                },
            )

        return ResultadoValidacion(es_valido=True)

    @classmethod
    def validar_fecha_siniestro(cls, siniestro) -> ResultadoValidacion:
        """Valida que la fecha del siniestro no sea futura."""

        if siniestro.fecha_siniestro:

            ahora = timezone.now()

            if siniestro.fecha_siniestro > ahora:

                return ResultadoValidacion(
                    es_valido=False, errores={"fecha_siniestro": "La fecha del siniestro no puede ser futura."}
                )

        return ResultadoValidacion(es_valido=True)

    @classmethod
    def validar_vigencia_poliza(cls, siniestro) -> ResultadoValidacion:
        """Valida que el siniestro esté dentro del período de vigencia de la póliza."""

        poliza = siniestro.get_poliza() if hasattr(siniestro, "get_poliza") else siniestro.poliza

        if poliza and siniestro.fecha_siniestro:

            fecha_sin = siniestro.fecha_siniestro.date()

            if not (poliza.fecha_inicio <= fecha_sin <= poliza.fecha_fin):

                return ResultadoValidacion(
                    es_valido=False,
                    errores={
                        "fecha_siniestro": (
                            f"El siniestro debe ocurrir dentro del período de vigencia "
                            f"de la póliza ({poliza.fecha_inicio} - {poliza.fecha_fin})."
                        )
                    },
                )

        return ResultadoValidacion(es_valido=True)

    @classmethod
    def validar_siniestro(cls, siniestro) -> ResultadoValidacion:
        """Ejecuta todas las validaciones del siniestro."""

        resultado = ResultadoValidacion(es_valido=True)

        for validacion in [
            cls.validar_bien_asegurado,
            cls.validar_fecha_siniestro,
            cls.validar_vigencia_poliza,
        ]:

            resultado.fusionar(validacion(siniestro))

        return resultado

    # =========================================================================

    # GENERACIÓN DE NÚMERO

    # =========================================================================

    @classmethod
    def generar_numero_siniestro(cls, prefijo: str = "SIN") -> str:
        """Genera un número de siniestro único."""

        from app.models import Siniestro

        anio = timezone.now().year

        ultimo = Siniestro.objects.aggregate(Max("id"))["id__max"] or 0

        return f"{prefijo}-{anio}-{str(ultimo + 1).zfill(5)}"

    # =========================================================================

    # OPERACIONES CRUD

    # =========================================================================

    @classmethod
    @transaction.atomic
    def crear_siniestro(
        cls, bien_asegurado=None, tipo_siniestro=None, fecha_siniestro=None, **kwargs
    ) -> ResultadoOperacion:
        """Crea un nuevo siniestro con sincronización y validaciones."""

        from app.models import Siniestro

        try:

            siniestro = Siniestro(
                bien_asegurado=bien_asegurado, tipo_siniestro=tipo_siniestro, fecha_siniestro=fecha_siniestro, **kwargs
            )

            cls.sincronizar_desde_bien_asegurado(siniestro)

            validacion = cls.validar_siniestro(siniestro)

            if not validacion.es_valido:

                return ResultadoOperacion.desde_validacion(validacion)

            siniestro.save()

            return ResultadoOperacion.exito(siniestro, "Siniestro creado exitosamente")

        except Exception as e:

            return ResultadoOperacion.fallo({"__all__": str(e)}, f"Error al crear siniestro: {str(e)}")

    @classmethod
    @transaction.atomic
    def actualizar_siniestro(cls, siniestro, **campos) -> ResultadoOperacion:
        """Actualiza un siniestro existente con sincronización y validaciones."""

        try:

            for campo, valor in campos.items():

                if hasattr(siniestro, campo):

                    setattr(siniestro, campo, valor)

            cls.sincronizar_desde_bien_asegurado(siniestro)

            validacion = cls.validar_siniestro(siniestro)

            if not validacion.es_valido:

                return ResultadoOperacion.desde_validacion(validacion)

            siniestro.save()

            return ResultadoOperacion.exito(siniestro, "Siniestro actualizado exitosamente")

        except Exception as e:

            return ResultadoOperacion.fallo({"__all__": str(e)}, f"Error al actualizar siniestro: {str(e)}")

    # =========================================================================

    # CREACIÓN DESDE EMAIL (Vista delegada)

    # =========================================================================

    @classmethod
    @transaction.atomic
    def crear_desde_email(
        cls,
        siniestro_email,
        poliza,
        tipo_siniestro,
        ubicacion: str,
        monto_estimado: Decimal,
        responsable=None,
        fecha_reporte_str: Optional[str] = None,
        usuario=None,
    ) -> ResultadoOperacion:
        """

        Crea un siniestro a partir de un registro de email.

        """

        from app.models import ResponsableCustodio, Siniestro

        try:

            # Obtener o crear responsable

            if not responsable and siniestro_email.responsable_nombre:

                responsable, _ = ResponsableCustodio.objects.get_or_create(
                    nombre=siniestro_email.responsable_nombre, defaults={"activo": True}
                )

            # Parsear fecha

            fecha_siniestro = timezone.now()

            if fecha_reporte_str:

                try:

                    fecha_siniestro = timezone.make_aware(datetime.strptime(fecha_reporte_str.strip(), "%d/%m/%Y"))

                except ValueError:

                    pass

            elif siniestro_email.fecha_reporte:

                try:

                    fecha_siniestro = timezone.make_aware(
                        datetime.strptime(siniestro_email.fecha_reporte.strip(), "%d/%m/%Y")
                    )

                except ValueError:

                    pass

            # Generar número

            numero_siniestro = cls.generar_numero_siniestro("SIN-EMAIL")

            # Crear siniestro

            siniestro = Siniestro.objects.create(
                poliza=poliza,
                numero_siniestro=numero_siniestro,
                tipo_siniestro=tipo_siniestro,
                fecha_siniestro=fecha_siniestro,
                bien_nombre=f"{siniestro_email.periferico} {siniestro_email.marca}".strip(),
                bien_modelo=siniestro_email.modelo,
                bien_serie=siniestro_email.serie,
                bien_marca=siniestro_email.marca,
                responsable_custodio=responsable,
                ubicacion=ubicacion,
                causa=siniestro_email.causa,
                descripcion_detallada=siniestro_email.problema,
                monto_estimado=monto_estimado,
                estado="registrado",
            )

            # Actualizar registro de email

            siniestro_email.siniestro_creado = siniestro

            siniestro_email.responsable_encontrado = responsable

            siniestro_email.estado_procesamiento = "procesado"

            siniestro_email.fecha_procesamiento = timezone.now()

            siniestro_email.procesado_por = usuario

            siniestro_email.save()

            return ResultadoOperacion.exito(siniestro, "Siniestro creado desde email exitosamente")

        except Exception as e:

            return ResultadoOperacion.fallo({"__all__": str(e)}, f"Error al crear siniestro desde email: {str(e)}")
