"""

Servicio de Reportes Avanzados.

Gestiona la generación de reportes especializados para análisis de seguros.

"""

from decimal import Decimal

from datetime import datetime, timedelta

from collections import defaultdict

from django.db.models import Sum, Count, Avg, F, Q, Case, When, Value, DecimalField

from django.db.models.functions import TruncMonth, Coalesce

from django.utils import timezone

from app.models import (

    Siniestro, Poliza, Factura, Pago, TipoSiniestro, TipoPoliza,

    CompaniaAseguradora, ResponsableCustodio, Ramo, DetallePolizaRamo

)

class ReportesAvanzadosService:

    """Servicio para reportes especializados de seguros"""

    @classmethod
    def calcular_siniestralidad(cls, fecha_desde=None, fecha_hasta=None,

                                 compania_id=None, tipo_poliza_id=None):

        """

        Calcula el índice de siniestralidad: Siniestros pagados / Primas pagadas.

        Args:

            fecha_desde: Fecha de inicio del período

            fecha_hasta: Fecha de fin del período

            compania_id: ID de compañía para filtrar

            tipo_poliza_id: ID de tipo de póliza para filtrar

        Returns:

            dict: Datos de siniestralidad con índice, totales y detalle

        """

        # Definir período por defecto (último año)

        if not fecha_hasta:

            fecha_hasta = timezone.now().date()

        if not fecha_desde:

            fecha_desde = fecha_hasta - timedelta(days=365)

        # Filtro base para siniestros

        filtro_siniestros = Q(

            fecha_pago__isnull=False,

            fecha_pago__gte=fecha_desde,

            fecha_pago__lte=fecha_hasta,

        )

        # Filtro base para pagos de facturas

        filtro_pagos = Q(

            estado='aprobado',

            fecha_pago__gte=fecha_desde,

            fecha_pago__lte=fecha_hasta,

        )

        if compania_id:

            filtro_siniestros &= Q(poliza__compania_aseguradora_id=compania_id)

            filtro_pagos &= Q(factura__poliza__compania_aseguradora_id=compania_id)

        if tipo_poliza_id:

            filtro_siniestros &= Q(poliza__tipo_poliza_id=tipo_poliza_id)

            filtro_pagos &= Q(factura__poliza__tipo_poliza_id=tipo_poliza_id)

        # Calcular totales

        siniestros_pagados = Siniestro.objects.filter(filtro_siniestros).aggregate(

            total=Coalesce(Sum('valor_pagado'), Decimal('0.00'))

        )['total']

        primas_pagadas = Pago.objects.filter(filtro_pagos).aggregate(

            total=Coalesce(Sum('monto'), Decimal('0.00'))

        )['total']

        # Calcular índice

        if primas_pagadas and primas_pagadas > 0:

            indice_siniestralidad = (siniestros_pagados / primas_pagadas) * 100

        else:

            indice_siniestralidad = Decimal('0.00')

        # Detalle por mes

        detalle_mensual = []

        fecha_actual = fecha_desde.replace(day=1)

        while fecha_actual <= fecha_hasta:

            mes_siguiente = (fecha_actual + timedelta(days=32)).replace(day=1)

            fin_mes = mes_siguiente - timedelta(days=1)

            # Filtros del mes

            filtro_mes_sin = Q(fecha_pago__gte=fecha_actual, fecha_pago__lte=fin_mes)

            filtro_mes_pago = Q(fecha_pago__gte=fecha_actual, fecha_pago__lte=fin_mes)

            if compania_id:

                filtro_mes_sin &= Q(poliza__compania_aseguradora_id=compania_id)

                filtro_mes_pago &= Q(factura__poliza__compania_aseguradora_id=compania_id)

            siniestros_mes = Siniestro.objects.filter(

                filtro_mes_sin,

                fecha_pago__isnull=False

            ).aggregate(total=Coalesce(Sum('valor_pagado'), Decimal('0.00')))['total']

            primas_mes = Pago.objects.filter(

                filtro_mes_pago,

                estado='aprobado'

            ).aggregate(total=Coalesce(Sum('monto'), Decimal('0.00')))['total']

            indice_mes = (siniestros_mes / primas_mes * 100) if primas_mes > 0 else Decimal('0.00')

            detalle_mensual.append({

                'mes': fecha_actual.strftime('%Y-%m'),

                'mes_nombre': fecha_actual.strftime('%B %Y'),

                'siniestros_pagados': float(siniestros_mes),

                'primas_pagadas': float(primas_mes),

                'indice': float(indice_mes),

            })

            fecha_actual = mes_siguiente

        return {

            'periodo': {

                'desde': fecha_desde.isoformat(),

                'hasta': fecha_hasta.isoformat(),

            },

            'totales': {

                'siniestros_pagados': float(siniestros_pagados),

                'primas_pagadas': float(primas_pagadas),

                'indice_siniestralidad': float(indice_siniestralidad),

            },

            'interpretacion': cls._interpretar_siniestralidad(indice_siniestralidad),

            'detalle_mensual': detalle_mensual,

        }

    @staticmethod
    def _interpretar_siniestralidad(indice):

        """Interpreta el índice de siniestralidad"""

        if indice < 30:

            return {

                'nivel': 'excelente',

                'color': 'green',

                'mensaje': 'Siniestralidad muy baja. Excelente desempeño.',

            }

        elif indice < 50:

            return {

                'nivel': 'bueno',

                'color': 'blue',

                'mensaje': 'Siniestralidad dentro de rangos normales.',

            }

        elif indice < 70:

            return {

                'nivel': 'moderado',

                'color': 'yellow',

                'mensaje': 'Siniestralidad moderada. Requiere monitoreo.',

            }

        elif indice < 100:

            return {

                'nivel': 'alto',

                'color': 'orange',

                'mensaje': 'Siniestralidad alta. Revisar coberturas y primas.',

            }

        else:

            return {

                'nivel': 'critico',

                'color': 'red',

                'mensaje': 'CRÍTICO: Los siniestros superan las primas pagadas.',

            }

    @classmethod
    def reporte_gasto_por_ramos(cls, fecha_desde=None, fecha_hasta=None,

                                 poliza_id=None):

        """

        Genera un reporte de gastos agrupado por ramo.

        Args:

            fecha_desde: Fecha de inicio

            fecha_hasta: Fecha de fin

            poliza_id: ID de póliza específica (opcional)

        Returns:

            dict: Reporte con totales y detalle por ramo

        """

        if not fecha_hasta:

            fecha_hasta = timezone.now().date()

        if not fecha_desde:

            fecha_desde = fecha_hasta - timedelta(days=365)

        # Filtro base

        filtro = Q(

            poliza__fecha_inicio__lte=fecha_hasta,

            poliza__fecha_fin__gte=fecha_desde,

        )

        if poliza_id:

            filtro &= Q(poliza_id=poliza_id)

        # Agregar datos por ramo

        datos_ramo = DetallePolizaRamo.objects.filter(filtro).values(

            'ramo__codigo',

            'ramo__nombre',

        ).annotate(

            suma_asegurada=Sum('suma_asegurada'),

            total_prima=Sum('total_prima'),

            total_contribuciones=Sum(

                F('contribucion_superintendencia') +

                F('seguro_campesino') +

                F('emision')

            ),

            total_iva=Sum('iva'),

            total_retenciones=Sum(F('retencion_prima') + F('retencion_iva')),

            total_facturado=Sum('total_facturado'),

            valor_por_pagar=Sum('valor_por_pagar'),

            cantidad_polizas=Count('poliza', distinct=True),

        ).order_by('-total_prima')

        # Calcular totales generales

        totales = {

            'suma_asegurada': Decimal('0.00'),

            'total_prima': Decimal('0.00'),

            'total_contribuciones': Decimal('0.00'),

            'total_iva': Decimal('0.00'),

            'total_retenciones': Decimal('0.00'),

            'total_facturado': Decimal('0.00'),

            'valor_por_pagar': Decimal('0.00'),

        }

        ramos = []

        for dato in datos_ramo:

            ramo = {

                'codigo': dato['ramo__codigo'],

                'nombre': dato['ramo__nombre'],

                'suma_asegurada': float(dato['suma_asegurada'] or 0),

                'total_prima': float(dato['total_prima'] or 0),

                'total_contribuciones': float(dato['total_contribuciones'] or 0),

                'total_iva': float(dato['total_iva'] or 0),

                'total_retenciones': float(dato['total_retenciones'] or 0),

                'total_facturado': float(dato['total_facturado'] or 0),

                'valor_por_pagar': float(dato['valor_por_pagar'] or 0),

                'cantidad_polizas': dato['cantidad_polizas'],

            }

            ramos.append(ramo)

            # Acumular totales

            for key in totales.keys():

                if key in dato and dato[key]:

                    totales[key] += Decimal(str(dato[key]))

        # Calcular porcentajes

        for ramo in ramos:

            if totales['total_prima'] > 0:

                ramo['porcentaje_prima'] = (

                    ramo['total_prima'] / float(totales['total_prima']) * 100

                )

            else:

                ramo['porcentaje_prima'] = 0

        return {

            'periodo': {

                'desde': fecha_desde.isoformat(),

                'hasta': fecha_hasta.isoformat(),

            },

            'totales': {k: float(v) for k, v in totales.items()},

            'ramos': ramos,

            'cantidad_ramos': len(ramos),

        }

    @classmethod
    def reporte_dias_gestion_siniestros(cls, fecha_desde=None, fecha_hasta=None,

                                         tipo_siniestro_id=None, estado=None):

        """

        Genera un reporte de días promedio de gestión por siniestro.

        Args:

            fecha_desde: Fecha de inicio

            fecha_hasta: Fecha de fin

            tipo_siniestro_id: Filtrar por tipo de siniestro

            estado: Filtrar por estado

        Returns:

            dict: Reporte con promedios y detalle

        """

        if not fecha_hasta:

            fecha_hasta = timezone.now().date()

        if not fecha_desde:

            fecha_desde = fecha_hasta - timedelta(days=365)

        # Filtro base

        filtro = Q(

            fecha_registro__date__gte=fecha_desde,

            fecha_registro__date__lte=fecha_hasta,

        )

        if tipo_siniestro_id:

            filtro &= Q(tipo_siniestro_id=tipo_siniestro_id)

        if estado:

            filtro &= Q(estado=estado)

        siniestros = Siniestro.objects.filter(filtro)

        # Calcular días de gestión para cada siniestro

        datos_siniestros = []

        total_dias = 0

        siniestros_cerrados = 0

        for siniestro in siniestros:

            dias = siniestro.dias_gestion

            datos_siniestros.append({

                'numero_siniestro': siniestro.numero_siniestro,

                'tipo': siniestro.tipo_siniestro.get_nombre_display() if siniestro.tipo_siniestro else 'N/A',

                'estado': siniestro.get_estado_display(),

                'fecha_registro': siniestro.fecha_registro.strftime('%Y-%m-%d'),

                'dias_gestion': dias,

                'monto_estimado': float(siniestro.monto_estimado),

                'monto_pagado': float(siniestro.valor_pagado or 0),

            })

            total_dias += dias

            if siniestro.estado in ['liquidado', 'cerrado']:

                siniestros_cerrados += 1

        # Calcular promedios

        cantidad = len(datos_siniestros)

        promedio_general = total_dias / cantidad if cantidad > 0 else 0

        # Agrupar por tipo de siniestro

        por_tipo = defaultdict(lambda: {'total_dias': 0, 'cantidad': 0})

        for dato in datos_siniestros:

            tipo = dato['tipo']

            por_tipo[tipo]['total_dias'] += dato['dias_gestion']

            por_tipo[tipo]['cantidad'] += 1

        resumen_por_tipo = []

        for tipo, valores in por_tipo.items():

            resumen_por_tipo.append({

                'tipo': tipo,

                'cantidad_siniestros': valores['cantidad'],

                'promedio_dias': valores['total_dias'] / valores['cantidad'] if valores['cantidad'] > 0 else 0,

            })

        # Agrupar por estado

        por_estado = defaultdict(lambda: {'total_dias': 0, 'cantidad': 0})

        for dato in datos_siniestros:

            estado = dato['estado']

            por_estado[estado]['total_dias'] += dato['dias_gestion']

            por_estado[estado]['cantidad'] += 1

        resumen_por_estado = []

        for estado, valores in por_estado.items():

            resumen_por_estado.append({

                'estado': estado,

                'cantidad_siniestros': valores['cantidad'],

                'promedio_dias': valores['total_dias'] / valores['cantidad'] if valores['cantidad'] > 0 else 0,

            })

        # Detalle para contadora con fechas clave y montos

        detalle_contadora = []

        total_estimado = Decimal('0.00')

        total_pagado = Decimal('0.00')

        total_deducible = Decimal('0.00')

        pendientes_pago = 0

        for siniestro in siniestros.select_related('tipo_siniestro', 'poliza__compania_aseguradora'):

            # Calcular días entre hitos

            dias_hasta_envio = None

            dias_envio_respuesta = None

            dias_respuesta_pago = None

            if siniestro.fecha_envio_aseguradora and siniestro.fecha_registro:

                dias_hasta_envio = (siniestro.fecha_envio_aseguradora - siniestro.fecha_registro.date()).days

            if siniestro.fecha_respuesta_aseguradora and siniestro.fecha_envio_aseguradora:

                dias_envio_respuesta = (siniestro.fecha_respuesta_aseguradora - siniestro.fecha_envio_aseguradora).days

            if siniestro.fecha_pago and siniestro.fecha_respuesta_aseguradora:

                dias_respuesta_pago = (siniestro.fecha_pago - siniestro.fecha_respuesta_aseguradora).days

            # Acumular totales

            total_estimado += siniestro.monto_estimado or Decimal('0.00')

            total_pagado += siniestro.valor_pagado or Decimal('0.00')

            total_deducible += siniestro.deducible_aplicado or Decimal('0.00')

            if siniestro.estado not in ['liquidado', 'cerrado', 'rechazado'] and not siniestro.fecha_pago:

                pendientes_pago += 1

            detalle_contadora.append({

                'id': siniestro.pk,

                'numero_siniestro': siniestro.numero_siniestro,

                'tipo': siniestro.tipo_siniestro.nombre if siniestro.tipo_siniestro else 'N/A',

                'compania': siniestro.poliza.compania_aseguradora.nombre if siniestro.poliza and siniestro.poliza.compania_aseguradora else 'N/A',

                'estado': siniestro.get_estado_display(),

                'estado_raw': siniestro.estado,

                # Fechas clave

                'fecha_registro': siniestro.fecha_registro.strftime('%d/%m/%Y') if siniestro.fecha_registro else '-',

                'fecha_envio': siniestro.fecha_envio_aseguradora.strftime('%d/%m/%Y') if siniestro.fecha_envio_aseguradora else '-',

                'fecha_respuesta': siniestro.fecha_respuesta_aseguradora.strftime('%d/%m/%Y') if siniestro.fecha_respuesta_aseguradora else '-',

                'fecha_liquidacion': siniestro.fecha_liquidacion.strftime('%d/%m/%Y') if siniestro.fecha_liquidacion else '-',

                'fecha_pago': siniestro.fecha_pago.strftime('%d/%m/%Y') if siniestro.fecha_pago else '-',

                # Días entre hitos

                'dias_hasta_envio': dias_hasta_envio,

                'dias_envio_respuesta': dias_envio_respuesta,

                'dias_respuesta_pago': dias_respuesta_pago,

                'dias_total': siniestro.dias_gestion,

                # Montos

                'monto_estimado': float(siniestro.monto_estimado or 0),

                'valor_reclamo': float(siniestro.valor_reclamo or 0),

                'deducible': float(siniestro.deducible_aplicado or 0),

                'monto_indemnizado': float(siniestro.monto_indemnizado or 0),

                'valor_pagado': float(siniestro.valor_pagado or 0),

            })

        # Ordenar por fecha de registro (más reciente primero)

        detalle_contadora = sorted(detalle_contadora, key=lambda x: x['fecha_registro'], reverse=True)

        return {

            'periodo': {

                'desde': fecha_desde.isoformat(),

                'hasta': fecha_hasta.isoformat(),

            },

            'resumen': {

                'total_siniestros': cantidad,

                'siniestros_cerrados': siniestros_cerrados,

                'promedio_dias_gestion': round(promedio_general, 1),

            },

            'resumen_contadora': {

                'total_estimado': float(total_estimado),

                'total_pagado': float(total_pagado),

                'total_deducible': float(total_deducible),

                'pendientes_pago': pendientes_pago,

                'monto_pendiente': float(total_estimado - total_pagado - total_deducible),

            },

            'por_tipo': sorted(resumen_por_tipo, key=lambda x: -x['promedio_dias']),

            'por_estado': sorted(resumen_por_estado, key=lambda x: -x['cantidad_siniestros']),

            'detalle': sorted(datos_siniestros, key=lambda x: -x['dias_gestion'])[:50],

            'detalle_contadora': detalle_contadora,

        }

    @classmethod
    def reporte_siniestros_por_dependencia(cls, fecha_desde=None, fecha_hasta=None):

        """

        Genera un reporte de siniestros agrupados por departamento/área.

        Args:

            fecha_desde: Fecha de inicio

            fecha_hasta: Fecha de fin

        Returns:

            dict: Reporte con totales por dependencia

        """

        if not fecha_hasta:

            fecha_hasta = timezone.now().date()

        if not fecha_desde:

            fecha_desde = fecha_hasta - timedelta(days=365)

        filtro = Q(

            fecha_registro__date__gte=fecha_desde,

            fecha_registro__date__lte=fecha_hasta,

        )

        # Agrupar por departamento del responsable

        datos = Siniestro.objects.filter(filtro).values(

            'responsable_custodio__departamento',

        ).annotate(

            cantidad=Count('id'),

            monto_estimado_total=Sum('monto_estimado'),

            monto_pagado_total=Coalesce(Sum('valor_pagado'), Decimal('0.00')),

            promedio_estimado=Avg('monto_estimado'),

        ).order_by('-cantidad')

        dependencias = []

        total_cantidad = 0

        total_estimado = Decimal('0.00')

        total_pagado = Decimal('0.00')

        for dato in datos:

            depto = dato['responsable_custodio__departamento'] or 'Sin Asignar'

            dependencias.append({

                'dependencia': depto,

                'cantidad_siniestros': dato['cantidad'],

                'monto_estimado': float(dato['monto_estimado_total'] or 0),

                'monto_pagado': float(dato['monto_pagado_total'] or 0),

                'promedio_estimado': float(dato['promedio_estimado'] or 0),

            })

            total_cantidad += dato['cantidad']

            total_estimado += dato['monto_estimado_total'] or Decimal('0.00')

            total_pagado += dato['monto_pagado_total'] or Decimal('0.00')

        # Calcular porcentajes

        for dep in dependencias:

            if total_cantidad > 0:

                dep['porcentaje_cantidad'] = (dep['cantidad_siniestros'] / total_cantidad) * 100

            else:

                dep['porcentaje_cantidad'] = 0

            if total_estimado > 0:

                dep['porcentaje_monto'] = (Decimal(str(dep['monto_estimado'])) / total_estimado) * 100

            else:

                dep['porcentaje_monto'] = 0

        return {

            'periodo': {

                'desde': fecha_desde.isoformat(),

                'hasta': fecha_hasta.isoformat(),

            },

            'totales': {

                'cantidad_siniestros': total_cantidad,

                'monto_estimado': float(total_estimado),

                'monto_pagado': float(total_pagado),

            },

            'dependencias': dependencias,

        }

    @classmethod
    def reporte_siniestralidad_por_compania(cls, fecha_desde=None, fecha_hasta=None):

        """

        Genera un reporte comparativo de siniestralidad por compañía aseguradora.

        Args:

            fecha_desde: Fecha de inicio

            fecha_hasta: Fecha de fin

        Returns:

            dict: Reporte comparativo entre aseguradoras

        """

        if not fecha_hasta:

            fecha_hasta = timezone.now().date()

        if not fecha_desde:

            fecha_desde = fecha_hasta - timedelta(days=365)

        companias = CompaniaAseguradora.objects.filter(activo=True)

        resultados = []

        for compania in companias:

            datos_siniestralidad = cls.calcular_siniestralidad(

                fecha_desde=fecha_desde,

                fecha_hasta=fecha_hasta,

                compania_id=compania.id,

            )

            # Contar pólizas vigentes

            polizas_vigentes = Poliza.objects.filter(

                compania_aseguradora=compania,

                estado__in=['vigente', 'por_vencer'],

            ).count()

            # Contar siniestros en el período

            siniestros_periodo = Siniestro.objects.filter(

                poliza__compania_aseguradora=compania,

                fecha_registro__date__gte=fecha_desde,

                fecha_registro__date__lte=fecha_hasta,

            ).count()

            resultados.append({

                'compania': compania.nombre,

                'polizas_vigentes': polizas_vigentes,

                'siniestros_periodo': siniestros_periodo,

                'siniestros_pagados': datos_siniestralidad['totales']['siniestros_pagados'],

                'primas_pagadas': datos_siniestralidad['totales']['primas_pagadas'],

                'indice_siniestralidad': datos_siniestralidad['totales']['indice_siniestralidad'],

                'nivel': datos_siniestralidad['interpretacion']['nivel'],

            })

        # Ordenar por índice de siniestralidad

        resultados = sorted(resultados, key=lambda x: x['indice_siniestralidad'])

        return {

            'periodo': {

                'desde': fecha_desde.isoformat(),

                'hasta': fecha_hasta.isoformat(),

            },

            'companias': resultados,

        }

    @classmethod
    def generar_resumen_ejecutivo(cls, fecha_desde=None, fecha_hasta=None):

        """

        Genera un resumen ejecutivo completo con todas las métricas clave.

        Args:

            fecha_desde: Fecha de inicio

            fecha_hasta: Fecha de fin

        Returns:

            dict: Resumen ejecutivo completo

        """

        if not fecha_hasta:

            fecha_hasta = timezone.now().date()

        if not fecha_desde:

            fecha_desde = fecha_hasta - timedelta(days=365)

        # Calcular siniestralidad general

        siniestralidad = cls.calcular_siniestralidad(

            fecha_desde=fecha_desde,

            fecha_hasta=fecha_hasta,

        )

        # Reporte por ramos

        ramos = cls.reporte_gasto_por_ramos(

            fecha_desde=fecha_desde,

            fecha_hasta=fecha_hasta,

        )

        # Días de gestión

        dias_gestion = cls.reporte_dias_gestion_siniestros(

            fecha_desde=fecha_desde,

            fecha_hasta=fecha_hasta,

        )

        # Por dependencia

        dependencias = cls.reporte_siniestros_por_dependencia(

            fecha_desde=fecha_desde,

            fecha_hasta=fecha_hasta,

        )

        # Pólizas activas

        polizas_activas = Poliza.objects.filter(

            estado__in=['vigente', 'por_vencer']

        ).count()

        polizas_por_vencer = Poliza.objects.filter(

            estado='por_vencer'

        ).count()

        # Siniestros pendientes

        siniestros_pendientes = Siniestro.objects.filter(

            estado__in=['registrado', 'documentacion_pendiente', 'enviado_aseguradora', 'en_evaluacion']

        ).count()

        return {

            'periodo': {

                'desde': fecha_desde.isoformat(),

                'hasta': fecha_hasta.isoformat(),

            },

            'indicadores_clave': {

                'indice_siniestralidad': siniestralidad['totales']['indice_siniestralidad'],

                'nivel_siniestralidad': siniestralidad['interpretacion']['nivel'],

                'polizas_activas': polizas_activas,

                'polizas_por_vencer': polizas_por_vencer,

                'siniestros_pendientes': siniestros_pendientes,

                'promedio_dias_gestion': dias_gestion['resumen']['promedio_dias_gestion'],

            },

            'financiero': {

                'total_primas': siniestralidad['totales']['primas_pagadas'],

                'total_siniestros': siniestralidad['totales']['siniestros_pagados'],

                'total_asegurado': ramos['totales'].get('suma_asegurada', 0),

            },

            'top_ramos': ramos['ramos'][:5],

            'top_dependencias': dependencias['dependencias'][:5],

            'tendencia_mensual': siniestralidad['detalle_mensual'],

        }
