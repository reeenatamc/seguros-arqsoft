from django.db.models import Sum, Count, Avg, Q

from django.utils import timezone

from datetime import timedelta

from decimal import Decimal

import json


class ReportesService:

    @staticmethod
    def generar_reporte_polizas(filtros=None):

        from app.models import Poliza

        queryset = Poliza.objects.select_related(

            'compania_aseguradora', 'corredor_seguros', 'tipo_poliza'

        )

        if filtros:

            if filtros.get('estado'):

                queryset = queryset.filter(estado=filtros['estado'])

            if filtros.get('compania'):

                queryset = queryset.filter(compania_aseguradora_id=filtros['compania'])

            if filtros.get('tipo'):

                queryset = queryset.filter(tipo_poliza_id=filtros['tipo'])

            if filtros.get('fecha_desde'):

                queryset = queryset.filter(fecha_inicio__gte=filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):

                queryset = queryset.filter(fecha_fin__lte=filtros['fecha_hasta'])

        totales = queryset.aggregate(

            cantidad=Count('id'),

            suma_total=Sum('suma_asegurada'),

            vigentes=Count('id', filter=Q(estado='vigente')),

            por_vencer=Count('id', filter=Q(estado='por_vencer')),

            vencidas=Count('id', filter=Q(estado='vencida')),

        )

        por_compania = list(queryset.values(

            'compania_aseguradora__nombre'

        ).annotate(

            cantidad=Count('id'),

            suma=Sum('suma_asegurada')

        ).order_by('-suma'))

        por_tipo = list(queryset.values(

            'tipo_poliza__nombre'

        ).annotate(

            cantidad=Count('id'),

            suma=Sum('suma_asegurada')

        ).order_by('-cantidad'))

        return {

            'queryset': queryset,

            'totales': totales,

            'por_compania': por_compania,

            'por_tipo': por_tipo,

            'fecha_generacion': timezone.now()

        }

    @staticmethod
    def generar_reporte_facturas(filtros=None):

        from app.models import Factura

        queryset = Factura.objects.select_related(

            'poliza', 'poliza__compania_aseguradora'

        )

        if filtros:

            if filtros.get('estado'):

                queryset = queryset.filter(estado=filtros['estado'])

            if filtros.get('fecha_desde'):

                queryset = queryset.filter(fecha_emision__gte=filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):

                queryset = queryset.filter(fecha_emision__lte=filtros['fecha_hasta'])

        totales = queryset.aggregate(

            cantidad=Count('id'),

            total_facturado=Sum('monto_total'),

            total_pendiente=Sum('monto_total', filter=Q(estado__in=['pendiente', 'parcial'])),

            total_vencido=Sum('monto_total', filter=Q(estado='vencida')),

            pendientes=Count('id', filter=Q(estado='pendiente')),

            pagadas=Count('id', filter=Q(estado='pagada')),

            vencidas=Count('id', filter=Q(estado='vencida')),

        )

        return {

            'queryset': queryset,

            'totales': totales,

            'fecha_generacion': timezone.now()

        }

    @staticmethod
    def generar_reporte_siniestros(filtros=None):

        from app.models import Siniestro

        queryset = Siniestro.objects.select_related(

            'poliza', 'tipo_siniestro', 'poliza__compania_aseguradora'

        )

        if filtros:

            if filtros.get('estado'):

                queryset = queryset.filter(estado=filtros['estado'])

            if filtros.get('tipo'):

                queryset = queryset.filter(tipo_siniestro_id=filtros['tipo'])

            if filtros.get('fecha_desde'):

                queryset = queryset.filter(fecha_siniestro__date__gte=filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):

                queryset = queryset.filter(fecha_siniestro__date__lte=filtros['fecha_hasta'])

        totales = queryset.aggregate(

            cantidad=Count('id'),

            monto_estimado=Sum('monto_estimado'),

            monto_indemnizado=Sum('monto_indemnizado'),

            activos=Count('id', filter=~Q(estado__in=['cerrado', 'rechazado'])),

            cerrados=Count('id', filter=Q(estado='cerrado')),

            rechazados=Count('id', filter=Q(estado='rechazado')),

        )

        por_tipo = list(queryset.values(

            'tipo_siniestro__nombre'

        ).annotate(

            cantidad=Count('id'),

            monto=Sum('monto_estimado')

        ).order_by('-cantidad'))

        por_estado = list(queryset.values('estado').annotate(

            cantidad=Count('id'),

            monto=Sum('monto_estimado')

        ).order_by('-cantidad'))

        return {

            'queryset': queryset,

            'totales': totales,

            'por_tipo': por_tipo,

            'por_estado': por_estado,

            'fecha_generacion': timezone.now()

        }

    @staticmethod
    def get_datos_graficos_polizas():

        from app.models import Poliza

        estados = Poliza.objects.values('estado').annotate(

            count=Count('id')

        )

        labels = []

        data = []

        colors = {

            'vigente': '#48BB78',

            'por_vencer': '#ECC94B',

            'vencida': '#F56565',

            'cancelada': '#A0AEC0'

        }

        background_colors = []

        for item in estados:

            labels.append(item['estado'].replace('_', ' ').title())

            data.append(item['count'])

            background_colors.append(colors.get(item['estado'], '#CBD5E0'))

        return {

            'labels': json.dumps(labels),

            'data': json.dumps(data),

            'colors': json.dumps(background_colors)

        }

    @staticmethod
    def get_datos_graficos_facturas():

        from app.models import Factura

        estados = Factura.objects.values('estado').annotate(

            count=Count('id'),

            total=Sum('monto_total')

        )

        labels = []

        data = []

        colors = {

            'pendiente': '#ECC94B',

            'pagada': '#48BB78',

            'parcial': '#4299E1',

            'vencida': '#F56565'

        }

        background_colors = []

        for item in estados:

            labels.append(item['estado'].title())

            data.append(item['count'])

            background_colors.append(colors.get(item['estado'], '#CBD5E0'))

        return {

            'labels': json.dumps(labels),

            'data': json.dumps(data),

            'colors': json.dumps(background_colors)

        }

    @staticmethod
    def get_datos_graficos_siniestros_mensual():

        from app.models import Siniestro

        from django.db.models.functions import TruncMonth

        hace_12_meses = timezone.now() - timedelta(days=365)

        por_mes = Siniestro.objects.filter(

            fecha_siniestro__gte=hace_12_meses

        ).annotate(

            mes=TruncMonth('fecha_siniestro')

        ).values('mes').annotate(

            count=Count('id'),

            monto=Sum('monto_estimado')

        ).order_by('mes')

        labels = []

        data_count = []

        data_monto = []

        meses_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',

                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        for item in por_mes:

            labels.append(f"{meses_es[item['mes'].month - 1]} {item['mes'].year}")

            data_count.append(item['count'])

            data_monto.append(float(item['monto'] or 0))

        return {

            'labels': json.dumps(labels),

            'data_count': json.dumps(data_count),

            'data_monto': json.dumps(data_monto)

        }

    @staticmethod
    def get_datos_graficos_siniestros_por_tipo():

        from app.models import Siniestro

        por_tipo = Siniestro.objects.values(

            'tipo_siniestro__nombre'

        ).annotate(

            count=Count('id'),

            monto=Sum('monto_estimado')

        ).order_by('-count')[:8]

        labels = []

        data = []

        montos = []

        colors = ['#EF4444', '#F97316', '#F59E0B', '#EAB308', '#84CC16', '#22C55E', '#14B8A6', '#06B6D4']

        for i, item in enumerate(por_tipo):

            nombre = item['tipo_siniestro__nombre'] or 'Sin tipo'

            labels.append(nombre.title() if nombre else 'Sin tipo')

            data.append(item['count'])

            montos.append(float(item['monto'] or 0))

        return {

            'labels': json.dumps(labels),

            'data': json.dumps(data),

            'montos': json.dumps(montos),

            'colors': json.dumps(colors[:len(data)])

        }

    @staticmethod
    def get_datos_graficos_facturacion_mensual():

        from app.models import Factura

        from django.db.models.functions import TruncMonth

        hace_12_meses = timezone.now().date() - timedelta(days=365)

        por_mes = Factura.objects.filter(

            fecha_emision__gte=hace_12_meses

        ).annotate(

            mes=TruncMonth('fecha_emision')

        ).values('mes').annotate(

            facturado=Sum('monto_total'),

            cantidad=Count('id')

        ).order_by('mes')

        labels = []

        data_facturado = []

        data_cantidad = []

        meses_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',

                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        for item in por_mes:

            labels.append(f"{meses_es[item['mes'].month - 1]}")

            data_facturado.append(float(item['facturado'] or 0))

            data_cantidad.append(item['cantidad'])

        return {

            'labels': json.dumps(labels),

            'data_facturado': json.dumps(data_facturado),

            'data_cantidad': json.dumps(data_cantidad)

        }

    @staticmethod
    def get_datos_graficos_polizas_por_tipo():

        from app.models import Poliza

        por_tipo = Poliza.objects.values(

            'tipo_poliza__nombre'

        ).annotate(

            count=Count('id'),

            suma=Sum('suma_asegurada')

        ).order_by('-count')

        labels = []

        data = []

        sumas = []

        colors = ['#3B82F6', '#8B5CF6', '#EC4899', '#F43F5E', '#F97316', '#84CC16', '#14B8A6', '#06B6D4']

        for item in por_tipo:

            nombre = item['tipo_poliza__nombre'] or 'Sin tipo'

            labels.append(nombre)

            data.append(item['count'])

            sumas.append(float(item['suma'] or 0))

        return {

            'labels': json.dumps(labels),

            'data': json.dumps(data),

            'sumas': json.dumps(sumas),

            'colors': json.dumps(colors[:len(data)])

        }

    @staticmethod
    def get_datos_graficos_comparativo():

        from app.models import Poliza, Factura, Siniestro

        from django.db.models.functions import TruncMonth

        hace_6_meses = timezone.now() - timedelta(days=180)

        meses_es = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',

                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        polizas_mes = Poliza.objects.filter(

            fecha_creacion__gte=hace_6_meses

        ).annotate(

            mes=TruncMonth('fecha_creacion')

        ).values('mes').annotate(count=Count('id')).order_by('mes')

        facturas_mes = Factura.objects.filter(

            fecha_emision__gte=hace_6_meses.date()

        ).annotate(

            mes=TruncMonth('fecha_emision')

        ).values('mes').annotate(count=Count('id')).order_by('mes')

        siniestros_mes = Siniestro.objects.filter(

            fecha_siniestro__gte=hace_6_meses

        ).annotate(

            mes=TruncMonth('fecha_siniestro')

        ).values('mes').annotate(count=Count('id')).order_by('mes')

        # Normalizar todas las fechas a date para poder compararlas

        meses = set()

        for item in list(polizas_mes) + list(facturas_mes) + list(siniestros_mes):

            mes = item['mes']

            if hasattr(mes, 'date'):

                mes = mes.date()

            meses.add(mes)

        meses = sorted(list(meses))

        labels = [f"{meses_es[m.month - 1]}" for m in meses]

        # Crear diccionarios normalizando las fechas

        def normalizar_mes(mes):

            return mes.date() if hasattr(mes, 'date') else mes

        polizas_dict = {normalizar_mes(item['mes']): item['count'] for item in polizas_mes}

        facturas_dict = {normalizar_mes(item['mes']): item['count'] for item in facturas_mes}

        siniestros_dict = {normalizar_mes(item['mes']): item['count'] for item in siniestros_mes}

        data_polizas = [polizas_dict.get(m, 0) for m in meses]

        data_facturas = [facturas_dict.get(m, 0) for m in meses]

        data_siniestros = [siniestros_dict.get(m, 0) for m in meses]

        return {

            'labels': json.dumps(labels),

            'data_polizas': json.dumps(data_polizas),

            'data_facturas': json.dumps(data_facturas),

            'data_siniestros': json.dumps(data_siniestros)

        }
