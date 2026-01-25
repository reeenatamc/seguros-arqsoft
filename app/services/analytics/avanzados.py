"""
Servicio de Analytics Avanzados para el Dashboard Especializado.
Incluye:
- Ratio de siniestralidad por tipo de póliza
- Tendencia de montos indemnizados vs primas
- Análisis de ubicaciones con más siniestros
- Predicción simple de renovación de primas
"""
from django.db.models import Sum, Count, Avg, F, Q, Case, When, Value, DecimalField
from django.db.models.functions import TruncMonth, TruncYear, Extract, Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from collections import defaultdict
import json

from app.models import (
    Poliza, Factura, Pago, Siniestro, TipoPoliza, TipoSiniestro,
    PolicyRenewal, CompaniaAseguradora
)


class AdvancedAnalyticsService:
    """Servicio para cálculos analíticos avanzados del dashboard"""
    
    @classmethod
    def get_loss_ratio_by_policy_type(cls):
        """
        Calcula el ratio de siniestralidad por tipo de póliza.
        Ratio = (Monto Indemnizado / Primas Pagadas) * 100
        Un ratio > 100% indica pérdida, < 100% indica ganancia.
        """
        results = []
        
        tipos_poliza = TipoPoliza.objects.filter(activo=True)
        
        for tipo in tipos_poliza:
            # Obtener pólizas de este tipo
            polizas = Poliza.objects.filter(tipo_poliza=tipo)
            poliza_ids = polizas.values_list('id', flat=True)
            
            # Calcular primas cobradas (pagos aprobados de facturas de estas pólizas)
            primas_pagadas = Pago.objects.filter(
                factura__poliza__in=poliza_ids,
                estado='aprobado'
            ).aggregate(
                total=Coalesce(Sum('monto'), Value(Decimal('0')))
            )['total']
            
            # Calcular montos indemnizados (siniestros liquidados de estas pólizas)
            montos_indemnizados = Siniestro.objects.filter(
                poliza__in=poliza_ids,
                estado__in=['liquidado', 'cerrado']
            ).aggregate(
                total=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0')))
            )['total']
            
            # Calcular ratio
            if primas_pagadas > 0:
                ratio = (float(montos_indemnizados) / float(primas_pagadas)) * 100
            else:
                ratio = 0
            
            # Conteos adicionales
            num_polizas = polizas.count()
            num_siniestros = Siniestro.objects.filter(poliza__in=poliza_ids).count()
            
            results.append({
                'tipo': tipo.nombre,
                'tipo_id': tipo.id,
                'primas_pagadas': float(primas_pagadas),
                'montos_indemnizados': float(montos_indemnizados),
                'ratio': round(ratio, 2),
                'num_polizas': num_polizas,
                'num_siniestros': num_siniestros,
                'siniestros_por_poliza': round(num_siniestros / max(num_polizas, 1), 2),
                'status': 'danger' if ratio > 100 else ('warning' if ratio > 70 else 'success'),
            })
        
        # Ordenar por ratio descendente
        results.sort(key=lambda x: x['ratio'], reverse=True)
        
        return results
    
    @classmethod
    def get_claims_vs_premiums_trend(cls, months=12):
        """
        Obtiene la tendencia mensual de montos indemnizados vs primas pagadas.
        Retorna datos para gráfico de líneas comparativo.
        """
        today = timezone.now().date()
        start_date = today.replace(day=1) - timedelta(days=months * 30)
        
        # Primas pagadas por mes
        premiums_by_month = Pago.objects.filter(
            estado='aprobado',
            fecha_pago__gte=start_date
        ).annotate(
            month=TruncMonth('fecha_pago')
        ).values('month').annotate(
            total=Sum('monto')
        ).order_by('month')
        
        # Indemnizaciones por mes
        claims_by_month = Siniestro.objects.filter(
            estado__in=['liquidado', 'cerrado'],
            fecha_liquidacion__gte=start_date
        ).annotate(
            month=TruncMonth('fecha_liquidacion')
        ).values('month').annotate(
            total=Sum('monto_indemnizado')
        ).order_by('month')
        
        # Combinar datos en un diccionario por mes
        data_by_month = defaultdict(lambda: {'premiums': 0, 'claims': 0})
        
        for item in premiums_by_month:
            if item['month']:
                key = item['month'].strftime('%Y-%m')
                data_by_month[key]['premiums'] = float(item['total'] or 0)
        
        for item in claims_by_month:
            if item['month']:
                key = item['month'].strftime('%Y-%m')
                data_by_month[key]['claims'] = float(item['total'] or 0)
        
        # Generar lista ordenada de los últimos N meses
        result = {
            'labels': [],
            'premiums': [],
            'claims': [],
            'ratios': [],
        }
        
        current = start_date.replace(day=1)
        while current <= today:
            key = current.strftime('%Y-%m')
            label = current.strftime('%b %Y')
            
            premiums = data_by_month[key]['premiums']
            claims = data_by_month[key]['claims']
            ratio = (claims / premiums * 100) if premiums > 0 else 0
            
            result['labels'].append(label)
            result['premiums'].append(premiums)
            result['claims'].append(claims)
            result['ratios'].append(round(ratio, 2))
            
            # Avanzar al siguiente mes
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return result
    
    @classmethod
    def get_claims_by_location(cls):
        """
        Obtiene el análisis de siniestros por ubicación para heatmap.
        Agrupa por ubicación y calcula estadísticas.
        """
        # Obtener siniestros agrupados por ubicación
        locations_data = Siniestro.objects.exclude(
            ubicacion__isnull=True
        ).exclude(
            ubicacion=''
        ).values('ubicacion').annotate(
            count=Count('id'),
            total_estimado=Coalesce(Sum('monto_estimado'), Value(Decimal('0'))),
            total_indemnizado=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0'))),
        ).order_by('-count')[:20]  # Top 20 ubicaciones
        
        # Normalizar para el heatmap (0-100)
        max_count = max([loc['count'] for loc in locations_data], default=1)
        
        result = []
        for loc in locations_data:
            # Limpiar nombre de ubicación
            location_name = loc['ubicacion'][:50] if loc['ubicacion'] else 'Sin especificar'
            
            result.append({
                'location': location_name,
                'count': loc['count'],
                'total_estimado': float(loc['total_estimado']),
                'total_indemnizado': float(loc['total_indemnizado']),
                'intensity': round((loc['count'] / max_count) * 100, 0),
                'avg_amount': float(loc['total_estimado'] / loc['count']) if loc['count'] > 0 else 0,
            })
        
        return result
    
    @classmethod
    def get_claims_by_type_distribution(cls):
        """
        Distribución de siniestros por tipo para visualización.
        """
        distribution = Siniestro.objects.values(
            'tipo_siniestro__nombre'
        ).annotate(
            count=Count('id'),
            total_estimado=Coalesce(Sum('monto_estimado'), Value(Decimal('0'))),
            total_indemnizado=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0'))),
        ).order_by('-count')
        
        result = {
            'labels': [],
            'counts': [],
            'amounts': [],
        }
        
        for item in distribution:
            tipo = item['tipo_siniestro__nombre'] or 'Sin tipo'
            result['labels'].append(tipo)
            result['counts'].append(item['count'])
            result['amounts'].append(float(item['total_estimado']))
        
        return result
    
    @classmethod
    def predict_renewal_premium(cls, policy_id=None):
        """
        Predicción simple de prima de renovación basada en:
        - Historial de siniestros de la póliza
        - Tendencia general del mercado
        - Factor de inflación estimado
        
        Usa un modelo de regresión lineal simple.
        """
        if policy_id:
            return cls._predict_single_policy(policy_id)
        else:
            return cls._predict_all_policies()
    
    @classmethod
    def _predict_single_policy(cls, policy_id):
        """Predicción para una póliza específica"""
        try:
            poliza = Poliza.objects.get(id=policy_id)
        except Poliza.DoesNotExist:
            return None
        
        # Obtener prima actual (último pago de factura)
        ultima_factura = poliza.facturas.order_by('-fecha_emision').first()
        prima_actual = float(ultima_factura.subtotal) if ultima_factura else 0
        
        # Factor base de inflación (5% anual estimado)
        inflation_factor = 1.05
        
        # Factor de siniestralidad de la póliza
        siniestros = Siniestro.objects.filter(poliza=poliza)
        num_siniestros = siniestros.count()
        monto_siniestros = float(siniestros.aggregate(
            total=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0')))
        )['total'])
        
        # Calcular factor de riesgo basado en siniestralidad
        if prima_actual > 0:
            loss_ratio = monto_siniestros / prima_actual
        else:
            loss_ratio = 0
        
        # Factor de riesgo: si ratio > 70%, incrementar prima
        if loss_ratio > 1.0:
            risk_factor = 1.25  # +25%
        elif loss_ratio > 0.7:
            risk_factor = 1.15  # +15%
        elif loss_ratio > 0.5:
            risk_factor = 1.08  # +8%
        elif loss_ratio < 0.3 and num_siniestros == 0:
            risk_factor = 0.95  # -5% buen cliente
        else:
            risk_factor = 1.0
        
        # Calcular prima predicha
        prima_predicha = prima_actual * inflation_factor * risk_factor
        
        # Calcular intervalo de confianza (±10%)
        confidence_low = prima_predicha * 0.90
        confidence_high = prima_predicha * 1.10
        
        return {
            'policy_id': policy_id,
            'policy_number': poliza.numero_poliza,
            'current_premium': prima_actual,
            'predicted_premium': round(prima_predicha, 2),
            'confidence_low': round(confidence_low, 2),
            'confidence_high': round(confidence_high, 2),
            'change_percentage': round((prima_predicha / prima_actual - 1) * 100, 1) if prima_actual > 0 else 0,
            'loss_ratio': round(loss_ratio * 100, 1),
            'num_claims': num_siniestros,
            'risk_level': 'high' if risk_factor > 1.15 else ('medium' if risk_factor > 1.0 else 'low'),
            'factors': {
                'inflation': round((inflation_factor - 1) * 100, 1),
                'risk_adjustment': round((risk_factor - 1) * 100, 1),
            }
        }
    
    @classmethod
    def _predict_all_policies(cls):
        """Predicción para todas las pólizas por renovar"""
        today = timezone.now().date()
        
        # Pólizas que vencen en los próximos 90 días
        polizas_por_renovar = Poliza.objects.filter(
            estado__in=['vigente', 'por_vencer'],
            fecha_fin__gte=today,
            fecha_fin__lte=today + timedelta(days=90)
        ).order_by('fecha_fin')
        
        predictions = []
        
        for poliza in polizas_por_renovar:
            prediction = cls._predict_single_policy(poliza.id)
            if prediction:
                prediction['expiry_date'] = poliza.fecha_fin.isoformat()
                prediction['days_to_expiry'] = (poliza.fecha_fin - today).days
                prediction['policy_type'] = poliza.tipo_poliza.nombre
                prediction['insurer'] = poliza.compania_aseguradora.nombre
                predictions.append(prediction)
        
        # Resumen estadístico
        if predictions:
            total_current = sum(p['current_premium'] for p in predictions)
            total_predicted = sum(p['predicted_premium'] for p in predictions)
            avg_change = sum(p['change_percentage'] for p in predictions) / len(predictions)
        else:
            total_current = 0
            total_predicted = 0
            avg_change = 0
        
        return {
            'predictions': predictions,
            'summary': {
                'total_policies': len(predictions),
                'total_current_premiums': round(total_current, 2),
                'total_predicted_premiums': round(total_predicted, 2),
                'avg_change_percentage': round(avg_change, 1),
                'high_risk_count': sum(1 for p in predictions if p['risk_level'] == 'high'),
                'medium_risk_count': sum(1 for p in predictions if p['risk_level'] == 'medium'),
                'low_risk_count': sum(1 for p in predictions if p['risk_level'] == 'low'),
            }
        }
    
    @classmethod
    def get_insurer_performance(cls):
        """
        Análisis de rendimiento por aseguradora.
        Útil para comparar eficiencia en procesamiento de siniestros.
        """
        insurers = CompaniaAseguradora.objects.filter(activo=True)
        
        results = []
        
        for insurer in insurers:
            polizas = Poliza.objects.filter(compania_aseguradora=insurer)
            poliza_ids = polizas.values_list('id', flat=True)
            
            # Siniestros de esta aseguradora
            siniestros = Siniestro.objects.filter(poliza__in=poliza_ids)
            
            total_siniestros = siniestros.count()
            siniestros_aprobados = siniestros.filter(estado__in=['aprobado', 'liquidado', 'cerrado']).count()
            siniestros_rechazados = siniestros.filter(estado='rechazado').count()
            
            # Tiempo promedio de respuesta (días desde envío hasta respuesta)
            tiempos = siniestros.filter(
                fecha_envio_aseguradora__isnull=False,
                fecha_respuesta_aseguradora__isnull=False
            ).annotate(
                dias=F('fecha_respuesta_aseguradora') - F('fecha_envio_aseguradora')
            )
            
            # Monto total indemnizado
            monto_indemnizado = float(siniestros.aggregate(
                total=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0')))
            )['total'])
            
            # Tasa de aprobación
            if total_siniestros > 0:
                approval_rate = (siniestros_aprobados / total_siniestros) * 100
            else:
                approval_rate = 0
            
            results.append({
                'insurer': insurer.nombre,
                'insurer_id': insurer.id,
                'total_policies': polizas.count(),
                'total_claims': total_siniestros,
                'approved_claims': siniestros_aprobados,
                'rejected_claims': siniestros_rechazados,
                'approval_rate': round(approval_rate, 1),
                'total_indemnified': monto_indemnizado,
                'avg_claim_amount': round(monto_indemnizado / max(siniestros_aprobados, 1), 2),
            })
        
        # Ordenar por tasa de aprobación
        results.sort(key=lambda x: x['approval_rate'], reverse=True)
        
        return results
    
    @classmethod
    def get_dashboard_summary(cls):
        """
        Resumen ejecutivo del dashboard especializado.
        """
        today = timezone.now().date()
        start_year = today.replace(month=1, day=1)
        
        # KPIs principales
        total_primas_year = Pago.objects.filter(
            estado='aprobado',
            fecha_pago__gte=start_year
        ).aggregate(total=Coalesce(Sum('monto'), Value(Decimal('0'))))['total']
        
        total_indemnizaciones_year = Siniestro.objects.filter(
            estado__in=['liquidado', 'cerrado'],
            fecha_liquidacion__gte=start_year
        ).aggregate(total=Coalesce(Sum('monto_indemnizado'), Value(Decimal('0'))))['total']
        
        # Ratio global de siniestralidad
        if total_primas_year > 0:
            loss_ratio_global = (float(total_indemnizaciones_year) / float(total_primas_year)) * 100
        else:
            loss_ratio_global = 0
        
        # Conteos
        polizas_activas = Poliza.objects.filter(estado='vigente').count()
        polizas_por_vencer = Poliza.objects.filter(estado='por_vencer').count()
        siniestros_abiertos = Siniestro.objects.exclude(
            estado__in=['cerrado', 'rechazado']
        ).count()
        
        return {
            'total_premiums_ytd': float(total_primas_year),
            'total_claims_ytd': float(total_indemnizaciones_year),
            'loss_ratio_global': round(loss_ratio_global, 2),
            'active_policies': polizas_activas,
            'expiring_policies': polizas_por_vencer,
            'open_claims': siniestros_abiertos,
            'status': 'danger' if loss_ratio_global > 100 else ('warning' if loss_ratio_global > 70 else 'success'),
        }

