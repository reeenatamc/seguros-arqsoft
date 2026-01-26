"""
Módulo Base de Servicios de Dominio para el Sistema de Gestión de Seguros.

Este módulo define las clases base y tipos de datos compartidos que fundamentan
la capa de servicios del sistema. Implementa el patrón Result para manejo
explícito de éxitos y errores, evitando el uso de excepciones para control de flujo.

Patrones de Diseño Implementados:
    - Result Pattern: Encapsula el resultado de operaciones (éxito/fallo) con
      información estructurada, evitando excepciones para flujo de control.
    - Value Object: Las dataclasses inmutables representan resultados sin identidad.
    - Factory Method: Métodos de clase para construcción semántica de resultados.
    - Fluent Interface: Métodos que retornan self para encadenamiento.

Arquitectura:
    La capa de servicios actúa como intermediario entre las vistas (controllers)
    y los modelos (repositories), encapsulando la lógica de negocio y validaciones
    complejas que no pertenecen ni a la capa de presentación ni a la de datos.

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Views     │────▶│  Services   │────▶│   Models    │
    │ (Controller)│     │   (Logic)   │     │(Repository) │
    └─────────────┘     └─────────────┘     └─────────────┘

Autor: Equipo de Desarrollo UTPL
Versión: 1.0.0
Última Actualización: Enero 2026

Example:
    Uso del Result Pattern en un servicio::

        class PolizaService(BaseService):
            def crear_poliza(self, datos: dict) -> ResultadoOperacion:
                # Validar datos
                validacion = self._validar_datos_poliza(datos)
                if not validacion.es_valido:
                    return ResultadoOperacion.desde_validacion(validacion)

                # Crear póliza
                poliza = Poliza.objects.create(**datos)
                return ResultadoOperacion.exito(poliza, "Póliza creada exitosamente")
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


# =============================================================================
# TIPOS DE RESULTADO - RESULT PATTERN
# =============================================================================

@dataclass
class ResultadoValidacion:
    """
    Encapsula el resultado de una validación de reglas de negocio.

    Esta clase implementa el patrón Result para validaciones, proporcionando
    una estructura clara para comunicar si una validación fue exitosa y,
    en caso contrario, qué campos tienen errores.

    El diseño permite:
        1. Acumulación de múltiples errores en una sola validación
        2. Fusión de resultados de validaciones independientes
        3. Encadenamiento fluido de métodos para agregar errores

    Attributes:
        es_valido (bool): Indica si la validación fue exitosa.
        errores (Dict[str, str]): Diccionario de errores por campo.
            Las claves son nombres de campos, los valores son mensajes de error.

    Example:
        Validación con múltiples campos::

            def validar_poliza(datos: dict) -> ResultadoValidacion:
                resultado = ResultadoValidacion(es_valido=True)

                if not datos.get('numero_poliza'):
                    resultado.agregar_error('numero_poliza', 'Campo requerido')

                if datos.get('suma_asegurada', 0) <= 0:
                    resultado.agregar_error('suma_asegurada', 'Debe ser mayor a cero')

                return resultado
    """

    es_valido: bool
    errores: Dict[str, str] = None

    def __post_init__(self):
        """Inicializa el diccionario de errores si no fue proporcionado."""
        if self.errores is None:
            self.errores = {}

    def agregar_error(self, campo: str, mensaje: str) -> 'ResultadoValidacion':
        """
        Agrega un error de validación y marca el resultado como inválido.

        Implementa Fluent Interface para permitir encadenamiento de llamadas.

        Args:
            campo: Nombre del campo que tiene el error.
            mensaje: Descripción del error de validación.

        Returns:
            Self para permitir encadenamiento de métodos.

        Example:
            >>> resultado = ResultadoValidacion(es_valido=True)
            >>> resultado.agregar_error('email', 'Formato inválido').agregar_error('nombre', 'Requerido')
        """
        self.errores[campo] = mensaje
        self.es_valido = False
        return self

    def fusionar(self, otro: 'ResultadoValidacion') -> 'ResultadoValidacion':
        """
        Fusiona otro resultado de validación con este.

        Útil para combinar validaciones de diferentes aspectos de un objeto.
        Si el otro resultado es inválido, este también se marca como inválido
        y se agregan todos sus errores.

        Args:
            otro: Otro ResultadoValidacion a fusionar.

        Returns:
            Self con los errores fusionados.

        Example:
            >>> validacion_basica = validar_campos_requeridos(datos)
            >>> validacion_negocio = validar_reglas_negocio(datos)
            >>> resultado_final = validacion_basica.fusionar(validacion_negocio)
        """
        if not otro.es_valido:
            self.es_valido = False
            self.errores.update(otro.errores)
        return self


@dataclass
class ResultadoOperacion:
    """
    Encapsula el resultado de una operación de servicio de dominio.

    Implementa el patrón Result para operaciones completas, proporcionando
    una alternativa estructurada al manejo de excepciones. Cada operación
    retorna un ResultadoOperacion que indica explícitamente si tuvo éxito.

    Este enfoque:
        1. Hace explícito el manejo de errores (no se pueden ignorar)
        2. Proporciona mensajes contextuales para el usuario
        3. Permite transportar el objeto resultante en caso de éxito
        4. Estructura los errores por campo para formularios

    Attributes:
        exitoso (bool): Indica si la operación se completó correctamente.
        objeto (Any): El objeto resultante en caso de éxito (ej: Poliza creada).
        errores (Dict[str, str]): Errores por campo en caso de fallo.
        mensaje (str): Mensaje descriptivo para mostrar al usuario.

    Example:
        Manejo en una vista Django::

            def crear_poliza_view(request):
                resultado = PolizaService.crear_poliza(request.POST)

                if resultado.exitoso:
                    messages.success(request, resultado.mensaje)
                    return redirect('poliza_detalle', pk=resultado.objeto.pk)
                else:
                    # Mostrar errores en el formulario
                    form = PolizaForm(request.POST)
                    for campo, error in resultado.errores.items():
                        form.add_error(campo, error)
                    return render(request, 'poliza_form.html', {'form': form})
    """

    exitoso: bool
    objeto: Any = None
    errores: Dict[str, str] = None
    mensaje: str = ""

    def __post_init__(self):
        """Inicializa el diccionario de errores si no fue proporcionado."""
        if self.errores is None:
            self.errores = {}

    @classmethod
    def exito(cls, objeto: Any, mensaje: str = "") -> 'ResultadoOperacion':
        """
        Factory method para crear un resultado exitoso.

        Args:
            objeto: El objeto resultante de la operación.
            mensaje: Mensaje descriptivo opcional para el usuario.

        Returns:
            ResultadoOperacion marcado como exitoso con el objeto adjunto.

        Example:
            >>> poliza = Poliza.objects.create(**datos)
            >>> return ResultadoOperacion.exito(poliza, "Póliza creada correctamente")
        """
        return cls(exitoso=True, objeto=objeto, mensaje=mensaje)

    @classmethod
    def fallo(cls, errores: Dict[str, str], mensaje: str = "") -> 'ResultadoOperacion':
        """
        Factory method para crear un resultado fallido.

        Args:
            errores: Diccionario de errores por campo.
            mensaje: Mensaje descriptivo opcional para el usuario.

        Returns:
            ResultadoOperacion marcado como fallido con los errores.

        Example:
            >>> return ResultadoOperacion.fallo(
            ...     {'numero_poliza': 'Ya existe una póliza con este número'},
            ...     "Error al crear la póliza"
            ... )
        """
        return cls(exitoso=False, errores=errores, mensaje=mensaje)

    @classmethod
    def desde_validacion(cls, validacion: ResultadoValidacion, mensaje: str = "") -> 'ResultadoOperacion':
        """
        Factory method para crear un resultado desde una validación fallida.

        Convierte un ResultadoValidacion inválido en un ResultadoOperacion
        fallido, preservando los errores por campo.

        Args:
            validacion: ResultadoValidacion con es_valido=False.
            mensaje: Mensaje descriptivo opcional (por defecto: "Error de validación").

        Returns:
            ResultadoOperacion fallido con los errores de la validación.

        Example:
            >>> validacion = validar_datos_poliza(datos)
            >>> if not validacion.es_valido:
            ...     return ResultadoOperacion.desde_validacion(validacion)
        """
        return cls(
            exitoso=False,
            errores=validacion.errores,
            mensaje=mensaje or "Error de validación"
        )


# =============================================================================
# CLASE BASE PARA SERVICIOS
# =============================================================================

class BaseService:
    """
    Clase base abstracta para todos los servicios de dominio.

    Proporciona funcionalidad común compartida por todos los servicios,
    como acceso a la configuración del sistema. Los servicios heredan
    de esta clase para obtener comportamiento base consistente.

    Esta clase sigue el principio de Open/Closed: está abierta para
    extensión (heredando) pero cerrada para modificación.

    Métodos Estáticos:
        _get_config: Acceso a parámetros de configuración del sistema.

    Example:
        Creación de un servicio de dominio::

            class FacturaService(BaseService):
                @staticmethod
                def calcular_iva(subtotal: Decimal) -> Decimal:
                    tasa_iva = BaseService._get_config('IVA_PORCENTAJE', 12)
                    return subtotal * Decimal(tasa_iva) / 100
    """

    @staticmethod
    def _get_config(clave: str, default: Any) -> Any:
        """
        Obtiene un valor de configuración del sistema.

        Accede al modelo ConfiguracionSistema para obtener parámetros
        configurables sin hardcodear valores en el código.

        Args:
            clave: Nombre de la configuración (ej: 'IVA_PORCENTAJE', 'DIAS_ALERTA_VENCIMIENTO').
            default: Valor por defecto si la configuración no existe.

        Returns:
            El valor de la configuración o el default si no existe.

        Example:
            >>> dias_alerta = BaseService._get_config('DIAS_ALERTA_POLIZA', 30)
        """
        from app.models import ConfiguracionSistema
        return ConfiguracionSistema.get_config(clave, default)
