from django.db.models import Sum, Count, Avg, Q, F

from django.db.models.functions import TruncMonth, TruncWeek, ExtractMonth

from django.utils import timezone

from datetime import timedelta

from decimal import Decimal





class EstadisticasService:

    

    @staticmethod

    def get_dashboard_stats():

        from app.models import Poliza, Factura, Siniestro, Alerta

        

        hoy = timezone.now().date()

        

        return {

            'polizas': {

                'vigentes': Poliza.objects.filter(estado='vigente').count(),

                'por_vencer': Poliza.objects.filter(estado='por_vencer').count(),

                'vencidas': Poliza.objects.filter(estado='vencida').count(),

                'total': Poliza.objects.count(),

            },

            'facturas': {

                'pendientes': Factura.objects.filter(estado__in=['pendiente', 'parcial']).count(),

                'vencidas': Factura.objects.filter(estado='vencida').count(),

                'pagadas': Factura.objects.filter(estado='pagada').count(),

                'monto_pendiente': Factura.objects.filter(

                    estado__in=['pendiente', 'parcial']

                ).aggregate(total=Sum('monto_total'))['total'] or Decimal('0'),

            },

            'siniestros': {

                'activos': Siniestro.objects.exclude(estado__in=['cerrado', 'rechazado']).count(),

                'pendientes_doc': Siniestro.objects.filter(estado='documentacion_pendiente').count(),

                'en_evaluacion': Siniestro.objects.filter(estado='en_evaluacion').count(),

                'total': Siniestro.objects.count(),

            },

            'alertas': {

                'pendientes': Alerta.objects.filter(estado='pendiente').count(),

                'enviadas': Alerta.objects.filter(estado='enviada').count(),

                'total_activas': Alerta.objects.filter(estado__in=['pendiente', 'enviada']).count(),

            }

        }

    

    @staticmethod

    def get_polizas_por_estado():

        from app.models import Poliza

        

        estados = Poliza.objects.values('estado').annotate(

            cantidad=Count('id'),

            suma_total=Sum('suma_asegurada')

        ).order_by('estado')

        

        return list(estados)

    

    @staticmethod

    def get_polizas_por_compania():

        from app.models import Poliza

        

        return list(Poliza.objects.values(

            'compania_aseguradora__nombre'

        ).annotate(

            cantidad=Count('id'),

            suma_total=Sum('suma_asegurada')

        ).order_by('-cantidad')[:10])

    

    @staticmethod

    def get_polizas_por_tipo():

        from app.models import Poliza

        

        return list(Poliza.objects.values(

            'tipo_poliza__nombre'

        ).annotate(

            cantidad=Count('id'),

            suma_total=Sum('suma_asegurada')

        ).order_by('-cantidad'))

    

    @staticmethod

    def get_siniestros_por_tipo():

        from app.models import Siniestro

        

        return list(Siniestro.objects.values(

            'tipo_siniestro__nombre'

        ).annotate(

            cantidad=Count('id'),

            monto_total=Sum('monto_estimado'),

            monto_indemnizado=Sum('monto_indemnizado')

        ).order_by('-cantidad'))

    

    @staticmethod

    def get_siniestros_por_mes(meses=12):

        from app.models import Siniestro

        

        fecha_inicio = timezone.now() - timedelta(days=meses * 30)

        

        return list(Siniestro.objects.filter(

            fecha_siniestro__gte=fecha_inicio

        ).annotate(

            mes=TruncMonth('fecha_siniestro')

        ).values('mes').annotate(

            cantidad=Count('id'),

            monto_total=Sum('monto_estimado')

        ).order_by('mes'))

    

    @staticmethod

    def get_facturas_por_mes(meses=12):

        from app.models import Factura

        

        fecha_inicio = timezone.now() - timedelta(days=meses * 30)

        

        return list(Factura.objects.filter(

            fecha_emision__gte=fecha_inicio

        ).annotate(

            mes=TruncMonth('fecha_emision')

        ).values('mes').annotate(

            cantidad=Count('id'),

            monto_total=Sum('monto_total'),

            monto_pagado=Sum('pagos__monto', filter=Q(pagos__estado='aprobado'))

        ).order_by('mes'))

    

    @staticmethod

    def get_polizas_proximas_vencer(dias=30, limit=10):

        from app.models import Poliza

        

        hoy = timezone.now().date()

        fecha_limite = hoy + timedelta(days=dias)

        

        return Poliza.objects.filter(

            fecha_fin__gte=hoy,

            fecha_fin__lte=fecha_limite,

            estado__in=['vigente', 'por_vencer']

        ).select_related(

            'compania_aseguradora', 'tipo_poliza'

        ).order_by('fecha_fin')[:limit]

    

    @staticmethod

    def get_facturas_pendientes(limit=10):

        from app.models import Factura

        

        return Factura.objects.filter(

            estado__in=['pendiente', 'parcial', 'vencida']

        ).select_related(

            'poliza', 'poliza__compania_aseguradora'

        ).order_by('fecha_vencimiento')[:limit]

    

    @staticmethod

    def get_siniestros_recientes(limit=10):

        from app.models import Siniestro

        

        return Siniestro.objects.exclude(

            estado__in=['cerrado', 'rechazado']

        ).select_related(

            'poliza', 'tipo_siniestro', 'poliza__compania_aseguradora'

        ).order_by('-fecha_siniestro')[:limit]

    

    @staticmethod

    def get_kpis():

        from app.models import Poliza, Factura, Siniestro

        

        hoy = timezone.now().date()

        hace_30_dias = hoy - timedelta(days=30)

        hace_365_dias = hoy - timedelta(days=365)

        

        polizas_vigentes = Poliza.objects.filter(estado='vigente')

        suma_total_asegurada = polizas_vigentes.aggregate(

            total=Sum('suma_asegurada')

        )['total'] or Decimal('0')

        

        facturas_anio = Factura.objects.filter(fecha_emision__gte=hace_365_dias)

        total_facturado = facturas_anio.aggregate(total=Sum('monto_total'))['total'] or Decimal('0')

        

        siniestros_anio = Siniestro.objects.filter(fecha_siniestro__date__gte=hace_365_dias)

        total_siniestros = siniestros_anio.aggregate(total=Sum('monto_estimado'))['total'] or Decimal('0')

        total_indemnizado = siniestros_anio.aggregate(total=Sum('monto_indemnizado'))['total'] or Decimal('0')

        

        tasa_siniestralidad = (total_indemnizado / total_facturado * 100) if total_facturado > 0 else Decimal('0')

        

        tiempo_promedio_resolucion = siniestros_anio.filter(

            fecha_liquidacion__isnull=False

        ).annotate(

            dias_resolucion=F('fecha_liquidacion') - F('fecha_registro')

        ).aggregate(promedio=Avg('dias_resolucion'))['promedio']

        

        return {

            'suma_total_asegurada': suma_total_asegurada,

            'total_facturado_anio': total_facturado,

            'total_siniestros_anio': total_siniestros,

            'total_indemnizado_anio': total_indemnizado,

            'tasa_siniestralidad': round(tasa_siniestralidad, 2),

            'tiempo_promedio_resolucion': tiempo_promedio_resolucion.days if tiempo_promedio_resolucion else 0,

            'polizas_activas': polizas_vigentes.count(),

        }

