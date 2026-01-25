"""
Servicios de Analytics y Estadísticas.
Dashboard, KPIs, tendencias y análisis de datos.
"""

from .estadisticas import EstadisticasService
from .dashboard import DashboardAnalyticsService
from .filters import DashboardFiltersService, DateRangePresets
from .avanzados import AdvancedAnalyticsService

__all__ = [
    'EstadisticasService',
    'DashboardAnalyticsService',
    'DashboardFiltersService',
    'DateRangePresets',
    'AdvancedAnalyticsService',
]
