"""

Validadores de Configuración Extensibles.

Este módulo implementa un sistema de validación para ConfiguracionSistema

que permite agregar nuevos validadores sin modificar el modelo.

ARQUITECTURA:

- ValidadorConfig: Interfaz base para validadores

- RegistroValidadores: Registry que mantiene los validadores registrados

- Validadores concretos: PorcentajeValidator, RangoNumericoValidator, etc.

USO:

    from app.services.config_validators import (

        registro_validadores, PorcentajeValidator, validar_configuracion

    )

    # Registrar un nuevo validador

    registro_validadores.registrar(

        'MI_NUEVA_CONFIG',

        PorcentajeValidator(min_valor=0.0, max_valor=0.5)

    )

    # Validar una configuración

    errores = validar_configuracion('PORCENTAJE_SUPERINTENDENCIA', '0.035', 'decimal')

EXTENSIBILIDAD:

    Para agregar una nueva validación:

    1. Crear validador (puede ser función o clase):

       def validar_mi_config(valor: str, tipo: str) -> Dict[str, str]:

           if not es_valido(valor):

               return {'valor': 'Mensaje de error'}

           return {}

    2. Registrarlo:

       registro_validadores.registrar('MI_CONFIG', validar_mi_config)

"""

from abc import ABC, abstractmethod

from dataclasses import dataclass

from decimal import Decimal, InvalidOperation

from typing import Any, Callable, Dict, List, Optional, Set, Union

import json

import re

# ==============================================================================

# INTERFAZ BASE - VALIDADOR

# ==============================================================================


class ValidadorConfig(ABC):

    """

    Interfaz base para validadores de configuración.

    Cada validador verifica una configuración específica.

    """

    @abstractmethod
    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        """

        Valida el valor de una configuración.

        Args:

            valor: Valor de la configuración (siempre string)

            tipo: Tipo declarado ('texto', 'decimal', 'entero', 'json')

        Returns:

            Dict vacío si es válido, o Dict con errores {campo: mensaje}

        """

        pass

    @property
    def descripcion(self) -> str:

        """Descripción del validador para documentación."""

        return self.__class__.__name__

# ==============================================================================

# VALIDADORES CONCRETOS

# ==============================================================================


class PorcentajeValidator(ValidadorConfig):

    """

    Valida que un valor sea un porcentaje válido.

    Por defecto, acepta valores entre 0.0 y 1.0 (0% a 100%).

    """

    def __init__(

        self,

        min_valor: float = 0.0,

        max_valor: float = 1.0,

        tipo_requerido: str = 'decimal',

    ):

        self.min_valor = Decimal(str(min_valor))

        self.max_valor = Decimal(str(max_valor))

        self.tipo_requerido = tipo_requerido

    @property
    def descripcion(self) -> str:

        return f"Porcentaje entre {self.min_valor} y {self.max_valor}"

    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        errores = {}

        # Validar tipo

        if tipo != self.tipo_requerido:

            errores['tipo'] = f'Este parámetro debe ser de tipo "{self.tipo_requerido}".'

            return errores

        # Validar valor decimal

        try:

            valor_decimal = Decimal(valor)

        except (InvalidOperation, ValueError, TypeError):

            errores['valor'] = 'El valor debe ser un número decimal válido.'

            return errores

        # Validar rango

        if not (self.min_valor <= valor_decimal <= self.max_valor):

            errores['valor'] = (

                f'El porcentaje debe estar entre {self.min_valor} y {self.max_valor} '

                f'(por ejemplo, 0.035 para 3.5%).'

            )

        return errores


class RangoNumericoValidator(ValidadorConfig):

    """

    Valida que un valor numérico esté dentro de un rango.

    """

    def __init__(

        self,

        min_valor: Optional[float] = None,

        max_valor: Optional[float] = None,

        tipo_requerido: str = 'entero',

        mensaje_error: Optional[str] = None,

    ):

        self.min_valor = min_valor

        self.max_valor = max_valor

        self.tipo_requerido = tipo_requerido

        self.mensaje_error = mensaje_error

    @property
    def descripcion(self) -> str:

        partes = []

        if self.min_valor is not None:

            partes.append(f"mín: {self.min_valor}")

        if self.max_valor is not None:

            partes.append(f"máx: {self.max_valor}")

        return f"Número {self.tipo_requerido} ({', '.join(partes) or 'sin límites'})"

    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        errores = {}

        # Validar tipo

        if tipo != self.tipo_requerido:

            errores['tipo'] = f'Este parámetro debe ser de tipo "{self.tipo_requerido}".'

            return errores

        # Convertir según tipo

        try:

            if tipo == 'entero':

                valor_numerico = int(valor)

            else:

                valor_numerico = Decimal(valor)

        except (ValueError, InvalidOperation, TypeError):

            errores['valor'] = f'El valor debe ser un número {tipo} válido.'

            return errores

        # Validar rango

        if self.min_valor is not None and valor_numerico < self.min_valor:

            msg = self.mensaje_error or f'El valor debe ser al menos {self.min_valor}.'

            errores['valor'] = msg

        if self.max_valor is not None and valor_numerico > self.max_valor:

            msg = self.mensaje_error or f'El valor no debe exceder {self.max_valor}.'

            errores['valor'] = msg

        return errores


