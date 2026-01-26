"""

Data Transfer Objects (DTOs) para vistas de solo lectura.


PROBLEMA (ISP):

    Cuando pasas un modelo completo (Poliza, Siniestro) a un template,

    estás exponiendo decenas de métodos y propiedades que no se usan.


    # En views.py

    context = {'poliza': poliza}  # ← 50+ métodos/propiedades disponibles


    # En el template solo usas 3:

    {{ poliza.numero_poliza }}

    {{ poliza.fecha_fin }}

    {{ poliza.estado }}


SOLUCIÓN:

    Usar DTOs (dataclasses ligeras) que solo contienen lo necesario.


    # En views.py

    from app.dtos import PolizaResumen

    context = {'poliza': PolizaResumen.from_model(poliza)}  # ← solo 3 campos


BENEFICIOS:

    - Menor acoplamiento entre vistas y modelos

    - Documentación implícita de qué datos usa cada vista

    - Facilita testing (no necesitas modelo completo)

    - Mejor rendimiento (no carga relaciones innecesarias)

    - Serialización JSON más limpia para APIs


USO:

    from app.dtos import (

        PolizaResumen, PolizaDetalle,

        SiniestroResumen, SiniestroLista,

        FacturaResumen,

    )


    # Desde un modelo

    dto = PolizaResumen.from_model(poliza)


    # Desde un queryset (optimizado)

    dtos = PolizaResumen.from_queryset(Poliza.objects.filter(estado='vigente'))


    # En API responses

    return JsonResponse(dto.to_dict())

"""


from dataclasses import dataclass, field, asdict

from datetime import date, datetime

from decimal import Decimal

from typing import Optional, List, Dict, Any


# ==============================================================================

# BASE DTO

# ==============================================================================


@dataclass
class BaseDTO:

    """Clase base para todos los DTOs."""

    def to_dict(self) -> Dict[str, Any]:

        """Convierte el DTO a diccionario para JSON."""

        result = {}

        for key, value in asdict(self).items():

            if isinstance(value, (date, datetime)):

                result[key] = value.isoformat()

            elif isinstance(value, Decimal):

                result[key] = str(value)

            elif isinstance(value, BaseDTO):

                result[key] = value.to_dict()

            elif isinstance(value, list) and value and isinstance(value[0], BaseDTO):

                result[key] = [item.to_dict() for item in value]

            else:

                result[key] = value

        return result

# ==============================================================================

# POLIZA DTOs

# ==============================================================================


@dataclass
class PolizaResumen(BaseDTO):

    """

    DTO mínimo para listas y referencias.

    Usado en: select dropdowns, tablas de resumen, breadcrumbs.

    """

    id: int

    numero_poliza: str

    compania: str

    estado: str

    fecha_fin: date

    dias_para_vencer: int = 0

    @classmethod
    def from_model(cls, poliza) -> 'PolizaResumen':

        return cls(

            id=poliza.id,

            numero_poliza=poliza.numero_poliza,

            compania=poliza.compania_aseguradora.nombre,

            estado=poliza.get_estado_display(),

            fecha_fin=poliza.fecha_fin,

            dias_para_vencer=poliza.dias_para_vencer,

        )

    @classmethod
    def from_queryset(cls, queryset) -> List['PolizaResumen']:

        """Optimizado para querysets."""

        return [

            cls.from_model(p)

            for p in queryset.select_related('compania_aseguradora')

        ]

