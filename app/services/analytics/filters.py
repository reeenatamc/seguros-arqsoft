"""

Servicio de filtros dinámicos para el dashboard.

Proporciona filtros avanzados estilo Odoo con date range picker,

filtros por entidad, y generación de reportes personalizables.

"""

from django.db.models import Sum, Count, Avg, Q, F, Value, Min, Max

from django.db.models.functions import Coalesce, TruncMonth, TruncDay, TruncWeek

from django.utils import timezone

from datetime import timedelta, date, datetime

from decimal import Decimal

from typing import Dict, List, Any, Optional, Tuple

import json


class DateRangePresets:

    """

    Presets de rangos de fechas predefinidos para el selector.

    """

    TODAY = 'today'

    YESTERDAY = 'yesterday'

    THIS_WEEK = 'this_week'

    LAST_WEEK = 'last_week'

    THIS_MONTH = 'this_month'

    LAST_MONTH = 'last_month'

    THIS_QUARTER = 'this_quarter'

    LAST_QUARTER = 'last_quarter'

    THIS_YEAR = 'this_year'

    LAST_YEAR = 'last_year'

    LAST_7_DAYS = 'last_7_days'

    LAST_30_DAYS = 'last_30_days'

    LAST_90_DAYS = 'last_90_days'

    LAST_365_DAYS = 'last_365_days'

    CUSTOM = 'custom'

    CHOICES = {

        TODAY: 'Hoy',

        YESTERDAY: 'Ayer',

        THIS_WEEK: 'Esta semana',

        LAST_WEEK: 'Semana pasada',

        THIS_MONTH: 'Este mes',

        LAST_MONTH: 'Mes pasado',

        THIS_QUARTER: 'Este trimestre',

        LAST_QUARTER: 'Trimestre pasado',

        THIS_YEAR: 'Este año',

        LAST_YEAR: 'Año pasado',

        LAST_7_DAYS: 'Últimos 7 días',

        LAST_30_DAYS: 'Últimos 30 días',

        LAST_90_DAYS: 'Últimos 90 días',

        LAST_365_DAYS: 'Últimos 365 días',

        CUSTOM: 'Personalizado',

    }

    @classmethod
    def get_date_range(cls, preset: str, custom_start: date = None, custom_end: date = None) -> Tuple[date, date]:

        """

        Obtiene el rango de fechas para un preset dado.

        Returns:

            Tupla (fecha_inicio, fecha_fin)

        """

        today = timezone.now().date()

        if preset == cls.TODAY:

            return today, today

        elif preset == cls.YESTERDAY:

            yesterday = today - timedelta(days=1)

            return yesterday, yesterday

        elif preset == cls.THIS_WEEK:

            # Semana empieza el lunes

            start = today - timedelta(days=today.weekday())

            return start, today

        elif preset == cls.LAST_WEEK:

            start = today - timedelta(days=today.weekday() + 7)

            end = start + timedelta(days=6)

            return start, end

        elif preset == cls.THIS_MONTH:

            start = date(today.year, today.month, 1)

            return start, today

        elif preset == cls.LAST_MONTH:

            # Primer día del mes pasado

            if today.month == 1:

                start = date(today.year - 1, 12, 1)

                end = date(today.year - 1, 12, 31)

            else:

                start = date(today.year, today.month - 1, 1)

                # Último día del mes pasado

                end = date(today.year, today.month, 1) - timedelta(days=1)

            return start, end

        elif preset == cls.THIS_QUARTER:

            quarter = (today.month - 1) // 3

            start = date(today.year, quarter * 3 + 1, 1)

            return start, today

        elif preset == cls.LAST_QUARTER:

            quarter = (today.month - 1) // 3

            if quarter == 0:

                start = date(today.year - 1, 10, 1)

                end = date(today.year - 1, 12, 31)

            else:

                start = date(today.year, (quarter - 1) * 3 + 1, 1)

                end = date(today.year, quarter * 3 + 1, 1) - timedelta(days=1)

            return start, end

        elif preset == cls.THIS_YEAR:

            start = date(today.year, 1, 1)

            return start, today

        elif preset == cls.LAST_YEAR:

            start = date(today.year - 1, 1, 1)

            end = date(today.year - 1, 12, 31)

            return start, end

        elif preset == cls.LAST_7_DAYS:

            start = today - timedelta(days=6)

            return start, today

        elif preset == cls.LAST_30_DAYS:

            start = today - timedelta(days=29)

            return start, today

        elif preset == cls.LAST_90_DAYS:

            start = today - timedelta(days=89)

            return start, today

        elif preset == cls.LAST_365_DAYS:

            start = today - timedelta(days=364)

            return start, today

        elif preset == cls.CUSTOM and custom_start and custom_end:

            return custom_start, custom_end

        # Default: últimos 30 días

        return today - timedelta(days=29), today


