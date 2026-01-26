"""

Servicios de Analytics y Estadísticas.

Dashboard, KPIs, tendencias y análisis de datos.

"""

from .avanzados import AdvancedAnalyticsService
from .dashboard import DashboardAnalyticsService
from .estadisticas import EstadisticasService
from .filters import DashboardFiltersService, DateRangePresets

__all__ = [
    "EstadisticasService",
    "DashboardAnalyticsService",
    "DashboardFiltersService",
    "DateRangePresets",
    "AdvancedAnalyticsService",
]
