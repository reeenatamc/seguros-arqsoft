"""
Clases base y tipos compartidos para los servicios de dominio.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ResultadoValidacion:
    """Resultado de una validación de negocio."""
    es_valido: bool
    errores: Dict[str, str] = None
    
    def __post_init__(self):
        if self.errores is None:
            self.errores = {}
    
    def agregar_error(self, campo: str, mensaje: str) -> 'ResultadoValidacion':
        """Agrega un error y retorna self para encadenamiento."""
        self.errores[campo] = mensaje
        self.es_valido = False
        return self
    
    def fusionar(self, otro: 'ResultadoValidacion') -> 'ResultadoValidacion':
        """Fusiona otro resultado de validación."""
        if not otro.es_valido:
            self.es_valido = False
            self.errores.update(otro.errores)
        return self


@dataclass
class ResultadoOperacion:
    """Resultado de una operación de servicio."""
    exitoso: bool
    objeto: Any = None
    errores: Dict[str, str] = None
    mensaje: str = ""
    
    def __post_init__(self):
        if self.errores is None:
            self.errores = {}
    
    @classmethod
    def exito(cls, objeto: Any, mensaje: str = "") -> 'ResultadoOperacion':
        """Factory para resultado exitoso."""
        return cls(exitoso=True, objeto=objeto, mensaje=mensaje)
    
    @classmethod
    def fallo(cls, errores: Dict[str, str], mensaje: str = "") -> 'ResultadoOperacion':
        """Factory para resultado fallido."""
        return cls(exitoso=False, errores=errores, mensaje=mensaje)
    
    @classmethod
    def desde_validacion(cls, validacion: ResultadoValidacion, mensaje: str = "") -> 'ResultadoOperacion':
        """Crea ResultadoOperacion desde ResultadoValidacion fallida."""
        return cls(
            exitoso=False,
            errores=validacion.errores,
            mensaje=mensaje or "Error de validación"
        )


class BaseService:
    """Clase base para servicios de dominio."""
    
    @staticmethod
    def _get_config(clave: str, default: Any) -> Any:
        """Obtiene configuración del sistema."""
        from app.models import ConfiguracionSistema
        return ConfiguracionSistema.get_config(clave, default)