class JsonValidator(ValidadorConfig):

    """

    Valida que un valor sea JSON válido.

    Opcionalmente valida la estructura del JSON.

    """

    def __init__(

        self,

        esquema: Optional[Dict[str, Any]] = None,

        campos_requeridos: Optional[List[str]] = None,

    ):

        self.esquema = esquema

        self.campos_requeridos = campos_requeridos or []

    @property
    def descripcion(self) -> str:

        if self.campos_requeridos:

            return f"JSON con campos: {', '.join(self.campos_requeridos)}"

        return "JSON válido"

    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        errores = {}

        if tipo != 'json':

            errores['tipo'] = 'Este parámetro debe ser de tipo "json".'

            return errores

        try:

            data = json.loads(valor)

        except json.JSONDecodeError as e:

            errores['valor'] = f'JSON inválido: {str(e)}'

            return errores

        # Validar campos requeridos

        if self.campos_requeridos and isinstance(data, dict):

            faltantes = [c for c in self.campos_requeridos if c not in data]

            if faltantes:

                errores['valor'] = f'Campos requeridos faltantes: {", ".join(faltantes)}'

        return errores


class EmailValidator(ValidadorConfig):

    """Valida que un valor sea un email válido."""

    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    @property
    def descripcion(self) -> str:

        return "Email válido"

    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        errores = {}

        if tipo != 'texto':

            errores['tipo'] = 'Este parámetro debe ser de tipo "texto".'

            return errores

        if not self.EMAIL_REGEX.match(valor):

            errores['valor'] = 'El valor debe ser un email válido.'

        return errores


class UrlValidator(ValidadorConfig):

    """Valida que un valor sea una URL válida."""

    URL_REGEX = re.compile(

        r'^https?://'  # http:// o https://

        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # dominio

        r'localhost|'  # localhost

        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP

        r'(?::\d+)?'  # puerto opcional

        r'(?:/?|[/?]\S+)$', re.IGNORECASE

    )

    @property
    def descripcion(self) -> str:

        return "URL válida (http/https)"

    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        errores = {}

        if tipo != 'texto':

            errores['tipo'] = 'Este parámetro debe ser de tipo "texto".'

            return errores

        if not self.URL_REGEX.match(valor):

            errores['valor'] = 'El valor debe ser una URL válida (http:// o https://).'

        return errores


class ListaValoresValidator(ValidadorConfig):

    """Valida que un valor esté en una lista de valores permitidos."""

    def __init__(self, valores_permitidos: List[str], case_sensitive: bool = False):

        self.valores_permitidos = valores_permitidos

        self.case_sensitive = case_sensitive

    @property
    def descripcion(self) -> str:

        return f"Uno de: {', '.join(self.valores_permitidos)}"

    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        errores = {}

        if self.case_sensitive:

            es_valido = valor in self.valores_permitidos

        else:

            es_valido = valor.lower() in [v.lower() for v in self.valores_permitidos]

        if not es_valido:

            errores['valor'] = f'El valor debe ser uno de: {", ".join(self.valores_permitidos)}.'

        return errores


class TablaTasasValidator(ValidadorConfig):

    """

    Valida la estructura de la tabla de tasas de emisión.

    Espera un JSON array con objetos {limite: number|null, tasa: string}.

    """

    @property
    def descripcion(self) -> str:

        return "Tabla de tasas de emisión (JSON array)"

    def validar(self, valor: str, tipo: str) -> Dict[str, str]:

        errores = {}

        if tipo != 'json':

            errores['tipo'] = 'Este parámetro debe ser de tipo "json".'

            return errores

        try:

            data = json.loads(valor)

        except json.JSONDecodeError as e:

            errores['valor'] = f'JSON inválido: {str(e)}'

            return errores

        if not isinstance(data, list):

            errores['valor'] = 'La tabla de tasas debe ser un array JSON.'

            return errores

        for i, item in enumerate(data):

            if not isinstance(item, dict):

                errores['valor'] = f'El elemento {i} debe ser un objeto.'

                return errores

            if 'tasa' not in item:

                errores['valor'] = f'El elemento {i} debe tener campo "tasa".'

                return errores

            try:

                Decimal(str(item['tasa']))

            except (InvalidOperation, ValueError):

                errores['valor'] = f'El elemento {i} tiene una tasa inválida.'

                return errores

        return errores

# ==============================================================================

# REGISTRO DE VALIDADORES

# ==============================================================================