@dataclass
class PolizaDetalle(BaseDTO):

    """

    DTO para vista de detalle de póliza.

    Incluye toda la información necesaria para la página de detalle.

    """

    id: int

    numero_poliza: str

    compania: str

    compania_id: int

    tipo_poliza: str

    grupo_ramo: str

    estado: str

    fecha_inicio: date

    fecha_fin: date

    suma_asegurada: Decimal

    prima_neta: Decimal

    prima_total: Decimal

    corredor: Optional[str] = None

    corredor_email: Optional[str] = None

    dias_para_vencer: int = 0

    bienes_count: int = 0

    siniestros_count: int = 0

    @classmethod
    def from_model(cls, poliza) -> 'PolizaDetalle':

        return cls(

            id=poliza.id,

            numero_poliza=poliza.numero_poliza,

            compania=poliza.compania_aseguradora.nombre,

            compania_id=poliza.compania_aseguradora_id,

            tipo_poliza=poliza.tipo_poliza.nombre if poliza.tipo_poliza else 'N/A',

            grupo_ramo=poliza.grupo_ramo.nombre if poliza.grupo_ramo else 'N/A',

            estado=poliza.get_estado_display(),

            fecha_inicio=poliza.fecha_inicio,

            fecha_fin=poliza.fecha_fin,

            suma_asegurada=poliza.suma_asegurada,

            prima_neta=poliza.prima_neta or Decimal('0'),

            prima_total=poliza.prima_total or Decimal('0'),

            corredor=poliza.corredor_seguros.nombre if poliza.corredor_seguros else None,

            corredor_email=poliza.corredor_seguros.email if poliza.corredor_seguros else None,

            dias_para_vencer=poliza.dias_para_vencer,

            bienes_count=poliza.bienes_asegurados.count(),

            siniestros_count=poliza.siniestros.count(),

        )

@dataclass
class PolizaCard(BaseDTO):

    """

    DTO para cards/widgets del dashboard.

    Solo lo esencial para mostrar en un card.

    """

    id: int

    numero_poliza: str

    compania: str

    estado: str

    estado_badge_class: str

    fecha_fin: date

    dias_para_vencer: int

    suma_asegurada: Decimal

    @classmethod
    def from_model(cls, poliza) -> 'PolizaCard':

        # Determinar clase CSS del badge

        estado = poliza.estado

        badge_classes = {

            'vigente': 'bg-green-100 text-green-800',

            'por_vencer': 'bg-yellow-100 text-yellow-800',

            'vencida': 'bg-red-100 text-red-800',

            'cancelada': 'bg-gray-100 text-gray-800',

        }

        return cls(

            id=poliza.id,

            numero_poliza=poliza.numero_poliza,

            compania=poliza.compania_aseguradora.nombre,

            estado=poliza.get_estado_display(),

            estado_badge_class=badge_classes.get(estado, 'bg-gray-100 text-gray-800'),

            fecha_fin=poliza.fecha_fin,

            dias_para_vencer=poliza.dias_para_vencer,

            suma_asegurada=poliza.suma_asegurada,

        )

# ==============================================================================

# SINIESTRO DTOs

# ==============================================================================


@dataclass
class SiniestroResumen(BaseDTO):

    """

    DTO mínimo para listas y referencias.

    Usado en: select dropdowns, tablas de resumen, notificaciones.

    """

    id: int

    numero_siniestro: str

    tipo: str

    estado: str

    fecha_siniestro: datetime

    bien_nombre: str

    @classmethod
    def from_model(cls, siniestro) -> 'SiniestroResumen':

        return cls(

            id=siniestro.id,

            numero_siniestro=siniestro.numero_siniestro,

            tipo=siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else 'N/A',

            estado=siniestro.get_estado_display(),

            fecha_siniestro=siniestro.fecha_siniestro,

            bien_nombre=siniestro.bien_nombre,

        )

@dataclass
class SiniestroLista(BaseDTO):

    """

    DTO para listados de siniestros.

    Incluye información para tablas y filtros.

    """

    id: int

    numero_siniestro: str

    tipo: str

    estado: str

    estado_badge_class: str

    fecha_siniestro: date

    fecha_registro: date

    bien_nombre: str

    poliza_numero: str

    monto_estimado: Decimal

    dias_gestion: int

    @classmethod
    def from_model(cls, siniestro) -> 'SiniestroLista':

        estado = siniestro.estado

        badge_classes = {

            'registrado': 'bg-blue-100 text-blue-800',

            'documentacion_pendiente': 'bg-yellow-100 text-yellow-800',

            'enviado_aseguradora': 'bg-purple-100 text-purple-800',

            'en_evaluacion': 'bg-indigo-100 text-indigo-800',

            'aprobado': 'bg-green-100 text-green-800',

            'rechazado': 'bg-red-100 text-red-800',

            'liquidado': 'bg-teal-100 text-teal-800',

            'cerrado': 'bg-gray-100 text-gray-800',

        }

        return cls(

            id=siniestro.id,

            numero_siniestro=siniestro.numero_siniestro,

            tipo=siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else 'N/A',

            estado=siniestro.get_estado_display(),

            estado_badge_class=badge_classes.get(estado, 'bg-gray-100 text-gray-800'),

            fecha_siniestro=siniestro.fecha_siniestro.date() if siniestro.fecha_siniestro else None,

            fecha_registro=siniestro.fecha_registro.date() if siniestro.fecha_registro else None,

            bien_nombre=siniestro.bien_nombre,

            poliza_numero=siniestro.poliza.numero_poliza if siniestro.poliza else 'N/A',

            monto_estimado=siniestro.monto_estimado or Decimal('0'),

            dias_gestion=siniestro.dias_gestion,

        )

    @classmethod
    def from_queryset(cls, queryset) -> List['SiniestroLista']:

        return [

            cls.from_model(s)

            for s in queryset.select_related('tipo_siniestro', 'poliza')

        ]