class DashboardFiltersService:

    """

    Servicio para manejar filtros dinámicos del dashboard.

    Soporta filtros por fecha, compañía, corredor, tipo de póliza, estado, etc.

    """

    @classmethod
    def get_available_filters(cls) -> Dict[str, Any]:

        """

        Obtiene todos los filtros disponibles con sus opciones.

        Útil para poblar los selectores en el frontend.

        """

        from app.models import (

            CompaniaAseguradora, CorredorSeguros, TipoPoliza,

            TipoSiniestro, Poliza, Factura, Siniestro

        )

        return {

            'date_presets': DateRangePresets.CHOICES,

            'insurers': list(

                CompaniaAseguradora.objects.filter(activo=True)

                .values('id', 'nombre')

                .order_by('nombre')

            ),

            'brokers': list(

                CorredorSeguros.objects.filter(activo=True)

                .values('id', 'nombre')

                .order_by('nombre')

            ),

            'policy_types': list(

                TipoPoliza.objects.filter(activo=True)

                .values('id', 'nombre')

                .order_by('nombre')

            ),

            'claim_types': list(

                TipoSiniestro.objects.filter(activo=True)

                .values('id', 'nombre')

                .order_by('nombre')

            ),

            'policy_states': [

                {'value': choice[0], 'label': choice[1]}

                for choice in Poliza.ESTADO_CHOICES

            ],

            'invoice_states': [

                {'value': choice[0], 'label': choice[1]}

                for choice in Factura.ESTADO_CHOICES

            ],

            'claim_states': [

                {'value': choice[0], 'label': choice[1]}

                for choice in Siniestro.ESTADO_CHOICES

            ],

        }

    @classmethod
    def parse_filters_from_request(cls, request) -> Dict[str, Any]:

        """

        Parsea los filtros desde los parámetros GET de la request.

        """

        params = request.GET

        # Date range

        date_preset = params.get('date_preset', DateRangePresets.THIS_MONTH)

        custom_start = None

        custom_end = None

        if date_preset == DateRangePresets.CUSTOM:

            try:

                custom_start = datetime.strptime(params.get('date_from', ''), '%Y-%m-%d').date()

                custom_end = datetime.strptime(params.get('date_to', ''), '%Y-%m-%d').date()

            except ValueError:

                date_preset = DateRangePresets.THIS_MONTH

        start_date, end_date = DateRangePresets.get_date_range(date_preset, custom_start, custom_end)

        # Parsear listas (pueden venir múltiples valores)

        def parse_list(key):

            values = params.getlist(key)

            if not values:

                value = params.get(key)

                if value:

                    values = [v.strip() for v in value.split(',') if v.strip()]

            return [int(v) for v in values if v.isdigit()] if values else []

        def parse_string_list(key):

            values = params.getlist(key)

            if not values:

                value = params.get(key)

                if value:

                    values = [v.strip() for v in value.split(',') if v.strip()]

            return values

        return {

            'date_preset': date_preset,

            'date_from': start_date,

            'date_to': end_date,

            'insurers': parse_list('insurer'),

            'brokers': parse_list('broker'),

            'policy_types': parse_list('policy_type'),

            'claim_types': parse_list('claim_type'),

            'policy_states': parse_string_list('policy_state'),

            'invoice_states': parse_string_list('invoice_state'),

            'claim_states': parse_string_list('claim_state'),

            'search_query': params.get('q', '').strip(),

        }

    @classmethod
    def get_filtered_stats(cls, filters: Dict[str, Any]) -> Dict[str, Any]:

        """

        Obtiene estadísticas filtradas según los parámetros proporcionados.

        """

        from app.models import Poliza, Factura, Siniestro, Alerta

        date_from = filters.get('date_from')

        date_to = filters.get('date_to')

        # Construir querysets base con filtros

        policies_qs = cls._build_policy_queryset(filters)

        invoices_qs = cls._build_invoice_queryset(filters)

        claims_qs = cls._build_claim_queryset(filters)

        # Estadísticas de pólizas

        policy_stats = policies_qs.aggregate(

            total=Count('id'),

            active=Count('id', filter=Q(estado='vigente')),

            expiring=Count('id', filter=Q(estado='por_vencer')),

            expired=Count('id', filter=Q(estado='vencida')),

            total_insured=Coalesce(Sum('suma_asegurada'), Value(Decimal('0'))),

        )

        # Estadísticas de facturas

        invoice_stats = invoices_qs.aggregate(

            total=Count('id'),

            pending=Count('id', filter=Q(estado__in=['pendiente', 'parcial'])),

            paid=Count('id', filter=Q(estado='pagada')),

            overdue=Count('id', filter=Q(estado='vencida')),

            total_amount=Coalesce(Sum('monto_total'), Value(Decimal('0'))),

            paid_amount=Coalesce(Sum('monto_total', filter=Q(estado='pagada')), Value(Decimal('0'))),

            pending_amount=Coalesce(Sum('monto_total', filter=Q(estado__in=['pendiente', 'parcial', 'vencida'])), Value(Decimal('0'))),

        )

        # Estadísticas de siniestros

        claim_stats = claims_qs.aggregate(

            total=Count('id'),

            active=Count('id', filter=~Q(estado__in=['cerrado', 'rechazado'])),

            pending_docs=Count('id', filter=Q(estado='documentacion_pendiente')),

            in_evaluation=Count('id', filter=Q(estado='en_evaluacion')),

            approved=Count('id', filter=Q(estado='aprobado')),

            total_estimated=Coalesce(Sum('monto_estimado'), Value(Decimal('0'))),

            total_indemnified=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0'))),

        )

        # Alertas activas (no filtradas por fecha, son globales)

        alert_stats = {

            'pending': Alerta.objects.filter(estado='pendiente').count(),

            'sent': Alerta.objects.filter(estado='enviada').count(),

            'total_active': Alerta.objects.filter(estado__in=['pendiente', 'enviada']).count(),

        }

        # Calcular KPIs

        collection_rate = 0

        if invoice_stats['total_amount'] > 0:

            collection_rate = round(

                (invoice_stats['paid_amount'] / invoice_stats['total_amount']) * 100, 1

            )

        loss_ratio = 0

        if invoice_stats['paid_amount'] > 0:

            loss_ratio = round(

                (claim_stats['total_indemnified'] / invoice_stats['paid_amount']) * 100, 1

            )

        return {

            'filters': {

                'date_preset': filters.get('date_preset'),

                'date_from': date_from.isoformat() if date_from else None,

                'date_to': date_to.isoformat() if date_to else None,

                'date_label': cls._get_date_range_label(filters),

            },

            'policies': {

                'total': policy_stats['total'],

                'active': policy_stats['active'],

                'expiring': policy_stats['expiring'],

                'expired': policy_stats['expired'],

                'total_insured': float(policy_stats['total_insured']),

            },

            'invoices': {

                'total': invoice_stats['total'],

                'pending': invoice_stats['pending'],

                'paid': invoice_stats['paid'],

                'overdue': invoice_stats['overdue'],

                'total_amount': float(invoice_stats['total_amount']),

                'paid_amount': float(invoice_stats['paid_amount']),

                'pending_amount': float(invoice_stats['pending_amount']),

                'collection_rate': collection_rate,

            },

            'claims': {

                'total': claim_stats['total'],

                'active': claim_stats['active'],

                'pending_docs': claim_stats['pending_docs'],

                'in_evaluation': claim_stats['in_evaluation'],

                'approved': claim_stats['approved'],

                'total_estimated': float(claim_stats['total_estimated']),

                'total_indemnified': float(claim_stats['total_indemnified']),

            },

            'alerts': alert_stats,

            'kpis': {

                'collection_rate': collection_rate,

                'loss_ratio': loss_ratio,

            }

        }

    @classmethod
    def get_chart_data(cls, filters: Dict[str, Any]) -> Dict[str, Any]:

        """

        Obtiene datos para gráficos filtrados.

        """

        from app.models import Poliza, Factura, Siniestro

        date_from = filters.get('date_from')

        date_to = filters.get('date_to')

        # Determinar granularidad basada en el rango de fechas

        days_diff = (date_to - date_from).days

        if days_diff <= 31:

            trunc_func = TruncDay

            date_format = '%d/%m'

        elif days_diff <= 180:

            trunc_func = TruncWeek

            date_format = 'Sem %W'

        else:

            trunc_func = TruncMonth

            date_format = '%b %Y'

        # Construir querysets

        invoices_qs = cls._build_invoice_queryset(filters)

        claims_qs = cls._build_claim_queryset(filters)

        # Facturación por período

        invoicing_by_period = list(

            invoices_qs

            .annotate(period=trunc_func('fecha_emision'))

            .values('period')

            .annotate(

                amount=Coalesce(Sum('monto_total'), Value(Decimal('0'))),

                count=Count('id'),

                paid=Coalesce(Sum('monto_total', filter=Q(estado='pagada')), Value(Decimal('0')))

            )

            .order_by('period')

        )

        # Siniestros por período

        claims_by_period = list(

            claims_qs

            .annotate(period=trunc_func('fecha_siniestro'))

            .values('period')

            .annotate(

                count=Count('id'),

                amount=Coalesce(Sum('monto_estimado'), Value(Decimal('0')))

            )

            .order_by('period')

        )

        # Formatear datos para Chart.js

        invoicing_labels = [

            item['period'].strftime(date_format) if item['period'] else ''

            for item in invoicing_by_period

        ]

        claims_labels = [

            item['period'].strftime(date_format) if item['period'] else ''

            for item in claims_by_period

        ]

        # Distribución por compañía

        policies_qs = cls._build_policy_queryset(filters)

        by_insurer = list(

            policies_qs

            .values('compania_aseguradora__nombre')

            .annotate(

                count=Count('id'),

                total=Coalesce(Sum('suma_asegurada'), Value(Decimal('0')))

            )

            .order_by('-count')[:8]

        )

        # Distribución por tipo de póliza

        by_policy_type = list(

            policies_qs

            .values('tipo_poliza__nombre')

            .annotate(count=Count('id'))

            .order_by('-count')

        )

        # Distribución por estado de póliza

        by_policy_state = list(

            policies_qs

            .values('estado')

            .annotate(count=Count('id'))

            .order_by('estado')

        )

        # Distribución por tipo de siniestro (sin límite para mostrar todos)

        by_claim_type = list(

            claims_qs

            .values('tipo_siniestro__nombre')

            .annotate(

                count=Count('id'),

                amount=Coalesce(Sum('monto_estimado'), Value(Decimal('0')))

            )

            .order_by('-count')

        )

        return {

            'invoicing_trend': {

                'labels': invoicing_labels,

                'amounts': [float(item['amount']) for item in invoicing_by_period],

                'counts': [item['count'] for item in invoicing_by_period],

                'paid': [float(item['paid']) for item in invoicing_by_period],

            },

            'claims_trend': {

                'labels': claims_labels,

                'counts': [item['count'] for item in claims_by_period],

                'amounts': [float(item['amount']) for item in claims_by_period],

            },

            'by_insurer': {

                'labels': [item['compania_aseguradora__nombre'] or 'Sin compañía' for item in by_insurer],

                'counts': [item['count'] for item in by_insurer],

                'totals': [float(item['total']) for item in by_insurer],

            },

            'by_policy_type': {

                'labels': [item['tipo_poliza__nombre'] or 'Sin tipo' for item in by_policy_type],

                'counts': [item['count'] for item in by_policy_type],

            },

            'by_policy_state': {

                'labels': [cls._get_state_label(item['estado'], 'policy') for item in by_policy_state],

                'counts': [item['count'] for item in by_policy_state],

                'colors': [cls._get_state_color(item['estado'], 'policy') for item in by_policy_state],

            },

            'by_claim_type': {

                'labels': [item['tipo_siniestro__nombre'] or 'Sin tipo' for item in by_claim_type],

                'counts': [item['count'] for item in by_claim_type],

                'amounts': [float(item['amount']) for item in by_claim_type],

            },

        }

    @classmethod
    def get_lists_data(cls, filters: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:

        """

        Obtiene listas de registros filtrados para mostrar en el dashboard.

        """

        from app.models import Poliza, Factura, Siniestro

        today = timezone.now().date()

        # Pólizas por vencer (próximos 30 días)

        expiring_policies = list(

            Poliza.objects.filter(

                fecha_fin__gte=today,

                fecha_fin__lte=today + timedelta(days=30),

                estado__in=['vigente', 'por_vencer']

            )

            .select_related('compania_aseguradora', 'tipo_poliza')

            .order_by('fecha_fin')[:limit]

            .values(

                'id', 'numero_poliza', 'fecha_fin',

                'compania_aseguradora__nombre', 'tipo_poliza__nombre',

                'suma_asegurada'

            )

        )

        for p in expiring_policies:

            p['days_to_expire'] = (p['fecha_fin'] - today).days

        # Facturas pendientes

        pending_invoices = list(

            Factura.objects.filter(estado__in=['pendiente', 'parcial', 'vencida'])

            .select_related('poliza', 'poliza__compania_aseguradora')

            .order_by('fecha_vencimiento')[:limit]

            .values(

                'id', 'numero_factura', 'fecha_emision', 'fecha_vencimiento',

                'monto_total', 'estado',

                'poliza__numero_poliza', 'poliza__compania_aseguradora__nombre'

            )

        )

        for f in pending_invoices:

            f['is_overdue'] = f['fecha_vencimiento'] < today

            f['monto_total'] = float(f['monto_total'])

        # Siniestros activos

        active_claims = list(

            Siniestro.objects.exclude(estado__in=['cerrado', 'rechazado'])

            .select_related('poliza', 'tipo_siniestro')

            .order_by('-fecha_siniestro')[:limit]

            .values(

                'id', 'numero_siniestro', 'fecha_siniestro', 'estado',

                'bien_nombre', 'monto_estimado',

                'poliza__numero_poliza', 'tipo_siniestro__nombre'

            )

        )

        for c in active_claims:

            c['monto_estimado'] = float(c['monto_estimado']) if c['monto_estimado'] else 0

            c['state_label'] = cls._get_state_label(c['estado'], 'claim')

            c['state_color'] = cls._get_state_color(c['estado'], 'claim')

        return {

            'expiring_policies': expiring_policies,

            'pending_invoices': pending_invoices,

            'active_claims': active_claims,

        }

    @classmethod
    def export_filtered_data(cls, filters: Dict[str, Any], export_type: str = 'summary') -> Dict[str, Any]:

        """

        Prepara datos para exportación basados en los filtros.

        """

        stats = cls.get_filtered_stats(filters)

        charts = cls.get_chart_data(filters)

        lists = cls.get_lists_data(filters, limit=100)

        return {

            'generated_at': timezone.now().isoformat(),

            'filters': filters,

            'statistics': stats,

            'charts': charts,

            'lists': lists,

        }

    # =========================================================================

    # Métodos privados de ayuda

    # =========================================================================

    @classmethod
    def _build_policy_queryset(cls, filters: Dict[str, Any]):

        """Construye el queryset de pólizas con los filtros aplicados."""

        from app.models import Poliza

        qs = Poliza.objects.all()

        date_from = filters.get('date_from')

        date_to = filters.get('date_to')

        if date_from and date_to:

            # Pólizas creadas en el rango o vigentes durante el rango

            qs = qs.filter(

                Q(fecha_creacion__date__gte=date_from, fecha_creacion__date__lte=date_to) |

                Q(fecha_inicio__lte=date_to, fecha_fin__gte=date_from)

            )

        if filters.get('insurers'):

            qs = qs.filter(compania_aseguradora_id__in=filters['insurers'])

        if filters.get('brokers'):

            qs = qs.filter(corredor_seguros_id__in=filters['brokers'])

        if filters.get('policy_types'):

            qs = qs.filter(tipo_poliza_id__in=filters['policy_types'])

        if filters.get('policy_states'):

            qs = qs.filter(estado__in=filters['policy_states'])

        if filters.get('search_query'):

            q = filters['search_query']

            qs = qs.filter(

                Q(numero_poliza__icontains=q) |

                Q(compania_aseguradora__nombre__icontains=q) |

                Q(corredor_seguros__nombre__icontains=q) |

                Q(coberturas__icontains=q)

            )

        return qs.distinct()

    @classmethod
    def _build_invoice_queryset(cls, filters: Dict[str, Any]):

        """Construye el queryset de facturas con los filtros aplicados."""

        from app.models import Factura

        qs = Factura.objects.all()

        date_from = filters.get('date_from')

        date_to = filters.get('date_to')

        if date_from and date_to:

            qs = qs.filter(fecha_emision__gte=date_from, fecha_emision__lte=date_to)

        if filters.get('insurers'):

            qs = qs.filter(poliza__compania_aseguradora_id__in=filters['insurers'])

        if filters.get('invoice_states'):

            qs = qs.filter(estado__in=filters['invoice_states'])

        if filters.get('search_query'):

            q = filters['search_query']

            qs = qs.filter(

                Q(numero_factura__icontains=q) |

                Q(poliza__numero_poliza__icontains=q)

            )

        return qs.distinct()

    @classmethod
    def _build_claim_queryset(cls, filters: Dict[str, Any]):

        """Construye el queryset de siniestros con los filtros aplicados."""

        from app.models import Siniestro

        qs = Siniestro.objects.all()

        date_from = filters.get('date_from')

        date_to = filters.get('date_to')

        if date_from and date_to:

            qs = qs.filter(

                fecha_siniestro__date__gte=date_from,

                fecha_siniestro__date__lte=date_to

            )

        if filters.get('insurers'):

            qs = qs.filter(poliza__compania_aseguradora_id__in=filters['insurers'])

        if filters.get('claim_types'):

            qs = qs.filter(tipo_siniestro_id__in=filters['claim_types'])

        if filters.get('claim_states'):

            qs = qs.filter(estado__in=filters['claim_states'])

        if filters.get('search_query'):

            q = filters['search_query']

            qs = qs.filter(

                Q(numero_siniestro__icontains=q) |

                Q(bien_nombre__icontains=q) |

                Q(poliza__numero_poliza__icontains=q)

            )

        return qs.distinct()

    @classmethod
    def _get_date_range_label(cls, filters: Dict[str, Any]) -> str:

        """Genera una etiqueta legible para el rango de fechas."""

        preset = filters.get('date_preset')

        if preset and preset in DateRangePresets.CHOICES:

            return DateRangePresets.CHOICES[preset]

        date_from = filters.get('date_from')

        date_to = filters.get('date_to')

        if date_from and date_to:

            return f"{date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"

        return 'Período no definido'

    @classmethod
    def _get_state_label(cls, state: str, entity_type: str) -> str:

        """Obtiene la etiqueta de un estado."""

        from app.models import Poliza, Factura, Siniestro

        if entity_type == 'policy':

            choices = dict(Poliza.ESTADO_CHOICES)

        elif entity_type == 'invoice':

            choices = dict(Factura.ESTADO_CHOICES)

        elif entity_type == 'claim':

            choices = dict(Siniestro.ESTADO_CHOICES)

        else:

            return state.replace('_', ' ').title()

        return choices.get(state, state.replace('_', ' ').title())

    @classmethod
    def _get_state_color(cls, state: str, entity_type: str) -> str:

        """Obtiene el color para un estado."""

        colors = {

            # Pólizas

            'vigente': '#10B981',      # Emerald

            'por_vencer': '#F59E0B',   # Amber

            'vencida': '#EF4444',      # Red

            'cancelada': '#6B7280',    # Gray

            # Facturas

            'pendiente': '#F59E0B',    # Amber

            'pagada': '#10B981',       # Emerald

            'parcial': '#3B82F6',      # Blue

            # Siniestros

            'registrado': '#3B82F6',           # Blue

            'documentacion_pendiente': '#F59E0B',  # Amber

            'enviado_aseguradora': '#8B5CF6',  # Purple

            'en_evaluacion': '#06B6D4',        # Cyan

            'aprobado': '#10B981',             # Emerald

            'rechazado': '#EF4444',            # Red

            'liquidado': '#059669',            # Emerald dark

            'cerrado': '#6B7280',              # Gray

        }

        return colors.get(state, '#6B7280')
