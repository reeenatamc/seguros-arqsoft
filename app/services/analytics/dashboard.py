"""

Servicio de analíticas avanzadas para el dashboard.

Proporciona estadísticas comparativas entre períodos, tendencias y KPIs dinámicos.

"""



from django.db.models import Sum, Count, Avg, Q, F, Value, Case, When

from django.db.models.functions import TruncMonth, TruncYear, TruncWeek, TruncDay, Coalesce

from django.utils import timezone

from datetime import timedelta, date

from decimal import Decimal

from typing import Dict, List, Any, Optional, Tuple

import json





class DashboardAnalyticsService:

    """

    Servicio para generar analíticas comparativas del dashboard.

    Soporta comparaciones entre años, meses, semanas y días.

    """

    

    # Constantes para períodos

    PERIOD_YEAR = 'year'

    PERIOD_MONTH = 'month'

    PERIOD_WEEK = 'week'

    PERIOD_DAY = 'day'

    

    PERIOD_CHOICES = {

        PERIOD_YEAR: 'Año',

        PERIOD_MONTH: 'Mes',

        PERIOD_WEEK: 'Semana',

        PERIOD_DAY: 'Día',

    }

    

    # Nombres de meses en español

    MONTH_NAMES_ES = [

        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',

        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'

    ]

    

    MONTH_NAMES_SHORT_ES = [

        'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',

        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'

    ]



    @classmethod

    def get_date_range_for_period(

        cls,

        period_type: str,

        reference_date: Optional[date] = None,

        offset: int = 0

    ) -> Tuple[date, date]:

        """

        Calcula el rango de fechas para un período específico.

        

        Args:

            period_type: Tipo de período (year, month, week, day)

            reference_date: Fecha de referencia (por defecto hoy)

            offset: Desplazamiento hacia atrás (0 = período actual, 1 = período anterior, etc.)

        

        Returns:

            Tupla con (fecha_inicio, fecha_fin) del período

        """

        if reference_date is None:

            reference_date = timezone.now().date()

        

        if period_type == cls.PERIOD_YEAR:

            year = reference_date.year - offset

            start_date = date(year, 1, 1)

            end_date = date(year, 12, 31)

            

        elif period_type == cls.PERIOD_MONTH:

            # Calcular el mes con offset

            month = reference_date.month - offset

            year = reference_date.year

            while month <= 0:

                month += 12

                year -= 1

            while month > 12:

                month -= 12

                year += 1

            

            start_date = date(year, month, 1)

            # Último día del mes

            if month == 12:

                end_date = date(year + 1, 1, 1) - timedelta(days=1)

            else:

                end_date = date(year, month + 1, 1) - timedelta(days=1)

                

        elif period_type == cls.PERIOD_WEEK:

            # Inicio de la semana actual (lunes)

            days_since_monday = reference_date.weekday()

            start_of_week = reference_date - timedelta(days=days_since_monday)

            start_date = start_of_week - timedelta(weeks=offset)

            end_date = start_date + timedelta(days=6)

            

        else:  # PERIOD_DAY

            target_date = reference_date - timedelta(days=offset)

            start_date = target_date

            end_date = target_date

        

        return start_date, end_date



    @classmethod

    def get_period_label(cls, period_type: str, start_date: date, end_date: date) -> str:

        """

        Genera una etiqueta legible para el período.

        """

        if period_type == cls.PERIOD_YEAR:

            return str(start_date.year)

        elif period_type == cls.PERIOD_MONTH:

            return f"{cls.MONTH_NAMES_ES[start_date.month - 1]} {start_date.year}"

        elif period_type == cls.PERIOD_WEEK:

            return f"Sem {start_date.isocalendar()[1]} ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})"

        else:

            return start_date.strftime('%d/%m/%Y')



    @classmethod

    def get_comparative_stats(

        cls,

        period_type: str = PERIOD_MONTH,

        reference_date: Optional[date] = None

    ) -> Dict[str, Any]:

        """

        Obtiene estadísticas comparativas entre el período actual y el anterior.

        

        Returns:

            Diccionario con estadísticas actuales, anteriores, variación porcentual

            y etiquetas de período.

        """

        from app.models import Poliza, Factura, Siniestro, Alerta

        

        # Calcular rangos de fechas

        current_start, current_end = cls.get_date_range_for_period(

            period_type, reference_date, offset=0

        )

        previous_start, previous_end = cls.get_date_range_for_period(

            period_type, reference_date, offset=1

        )

        

        # Estadísticas de pólizas

        current_policies = cls._get_policy_stats(current_start, current_end)

        previous_policies = cls._get_policy_stats(previous_start, previous_end)

        

        # Estadísticas de facturas

        current_invoices = cls._get_invoice_stats(current_start, current_end)

        previous_invoices = cls._get_invoice_stats(previous_start, previous_end)

        

        # Estadísticas de siniestros

        current_claims = cls._get_claim_stats(current_start, current_end)

        previous_claims = cls._get_claim_stats(previous_start, previous_end)

        

        # Calcular variaciones

        def calculate_variation(current: Decimal, previous: Decimal) -> Dict[str, Any]:

            """Calcula variación porcentual y dirección del cambio."""

            if previous == 0:

                percentage = 100 if current > 0 else 0

            else:

                percentage = ((current - previous) / previous) * 100

            

            return {

                'current': float(current),

                'previous': float(previous),

                'change': float(current - previous),

                'percentage': round(float(percentage), 1),

                'trend': 'up' if current > previous else 'down' if current < previous else 'stable'

            }

        

        return {

            'period': {

                'type': period_type,

                'type_label': cls.PERIOD_CHOICES.get(period_type, period_type),

                'current': {

                    'start': current_start.isoformat(),

                    'end': current_end.isoformat(),

                    'label': cls.get_period_label(period_type, current_start, current_end)

                },

                'previous': {

                    'start': previous_start.isoformat(),

                    'end': previous_end.isoformat(),

                    'label': cls.get_period_label(period_type, previous_start, previous_end)

                }

            },

            'policies': {

                'new_count': calculate_variation(

                    Decimal(current_policies['new_count']),

                    Decimal(previous_policies['new_count'])

                ),

                'total_insured': calculate_variation(

                    current_policies['total_insured'],

                    previous_policies['total_insured']

                ),

                'expired_count': calculate_variation(

                    Decimal(current_policies['expired_count']),

                    Decimal(previous_policies['expired_count'])

                ),

            },

            'invoices': {

                'count': calculate_variation(

                    Decimal(current_invoices['count']),

                    Decimal(previous_invoices['count'])

                ),

                'total_amount': calculate_variation(

                    current_invoices['total_amount'],

                    previous_invoices['total_amount']

                ),

                'paid_amount': calculate_variation(

                    current_invoices['paid_amount'],

                    previous_invoices['paid_amount']

                ),

                'collection_rate': {

                    'current': current_invoices['collection_rate'],

                    'previous': previous_invoices['collection_rate'],

                    'trend': 'up' if current_invoices['collection_rate'] > previous_invoices['collection_rate'] else 'down'

                }

            },

            'claims': {

                'count': calculate_variation(

                    Decimal(current_claims['count']),

                    Decimal(previous_claims['count'])

                ),

                'estimated_amount': calculate_variation(

                    current_claims['estimated_amount'],

                    previous_claims['estimated_amount']

                ),

                'indemnified_amount': calculate_variation(

                    current_claims['indemnified_amount'],

                    previous_claims['indemnified_amount']

                ),

            }

        }



    @classmethod

    def _get_policy_stats(cls, start_date: date, end_date: date) -> Dict[str, Any]:

        """Obtiene estadísticas de pólizas para un rango de fechas."""

        from app.models import Poliza

        

        # Pólizas nuevas en el período

        new_policies = Poliza.objects.filter(

            fecha_creacion__date__gte=start_date,

            fecha_creacion__date__lte=end_date

        )

        

        # Pólizas vencidas en el período

        expired_policies = Poliza.objects.filter(

            fecha_fin__gte=start_date,

            fecha_fin__lte=end_date,

            estado='vencida'

        )

        

        new_count = new_policies.count()

        total_insured = new_policies.aggregate(

            total=Coalesce(Sum('suma_asegurada'), Value(Decimal('0')))

        )['total']

        

        return {

            'new_count': new_count,

            'total_insured': total_insured,

            'expired_count': expired_policies.count(),

        }



    @classmethod

    def _get_invoice_stats(cls, start_date: date, end_date: date) -> Dict[str, Any]:

        """Obtiene estadísticas de facturas para un rango de fechas."""

        from app.models import Factura

        

        invoices = Factura.objects.filter(

            fecha_emision__gte=start_date,

            fecha_emision__lte=end_date

        )

        

        count = invoices.count()

        total_amount = invoices.aggregate(

            total=Coalesce(Sum('monto_total'), Value(Decimal('0')))

        )['total']

        

        paid_amount = invoices.filter(estado='pagada').aggregate(

            total=Coalesce(Sum('monto_total'), Value(Decimal('0')))

        )['total']

        

        # Tasa de cobro

        collection_rate = round((paid_amount / total_amount * 100), 1) if total_amount > 0 else 0

        

        return {

            'count': count,

            'total_amount': total_amount,

            'paid_amount': paid_amount,

            'collection_rate': float(collection_rate),

        }



    @classmethod

    def _get_claim_stats(cls, start_date: date, end_date: date) -> Dict[str, Any]:

        """Obtiene estadísticas de siniestros para un rango de fechas."""

        from app.models import Siniestro

        

        claims = Siniestro.objects.filter(

            fecha_siniestro__date__gte=start_date,

            fecha_siniestro__date__lte=end_date

        )

        

        count = claims.count()

        estimated = claims.aggregate(

            total=Coalesce(Sum('monto_estimado'), Value(Decimal('0')))

        )['total']

        indemnified = claims.aggregate(

            total=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0')))

        )['total']

        

        return {

            'count': count,

            'estimated_amount': estimated,

            'indemnified_amount': indemnified,

        }



    @classmethod

    def get_trend_data(

        cls,

        period_type: str = PERIOD_MONTH,

        periods_count: int = 12

    ) -> Dict[str, Any]:

        """

        Obtiene datos de tendencia para múltiples períodos.

        Útil para gráficos de líneas/barras con histórico.

        

        Args:

            period_type: Tipo de período

            periods_count: Cantidad de períodos a incluir

            

        Returns:

            Diccionario con labels y datasets para gráficos

        """

        from app.models import Poliza, Factura, Siniestro

        

        labels = []

        policies_data = []

        invoices_amount_data = []

        claims_data = []

        claims_amount_data = []

        

        today = timezone.now().date()

        

        # Iterar desde el período más antiguo al más reciente

        for offset in range(periods_count - 1, -1, -1):

            start_date, end_date = cls.get_date_range_for_period(period_type, today, offset)

            

            # Etiqueta del período

            if period_type == cls.PERIOD_YEAR:

                label = str(start_date.year)

            elif period_type == cls.PERIOD_MONTH:

                label = cls.MONTH_NAMES_SHORT_ES[start_date.month - 1]

                if start_date.year != today.year:

                    label += f" '{str(start_date.year)[2:]}"

            elif period_type == cls.PERIOD_WEEK:

                label = f"S{start_date.isocalendar()[1]}"

            else:

                label = start_date.strftime('%d/%m')

            

            labels.append(label)

            

            # Datos de pólizas (nuevas en el período)

            policies_count = Poliza.objects.filter(

                fecha_creacion__date__gte=start_date,

                fecha_creacion__date__lte=end_date

            ).count()

            policies_data.append(policies_count)

            

            # Datos de facturas

            invoice_total = Factura.objects.filter(

                fecha_emision__gte=start_date,

                fecha_emision__lte=end_date

            ).aggregate(

                total=Coalesce(Sum('monto_total'), Value(Decimal('0')))

            )['total']

            invoices_amount_data.append(float(invoice_total))

            

            # Datos de siniestros

            claims_queryset = Siniestro.objects.filter(

                fecha_siniestro__date__gte=start_date,

                fecha_siniestro__date__lte=end_date

            )

            claims_count = claims_queryset.count()

            claims_amount = claims_queryset.aggregate(

                total=Coalesce(Sum('monto_estimado'), Value(Decimal('0')))

            )['total']

            

            claims_data.append(claims_count)

            claims_amount_data.append(float(claims_amount))

        

        return {

            'labels': labels,

            'datasets': {

                'policies': {

                    'label': 'Pólizas Nuevas',

                    'data': policies_data,

                    'color': '#3B82F6'  # blue-500

                },

                'invoices_amount': {

                    'label': 'Facturación ($)',

                    'data': invoices_amount_data,

                    'color': '#10B981'  # emerald-500

                },

                'claims_count': {

                    'label': 'Siniestros',

                    'data': claims_data,

                    'color': '#EF4444'  # red-500

                },

                'claims_amount': {

                    'label': 'Monto Siniestros ($)',

                    'data': claims_amount_data,

                    'color': '#F59E0B'  # amber-500

                }

            }

        }



    @classmethod

    def get_year_over_year_comparison(cls) -> Dict[str, Any]:

        """

        Compara el año actual con el año anterior mes a mes.

        Ideal para gráficos comparativos.

        """

        from app.models import Factura, Siniestro

        

        today = timezone.now().date()

        current_year = today.year

        previous_year = current_year - 1

        

        labels = cls.MONTH_NAMES_SHORT_ES[:today.month]  # Solo hasta el mes actual

        

        current_year_invoices = []

        previous_year_invoices = []

        current_year_claims = []

        previous_year_claims = []

        

        for month in range(1, today.month + 1):

            # Año actual

            current_invoice_total = Factura.objects.filter(

                fecha_emision__year=current_year,

                fecha_emision__month=month

            ).aggregate(

                total=Coalesce(Sum('monto_total'), Value(Decimal('0')))

            )['total']

            current_year_invoices.append(float(current_invoice_total))

            

            current_claim_count = Siniestro.objects.filter(

                fecha_siniestro__year=current_year,

                fecha_siniestro__month=month

            ).count()

            current_year_claims.append(current_claim_count)

            

            # Año anterior

            prev_invoice_total = Factura.objects.filter(

                fecha_emision__year=previous_year,

                fecha_emision__month=month

            ).aggregate(

                total=Coalesce(Sum('monto_total'), Value(Decimal('0')))

            )['total']

            previous_year_invoices.append(float(prev_invoice_total))

            

            prev_claim_count = Siniestro.objects.filter(

                fecha_siniestro__year=previous_year,

                fecha_siniestro__month=month

            ).count()

            previous_year_claims.append(prev_claim_count)

        

        return {

            'labels': labels,

            'current_year': current_year,

            'previous_year': previous_year,

            'invoices': {

                'current': current_year_invoices,

                'previous': previous_year_invoices,

            },

            'claims': {

                'current': current_year_claims,

                'previous': previous_year_claims,

            }

        }



    @classmethod

    def get_quick_actions_data(cls) -> Dict[str, Any]:

        """

        Obtiene datos para las acciones rápidas del dashboard.

        Incluye contadores y alertas para tareas pendientes.

        """

        from app.models import Poliza, Factura, Siniestro, Alerta

        

        today = timezone.now().date()

        in_7_days = today + timedelta(days=7)

        in_30_days = today + timedelta(days=30)

        

        return {

            'policies_expiring_soon': Poliza.objects.filter(

                fecha_fin__gte=today,

                fecha_fin__lte=in_7_days,

                estado__in=['vigente', 'por_vencer']

            ).count(),

            'policies_expiring_month': Poliza.objects.filter(

                fecha_fin__gte=today,

                fecha_fin__lte=in_30_days,

                estado__in=['vigente', 'por_vencer']

            ).count(),

            'overdue_invoices': Factura.objects.filter(

                estado='vencida'

            ).count(),

            'pending_claims_docs': Siniestro.objects.filter(

                estado='documentacion_pendiente'

            ).count(),

            'claims_awaiting_response': Siniestro.objects.filter(

                estado='enviado_aseguradora',

                fecha_envio_aseguradora__lte=today - timedelta(days=8)

            ).count(),

            'unread_alerts': Alerta.objects.filter(

                estado__in=['pendiente', 'enviada']

            ).count(),

        }



    @classmethod

    def get_top_performers(cls, limit: int = 5) -> Dict[str, Any]:

        """

        Obtiene las entidades con mejor/peor rendimiento.

        """

        from app.models import Poliza, Siniestro, CompaniaAseguradora

        

        today = timezone.now().date()

        year_start = date(today.year, 1, 1)

        

        # Compañías con más pólizas activas

        top_insurers_by_policies = list(

            Poliza.objects.filter(estado='vigente')

            .values('compania_aseguradora__nombre')

            .annotate(

                count=Count('id'),

                total_insured=Sum('suma_asegurada')

            )

            .order_by('-count')[:limit]

        )

        

        # Compañías con más siniestros

        top_insurers_by_claims = list(

            Siniestro.objects.filter(fecha_siniestro__date__gte=year_start)

            .values('poliza__compania_aseguradora__nombre')

            .annotate(

                count=Count('id'),

                total_amount=Sum('monto_estimado')

            )

            .order_by('-count')[:limit]

        )

        

        return {

            'top_insurers_by_policies': top_insurers_by_policies,

            'top_insurers_by_claims': top_insurers_by_claims,

        }



    @classmethod

    def get_dashboard_summary(

        cls,

        period_type: str = PERIOD_MONTH

    ) -> Dict[str, Any]:

        """

        Obtiene un resumen completo para el dashboard.

        Combina todas las métricas en una sola llamada.

        """

        return {

            'comparative': cls.get_comparative_stats(period_type),

            'trend': cls.get_trend_data(period_type),

            'year_over_year': cls.get_year_over_year_comparison(),

            'quick_actions': cls.get_quick_actions_data(),

            'top_performers': cls.get_top_performers(),

        }