@dataclass
class SiniestroDetalle(BaseDTO):

    """

    DTO completo para vista de detalle.

    """

    id: int

    numero_siniestro: str

    tipo: str

    estado: str

    fecha_siniestro: datetime

    fecha_registro: datetime

    # Bien afectado

    bien_nombre: str

    bien_marca: str

    bien_modelo: str

    bien_serie: str

    bien_codigo_activo: str

    # Póliza

    poliza_id: int

    poliza_numero: str

    poliza_compania: str

    # Responsable

    responsable_nombre: Optional[str]

    responsable_email: Optional[str]

    # Ubicación y descripción

    ubicacion: str

    causa: str

    descripcion: str

    # Montos

    monto_estimado: Decimal

    monto_indemnizado: Optional[Decimal]

    deducible_aplicado: Optional[Decimal]

    # Métricas

    dias_gestion: int

    dias_desde_registro: int

    @classmethod
    def from_model(cls, siniestro) -> 'SiniestroDetalle':

        return cls(

            id=siniestro.id,

            numero_siniestro=siniestro.numero_siniestro,

            tipo=siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else 'N/A',

            estado=siniestro.get_estado_display(),

            fecha_siniestro=siniestro.fecha_siniestro,

            fecha_registro=siniestro.fecha_registro,

            bien_nombre=siniestro.bien_nombre,

            bien_marca=siniestro.bien_marca or '',

            bien_modelo=siniestro.bien_modelo or '',

            bien_serie=siniestro.bien_serie or '',

            bien_codigo_activo=siniestro.bien_codigo_activo or '',

            poliza_id=siniestro.poliza_id,

            poliza_numero=siniestro.poliza.numero_poliza if siniestro.poliza else 'N/A',

            poliza_compania=siniestro.poliza.compania_aseguradora.nombre if siniestro.poliza else 'N/A',

            responsable_nombre=siniestro.responsable_custodio.nombre if siniestro.responsable_custodio else None,

            responsable_email=siniestro.responsable_custodio.email if siniestro.responsable_custodio else None,

            ubicacion=siniestro.ubicacion,

            causa=siniestro.causa,

            descripcion=siniestro.descripcion_detallada,

            monto_estimado=siniestro.monto_estimado or Decimal('0'),

            monto_indemnizado=siniestro.monto_indemnizado,

            deducible_aplicado=siniestro.deducible_aplicado,

            dias_gestion=siniestro.dias_gestion,

            dias_desde_registro=siniestro.dias_desde_registro,

        )

# ==============================================================================

# FACTURA DTOs

# ==============================================================================


@dataclass
class FacturaResumen(BaseDTO):

    """

    DTO mínimo para listas y referencias.

    """

    id: int

    numero_factura: str

    poliza_numero: str

    estado: str

    monto_total: Decimal

    saldo_pendiente: Decimal

    fecha_vencimiento: date

    @classmethod
    def from_model(cls, factura) -> 'FacturaResumen':

        return cls(

            id=factura.id,

            numero_factura=factura.numero_factura,

            poliza_numero=factura.poliza.numero_poliza if factura.poliza else 'N/A',

            estado=factura.get_estado_display(),

            monto_total=factura.monto_total,

            saldo_pendiente=factura.saldo_pendiente,

            fecha_vencimiento=factura.fecha_vencimiento,

        )