class RegistroValidadores:

    """

    Registry pattern para validadores de configuración.

    Permite registrar y obtener validadores por clave de configuración.

    """

    def __init__(self):

        self._validadores: Dict[str, Union[ValidadorConfig, Callable]] = {}

    def registrar(

        self,

        clave: str,

        validador: Union[ValidadorConfig, Callable[[str, str], Dict[str, str]]]

    ) -> 'RegistroValidadores':

        """

        Registra un validador para una clave de configuración.

        Args:

            clave: Nombre de la configuración (ej: 'PORCENTAJE_SUPERINTENDENCIA')

            validador: Instancia de ValidadorConfig o función callable

        Returns:

            self para encadenamiento

        """

        self._validadores[clave] = validador

        return self

    def registrar_multiples(

        self,

        claves: List[str],

        validador: Union[ValidadorConfig, Callable[[str, str], Dict[str, str]]]

    ) -> 'RegistroValidadores':

        """Registra el mismo validador para múltiples claves."""

        for clave in claves:

            self._validadores[clave] = validador

        return self

    def obtener(self, clave: str) -> Optional[Union[ValidadorConfig, Callable]]:

        """Obtiene el validador para una clave."""

        return self._validadores.get(clave)

    def tiene_validador(self, clave: str) -> bool:

        """Verifica si existe un validador para la clave."""

        return clave in self._validadores

    def validar(self, clave: str, valor: str, tipo: str) -> Dict[str, str]:

        """

        Ejecuta la validación para una clave.

        Returns:

            Dict vacío si es válido o no hay validador,

            Dict con errores {campo: mensaje} si hay errores

        """

        validador = self.obtener(clave)

        if validador is None:

            return {}

        if isinstance(validador, ValidadorConfig):

            return validador.validar(valor, tipo)

        elif callable(validador):

            return validador(valor, tipo)

        return {}

    @property
    def claves_registradas(self) -> List[str]:

        """Lista de claves que tienen validador registrado."""

        return list(self._validadores.keys())

    def documentacion(self) -> Dict[str, str]:

        """Genera documentación de todos los validadores registrados."""

        docs = {}

        for clave, validador in self._validadores.items():

            if isinstance(validador, ValidadorConfig):

                docs[clave] = validador.descripcion

            elif callable(validador):

                docs[clave] = validador.__doc__ or 'Validación personalizada'

        return docs

# ==============================================================================

# REGISTRO GLOBAL - SINGLETON

# ==============================================================================

# Crear registro global


registro_validadores = RegistroValidadores()

# Registrar validadores por defecto

registro_validadores.registrar_multiples(

    ['PORCENTAJE_SUPERINTENDENCIA', 'PORCENTAJE_SEGURO_CAMPESINO'],

    PorcentajeValidator(min_valor=0.0, max_valor=0.1)  # 0% a 10%

)

registro_validadores.registrar(

    'PORCENTAJE_IVA',

    PorcentajeValidator(min_valor=0.0, max_valor=0.25)  # 0% a 25%

)

registro_validadores.registrar(

    'PORCENTAJE_DESCUENTO_PRONTO_PAGO',

    PorcentajeValidator(min_valor=0.0, max_valor=0.2)  # 0% a 20%

)

registro_validadores.registrar(

    'DIAS_LIMITE_DESCUENTO_PRONTO_PAGO',

    RangoNumericoValidator(min_valor=1, max_valor=90, tipo_requerido='entero')

)

registro_validadores.registrar(

    'DIAS_ALERTA_VENCIMIENTO_POLIZA',

    RangoNumericoValidator(min_valor=1, max_valor=365, tipo_requerido='entero')

)

registro_validadores.registrar(

    'DIAS_ALERTA_DOCUMENTACION_SINIESTRO',

    RangoNumericoValidator(min_valor=1, max_valor=180, tipo_requerido='entero')

)

registro_validadores.registrar(

    'DIAS_ALERTA_RESPUESTA_ASEGURADORA',

    RangoNumericoValidator(min_valor=1, max_valor=90, tipo_requerido='entero')

)

registro_validadores.registrar(

    'HORAS_LIMITE_DEPOSITO_INDEMNIZACION',

    RangoNumericoValidator(min_valor=1, max_valor=720, tipo_requerido='entero')

)

registro_validadores.registrar(

    'EMAIL_GERENTE_SINIESTROS',

    EmailValidator()

)

registro_validadores.registrar(

    'SITE_URL',

    UrlValidator()

)

registro_validadores.registrar(

    'NOTIFICACIONES_WEBHOOK_URL',

    UrlValidator()

)

registro_validadores.registrar(

    'TABLA_TASAS_EMISION',

    TablaTasasValidator()

)

# ==============================================================================

# FUNCIÓN DE CONVENIENCIA

# ==============================================================================


def validar_configuracion(clave: str, valor: str, tipo: str) -> Dict[str, str]:

    """

    Función de conveniencia para validar una configuración.

    Args:

        clave: Nombre de la configuración

        valor: Valor a validar

        tipo: Tipo declarado de la configuración

    Returns:

        Dict vacío si es válido, Dict con errores si hay problemas

    """

    return registro_validadores.validar(clave, valor, tipo)