@dataclass
class FacturaLista(BaseDTO):

    """

    DTO para listados de facturas.

    """

    id: int

    numero_factura: str

    poliza_numero: str

    compania: str

    estado: str

    estado_badge_class: str

    subtotal: Decimal

    iva: Decimal

    monto_total: Decimal

    saldo_pendiente: Decimal

    fecha_emision: date

    fecha_vencimiento: date

    dias_para_vencimiento: int

    esta_vencida: bool

    @classmethod
    def from_model(cls, factura) -> 'FacturaLista':

        estado = factura.estado

        badge_classes = {

            'pendiente': 'bg-yellow-100 text-yellow-800',

            'parcial': 'bg-blue-100 text-blue-800',

            'pagada': 'bg-green-100 text-green-800',

            'vencida': 'bg-red-100 text-red-800',

            'anulada': 'bg-gray-100 text-gray-800',

        }

        return cls(

            id=factura.id,

            numero_factura=factura.numero_factura,

            poliza_numero=factura.poliza.numero_poliza if factura.poliza else 'N/A',

            compania=factura.poliza.compania_aseguradora.nombre if factura.poliza else 'N/A',

            estado=factura.get_estado_display(),

            estado_badge_class=badge_classes.get(estado, 'bg-gray-100 text-gray-800'),

            subtotal=factura.subtotal,

            iva=factura.iva,

            monto_total=factura.monto_total,

            saldo_pendiente=factura.saldo_pendiente,

            fecha_emision=factura.fecha_emision,

            fecha_vencimiento=factura.fecha_vencimiento,

            dias_para_vencimiento=factura.dias_para_vencimiento,

            esta_vencida=factura.esta_vencida,

        )

# ==============================================================================

# BIEN ASEGURADO DTOs

# ==============================================================================


@dataclass
class BienAseguradoResumen(BaseDTO):

    """

    DTO mínimo para listas y selects.

    """

    id: int

    codigo: str

    nombre: str

    poliza_numero: str

    valor_asegurado: Decimal

    estado: str

    @classmethod
    def from_model(cls, bien) -> 'BienAseguradoResumen':

        return cls(

            id=bien.id,

            codigo=bien.codigo_bien,

            nombre=bien.nombre,

            poliza_numero=bien.poliza.numero_poliza if bien.poliza else 'N/A',

            valor_asegurado=bien.valor_asegurado,

            estado=bien.get_estado_display(),

        )

@dataclass
class BienAseguradoLista(BaseDTO):

    """

    DTO para tablas de bienes asegurados.

    """

    id: int

    codigo: str

    nombre: str

    categoria: str

    marca: str

    modelo: str

    ubicacion: str

    responsable: Optional[str]

    valor_asegurado: Decimal

    estado: str

    estado_badge_class: str

    condicion: str

    tiene_siniestros: bool

    @classmethod
    def from_model(cls, bien) -> 'BienAseguradoLista':

        estado = bien.estado

        badge_classes = {

            'activo': 'bg-green-100 text-green-800',

            'inactivo': 'bg-gray-100 text-gray-800',

            'dado_de_baja': 'bg-red-100 text-red-800',

            'siniestrado': 'bg-orange-100 text-orange-800',

            'transferido': 'bg-blue-100 text-blue-800',

        }

        return cls(

            id=bien.id,

            codigo=bien.codigo_bien,

            nombre=bien.nombre,

            categoria=bien.categoria or 'Sin categoría',

            marca=bien.marca or '',

            modelo=bien.modelo or '',

            ubicacion=bien.ubicacion or '',

            responsable=bien.responsable_custodio.nombre if bien.responsable_custodio else None,

            valor_asegurado=bien.valor_asegurado,

            estado=bien.get_estado_display(),

            estado_badge_class=badge_classes.get(estado, 'bg-gray-100 text-gray-800'),

            condicion=bien.get_condicion_display() if bien.condicion else 'N/A',

            tiene_siniestros=bien.tiene_siniestros,

        )

# ==============================================================================

# DASHBOARD DTOs

# ==============================================================================


@dataclass
class DashboardStats(BaseDTO):

    """

    DTO para estadísticas del dashboard.

    Evita múltiples queries y cálculos en el template.

    """

    # Pólizas

    polizas_total: int

    polizas_vigentes: int

    polizas_por_vencer: int

    polizas_vencidas: int

    # Siniestros

    siniestros_total: int

    siniestros_abiertos: int

    siniestros_cerrados_mes: int

    # Facturas

    facturas_pendientes: int

    facturas_vencidas: int

    total_por_cobrar: Decimal

    # Indicadores

    tasa_siniestralidad: Decimal = Decimal('0')

    dias_promedio_gestion: int = 0

    @classmethod
    def calcular(cls) -> 'DashboardStats':

        """Calcula todas las estadísticas en queries optimizadas."""

        from app.models import Poliza, Siniestro, Factura

        from django.db.models import Sum, Avg, Count, Q

        from django.utils import timezone

        from datetime import timedelta

        hoy = timezone.now().date()

        inicio_mes = hoy.replace(day=1)

        # Pólizas

        polizas = Poliza.objects.aggregate(

            total=Count('id'),

            vigentes=Count('id', filter=Q(estado='vigente')),

            por_vencer=Count('id', filter=Q(estado='por_vencer')),

            vencidas=Count('id', filter=Q(estado='vencida')),

        )

        # Siniestros

        siniestros = Siniestro.objects.aggregate(

            total=Count('id'),

            abiertos=Count('id', filter=~Q(estado__in=['cerrado', 'rechazado'])),

            cerrados_mes=Count('id', filter=Q(

                estado='cerrado',

                fecha_registro__gte=inicio_mes

            )),

            dias_promedio=Avg('dias_gestion', filter=Q(estado='cerrado')),

        )

        # Facturas

        facturas = Factura.objects.aggregate(

            pendientes=Count('id', filter=Q(estado='pendiente')),

            vencidas=Count('id', filter=Q(estado='vencida')),

            por_cobrar=Sum('monto_total', filter=Q(estado__in=['pendiente', 'parcial', 'vencida'])),

        )

        return cls(

            polizas_total=polizas['total'] or 0,

            polizas_vigentes=polizas['vigentes'] or 0,

            polizas_por_vencer=polizas['por_vencer'] or 0,

            polizas_vencidas=polizas['vencidas'] or 0,

            siniestros_total=siniestros['total'] or 0,

            siniestros_abiertos=siniestros['abiertos'] or 0,

            siniestros_cerrados_mes=siniestros['cerrados_mes'] or 0,

            facturas_pendientes=facturas['pendientes'] or 0,

            facturas_vencidas=facturas['vencidas'] or 0,

            total_por_cobrar=facturas['por_cobrar'] or Decimal('0'),

            dias_promedio_gestion=int(siniestros['dias_promedio'] or 0),

        )

# ==============================================================================

# REPORTE DTOs

# ==============================================================================


@dataclass
class ReporteSiniestroContadora(BaseDTO):

    """

    DTO específico para el reporte de días de gestión de la contadora.

    """

    id: int

    numero_siniestro: str

    tipo: str

    bien_nombre: str

    poliza_numero: str

    fecha_siniestro: date

    fecha_registro: date

    dias_gestion: int

    estado: str

    monto_estimado: Decimal

    monto_indemnizado: Optional[Decimal]

    @classmethod
    def from_model(cls, siniestro) -> 'ReporteSiniestroContadora':

        return cls(

            id=siniestro.id,

            numero_siniestro=siniestro.numero_siniestro,

            tipo=siniestro.tipo_siniestro.nombre if siniestro.tipo_siniestro else 'N/A',

            bien_nombre=siniestro.bien_nombre,

            poliza_numero=siniestro.poliza.numero_poliza if siniestro.poliza else 'N/A',

            fecha_siniestro=siniestro.fecha_siniestro.date() if siniestro.fecha_siniestro else None,

            fecha_registro=siniestro.fecha_registro.date() if siniestro.fecha_registro else None,

            dias_gestion=siniestro.dias_gestion,

            estado=siniestro.get_estado_display(),

            monto_estimado=siniestro.monto_estimado or Decimal('0'),

            monto_indemnizado=siniestro.monto_indemnizado,

        )
