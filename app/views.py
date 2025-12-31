from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse
from django.utils import timezone

from .models import (
    Poliza, Factura, Siniestro, Alerta, CompaniaAseguradora, TipoPoliza, 
    TipoSiniestro, CorredorSeguros, InsuredAsset, Quote, QuoteOption, 
    PolicyRenewal, PaymentApproval, CalendarEvent
)
from .services import (
    EstadisticasService, ExportacionService, ReportesService,
    DashboardAnalyticsService, DashboardFiltersService, DateRangePresets,
    AdvancedAnalyticsService
)
from .services.pdf_reportes import PDFReportesService


@login_required
def dashboard(request):
    """
    Vista principal del dashboard con filtros avanzados estilo Odoo.
    Soporta date range picker, filtros por entidad, y actualización dinámica.
    """
    import json
    
    # Parsear filtros desde la request
    filters = DashboardFiltersService.parse_filters_from_request(request)
    
    # Obtener filtros disponibles para los selectores
    available_filters = DashboardFiltersService.get_available_filters()
    
    # Obtener estadísticas filtradas
    filtered_stats = DashboardFiltersService.get_filtered_stats(filters)
    
    # Obtener datos para gráficos filtrados
    chart_data = DashboardFiltersService.get_chart_data(filters)
    
    # Obtener listas de registros
    lists_data = DashboardFiltersService.get_lists_data(filters)
    
    # Estadísticas globales (sin filtros) para KPIs generales
    kpis = EstadisticasService.get_kpis()
    
    # Datos comparativos y tendencias (usando el sistema anterior para compatibilidad)
    period_type = request.GET.get('period', DashboardAnalyticsService.PERIOD_MONTH)
    if period_type not in DashboardAnalyticsService.PERIOD_CHOICES:
        period_type = DashboardAnalyticsService.PERIOD_MONTH
    
    comparative_data = DashboardAnalyticsService.get_comparative_stats(period_type)
    year_comparison = DashboardAnalyticsService.get_year_over_year_comparison()
    quick_actions = DashboardAnalyticsService.get_quick_actions_data()
    
    context = {
        # Filtros
        'filters': filters,
        'available_filters': available_filters,
        'date_presets': DateRangePresets.CHOICES,
        
        # Estadísticas filtradas
        'stats': filtered_stats,
        'chart_data': json.dumps(chart_data),
        
        # Listas de registros
        'expiring_policies': lists_data['expiring_policies'],
        'pending_invoices': lists_data['pending_invoices'],
        'active_claims': lists_data['active_claims'],
        
        # KPIs globales
        'kpis': kpis,
        
        # Datos comparativos
        'period_type': period_type,
        'period_choices': DashboardAnalyticsService.PERIOD_CHOICES,
        'comparative': comparative_data,
        'year_comparison': json.dumps(year_comparison),
        'quick_actions': quick_actions,
    }
    
    return render(request, 'app/dashboard/index.html', context)


@login_required
def polizas_lista(request):
    polizas = Poliza.objects.select_related(
        'compania_aseguradora', 'corredor_seguros', 'tipo_poliza'
    ).order_by('-fecha_inicio')
    
    query = request.GET.get('q', '').strip()
    if query:
        polizas = polizas.filter(
            Q(numero_poliza__icontains=query) |
            Q(compania_aseguradora__nombre__icontains=query) |
            Q(corredor_seguros__nombre__icontains=query)
        )
    
    estado = request.GET.get('estado')
    if estado:
        polizas = polizas.filter(estado=estado)
    
    compania = request.GET.get('compania')
    if compania:
        polizas = polizas.filter(compania_aseguradora_id=compania)
    
    paginator = Paginator(polizas, 15)
    page = request.GET.get('page', 1)
    polizas_page = paginator.get_page(page)
    
    companias = CompaniaAseguradora.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'polizas': polizas_page,
        'estado_filtro': estado,
        'query': query,
        'companias': companias,
        'compania_filtro': compania,
        'total_resultados': paginator.count,
    }
    
    return render(request, 'app/polizas/lista.html', context)


@login_required
@require_GET
def polizas_exportar(request):
    formato = request.GET.get('formato', 'excel')
    
    polizas = Poliza.objects.select_related(
        'compania_aseguradora', 'corredor_seguros', 'tipo_poliza'
    )
    
    estado = request.GET.get('estado')
    if estado:
        polizas = polizas.filter(estado=estado)
    
    if formato == 'csv':
        return ExportacionService.exportar_polizas_csv(polizas)
    return ExportacionService.exportar_polizas_excel(polizas)


@login_required
def facturas_lista(request):
    facturas = Factura.objects.select_related(
        'poliza', 'poliza__compania_aseguradora'
    ).order_by('-fecha_emision')
    
    query = request.GET.get('q', '').strip()
    if query:
        facturas = facturas.filter(
            Q(numero_factura__icontains=query) |
            Q(poliza__numero_poliza__icontains=query) |
            Q(poliza__compania_aseguradora__nombre__icontains=query)
        )
    
    estado = request.GET.get('estado')
    if estado:
        facturas = facturas.filter(estado=estado)
    
    paginator = Paginator(facturas, 15)
    page = request.GET.get('page', 1)
    facturas_page = paginator.get_page(page)
    
    context = {
        'facturas': facturas_page,
        'estado_filtro': estado,
        'query': query,
        'total_resultados': paginator.count,
    }
    
    return render(request, 'app/facturas/lista.html', context)


@login_required
@require_GET
def facturas_exportar(request):
    formato = request.GET.get('formato', 'excel')
    
    facturas = Factura.objects.select_related(
        'poliza', 'poliza__compania_aseguradora'
    )
    
    estado = request.GET.get('estado')
    if estado:
        facturas = facturas.filter(estado=estado)
    
    if formato == 'csv':
        return ExportacionService.exportar_facturas_csv(facturas)
    return ExportacionService.exportar_facturas_excel(facturas)


@login_required
def siniestros_lista(request):
    siniestros = Siniestro.objects.select_related(
        'poliza', 'tipo_siniestro', 'poliza__compania_aseguradora'
    ).order_by('-fecha_siniestro')
    
    query = request.GET.get('q', '').strip()
    if query:
        siniestros = siniestros.filter(
            Q(numero_siniestro__icontains=query) |
            Q(bien_nombre__icontains=query) |
            Q(poliza__numero_poliza__icontains=query)
        )
    
    estado = request.GET.get('estado')
    if estado:
        siniestros = siniestros.filter(estado=estado)
    
    tipo = request.GET.get('tipo')
    if tipo:
        siniestros = siniestros.filter(tipo_siniestro_id=tipo)
    
    paginator = Paginator(siniestros, 15)
    page = request.GET.get('page', 1)
    siniestros_page = paginator.get_page(page)
    
    tipos = TipoSiniestro.objects.filter(activo=True)
    
    context = {
        'siniestros': siniestros_page,
        'estado_filtro': estado,
        'query': query,
        'tipos': tipos,
        'tipo_filtro': tipo,
        'total_resultados': paginator.count,
    }
    
    return render(request, 'app/siniestros/lista.html', context)


@login_required
@require_GET
def siniestros_exportar(request):
    formato = request.GET.get('formato', 'excel')
    
    siniestros = Siniestro.objects.select_related(
        'poliza', 'tipo_siniestro', 'poliza__compania_aseguradora'
    )
    
    estado = request.GET.get('estado')
    if estado:
        siniestros = siniestros.filter(estado=estado)
    
    if formato == 'csv':
        return ExportacionService.exportar_siniestros_csv(siniestros)
    return ExportacionService.exportar_siniestros_excel(siniestros)


@login_required
def reportes_dashboard(request):
    stats = EstadisticasService.get_dashboard_stats()
    kpis = EstadisticasService.get_kpis()
    
    graficos_polizas = ReportesService.get_datos_graficos_polizas()
    graficos_facturas = ReportesService.get_datos_graficos_facturas()
    graficos_siniestros = ReportesService.get_datos_graficos_siniestros_mensual()
    
    polizas_por_compania = EstadisticasService.get_polizas_por_compania()
    polizas_por_tipo = EstadisticasService.get_polizas_por_tipo()
    siniestros_por_tipo = EstadisticasService.get_siniestros_por_tipo()
    
    context = {
        'stats': stats,
        'kpis': kpis,
        'graficos_polizas': graficos_polizas,
        'graficos_facturas': graficos_facturas,
        'graficos_siniestros': graficos_siniestros,
        'polizas_por_compania': polizas_por_compania,
        'polizas_por_tipo': polizas_por_tipo,
        'siniestros_por_tipo': siniestros_por_tipo,
    }
    
    return render(request, 'app/reportes/dashboard.html', context)


@login_required
def reportes_polizas(request):
    filtros = {
        'estado': request.GET.get('estado'),
        'compania': request.GET.get('compania'),
        'tipo': request.GET.get('tipo'),
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta'),
    }
    
    filtros = {k: v for k, v in filtros.items() if v}
    
    reporte = ReportesService.generar_reporte_polizas(filtros)
    
    paginator = Paginator(reporte['queryset'], 20)
    page = request.GET.get('page', 1)
    polizas_page = paginator.get_page(page)
    
    companias = CompaniaAseguradora.objects.filter(activo=True)
    tipos = TipoPoliza.objects.filter(activo=True)
    
    context = {
        'polizas': polizas_page,
        'totales': reporte['totales'],
        'por_compania': reporte['por_compania'],
        'por_tipo': reporte['por_tipo'],
        'companias': companias,
        'tipos': tipos,
        'filtros': filtros,
    }
    
    return render(request, 'app/reportes/polizas.html', context)


@login_required
def reportes_siniestros(request):
    filtros = {
        'estado': request.GET.get('estado'),
        'tipo': request.GET.get('tipo'),
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta'),
    }
    
    filtros = {k: v for k, v in filtros.items() if v}
    
    reporte = ReportesService.generar_reporte_siniestros(filtros)
    
    paginator = Paginator(reporte['queryset'], 20)
    page = request.GET.get('page', 1)
    siniestros_page = paginator.get_page(page)
    
    tipos = TipoSiniestro.objects.filter(activo=True)
    
    context = {
        'siniestros': siniestros_page,
        'totales': reporte['totales'],
        'por_tipo': reporte['por_tipo'],
        'por_estado': reporte['por_estado'],
        'tipos': tipos,
        'filtros': filtros,
    }
    
    return render(request, 'app/reportes/siniestros.html', context)


@login_required
def reportes_polizas_pdf(request):
    """Exporta el reporte de pólizas en formato PDF."""
    filtros = {
        'estado': request.GET.get('estado'),
        'compania': request.GET.get('compania'),
        'tipo': request.GET.get('tipo'),
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta'),
    }
    
    filtros = {k: v for k, v in filtros.items() if v}
    
    # Construir texto de filtros para el reporte
    filtros_texto = []
    if filtros.get('estado'):
        filtros_texto.append(f"Estado: {filtros['estado']}")
    if filtros.get('compania'):
        try:
            compania = CompaniaAseguradora.objects.get(id=filtros['compania'])
            filtros_texto.append(f"Compañía: {compania.nombre}")
        except CompaniaAseguradora.DoesNotExist:
            pass
    if filtros.get('tipo'):
        try:
            tipo = TipoPoliza.objects.get(id=filtros['tipo'])
            filtros_texto.append(f"Tipo: {tipo.nombre}")
        except TipoPoliza.DoesNotExist:
            pass
    if filtros.get('fecha_desde'):
        filtros_texto.append(f"Desde: {filtros['fecha_desde']}")
    if filtros.get('fecha_hasta'):
        filtros_texto.append(f"Hasta: {filtros['fecha_hasta']}")
    
    reporte = ReportesService.generar_reporte_polizas(filtros)
    
    return PDFReportesService.generar_reporte_polizas_pdf(
        reporte,
        filtros_texto=" | ".join(filtros_texto) if filtros_texto else None
    )


@login_required
def reportes_siniestros_pdf(request):
    """Exporta el reporte de siniestros en formato PDF."""
    filtros = {
        'estado': request.GET.get('estado'),
        'tipo': request.GET.get('tipo'),
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta'),
    }
    
    filtros = {k: v for k, v in filtros.items() if v}
    
    # Construir texto de filtros para el reporte
    filtros_texto = []
    if filtros.get('estado'):
        filtros_texto.append(f"Estado: {filtros['estado']}")
    if filtros.get('tipo'):
        try:
            tipo = TipoSiniestro.objects.get(id=filtros['tipo'])
            filtros_texto.append(f"Tipo: {tipo.nombre}")
        except TipoSiniestro.DoesNotExist:
            pass
    if filtros.get('fecha_desde'):
        filtros_texto.append(f"Desde: {filtros['fecha_desde']}")
    if filtros.get('fecha_hasta'):
        filtros_texto.append(f"Hasta: {filtros['fecha_hasta']}")
    
    reporte = ReportesService.generar_reporte_siniestros(filtros)
    
    return PDFReportesService.generar_reporte_siniestros_pdf(
        reporte,
        filtros_texto=" | ".join(filtros_texto) if filtros_texto else None
    )


@login_required
def reportes_facturas_pdf(request):
    """Exporta el reporte de facturas en formato PDF."""
    filtros = {
        'estado': request.GET.get('estado'),
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta'),
    }
    
    filtros = {k: v for k, v in filtros.items() if v}
    
    # Construir texto de filtros para el reporte
    filtros_texto = []
    if filtros.get('estado'):
        filtros_texto.append(f"Estado: {filtros['estado']}")
    if filtros.get('fecha_desde'):
        filtros_texto.append(f"Desde: {filtros['fecha_desde']}")
    if filtros.get('fecha_hasta'):
        filtros_texto.append(f"Hasta: {filtros['fecha_hasta']}")
    
    reporte = ReportesService.generar_reporte_facturas(filtros)
    
    return PDFReportesService.generar_reporte_facturas_pdf(
        reporte,
        filtros_texto=" | ".join(filtros_texto) if filtros_texto else None
    )


@login_required
def reportes_ejecutivo_pdf(request):
    """Genera un reporte ejecutivo general en PDF."""
    stats = EstadisticasService.get_dashboard_stats()
    kpis = EstadisticasService.get_kpis()
    
    dashboard_data = {
        'stats': stats,
        'kpis': kpis,
    }
    
    return PDFReportesService.generar_reporte_ejecutivo_pdf(dashboard_data)


@login_required
def alertas_lista(request):
    alertas = Alerta.objects.select_related(
        'poliza', 'factura', 'siniestro'
    ).prefetch_related('destinatarios').order_by('-fecha_creacion')
    
    estado = request.GET.get('estado')
    if estado:
        alertas = alertas.filter(estado=estado)
    
    tipo = request.GET.get('tipo')
    if tipo:
        alertas = alertas.filter(tipo_alerta=tipo)
    
    paginator = Paginator(alertas, 20)
    page = request.GET.get('page', 1)
    alertas_page = paginator.get_page(page)
    
    context = {
        'alertas': alertas_page,
        'estado_filtro': estado,
        'tipo_filtro': tipo,
    }
    
    return render(request, 'app/alertas/lista.html', context)


@login_required
@require_POST
def alerta_marcar_leida(request, pk):
    alerta = get_object_or_404(Alerta, pk=pk)
    alerta.marcar_como_leida()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    return redirect('alertas_lista')


@login_required
def api_stats(request):
    stats = EstadisticasService.get_dashboard_stats()
    return JsonResponse(stats)


@login_required
def api_kpis(request):
    kpis = EstadisticasService.get_kpis()
    kpis_serializable = {
        k: float(v) if isinstance(v, (int, float)) or hasattr(v, '__float__') else v
        for k, v in kpis.items()
    }
    return JsonResponse(kpis_serializable)


# ============================================================================
# DOCUMENTOS
# ============================================================================

from .models import Documento
from django.http import FileResponse
import mimetypes
import os


@login_required
def documentos_lista(request):
    documentos = Documento.objects.select_related(
        'poliza', 'siniestro', 'factura', 'subido_por'
    ).order_by('-fecha_subida')
    
    # Filtros
    tipo = request.GET.get('tipo')
    if tipo:
        documentos = documentos.filter(tipo_documento=tipo)
    
    query = request.GET.get('q')
    if query:
        documentos = documentos.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(poliza__numero_poliza__icontains=query) |
            Q(siniestro__numero_siniestro__icontains=query) |
            Q(factura__numero_factura__icontains=query)
        )
    
    # Paginación
    paginator = Paginator(documentos, 20)
    page = request.GET.get('page')
    documentos = paginator.get_page(page)
    
    context = {
        'documentos': documentos,
        'query': query or '',
        'tipo_filtro': tipo or '',
        'tipos_documento': Documento.TIPO_DOCUMENTO_CHOICES,
        'total_resultados': paginator.count,
    }
    
    return render(request, 'app/documentos/lista.html', context)


@login_required
def documento_ver(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    
    # Obtener información del archivo
    file_path = documento.archivo.path
    file_name = os.path.basename(documento.archivo.name)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Determinar el tipo de contenido
    content_type, _ = mimetypes.guess_type(file_path)
    
    # Categorizar el tipo de archivo para el template
    if file_ext in ['.pdf']:
        file_type = 'pdf'
    elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
        file_type = 'image'
    elif file_ext in ['.doc', '.docx']:
        file_type = 'word'
    elif file_ext in ['.xls', '.xlsx']:
        file_type = 'excel'
    elif file_ext in ['.txt', '.csv']:
        file_type = 'text'
    else:
        file_type = 'other'
    
    context = {
        'documento': documento,
        'file_type': file_type,
        'file_ext': file_ext,
        'content_type': content_type,
    }
    
    return render(request, 'app/documentos/ver.html', context)


@login_required
def documento_descargar(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    
    file_path = documento.archivo.path
    file_name = os.path.basename(documento.archivo.name)
    content_type, _ = mimetypes.guess_type(file_path)
    
    response = FileResponse(
        open(file_path, 'rb'),
        content_type=content_type or 'application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    
    return response


# ============================================================================
# BÚSQUEDA GLOBAL
# ============================================================================

from django.contrib import messages
from itertools import chain


@login_required
def busqueda_global(request):
    query = request.GET.get('q', '').strip()
    
    polizas = []
    facturas = []
    siniestros = []
    
    if query:
        polizas = Poliza.objects.filter(
            Q(numero_poliza__icontains=query) |
            Q(coberturas__icontains=query) |
            Q(observaciones__icontains=query) |
            Q(compania_aseguradora__nombre__icontains=query) |
            Q(corredor_seguros__nombre__icontains=query)
        ).select_related('compania_aseguradora', 'corredor_seguros', 'tipo_poliza')[:20]
        
        facturas = Factura.objects.filter(
            Q(numero_factura__icontains=query) |
            Q(concepto__icontains=query) |
            Q(poliza__numero_poliza__icontains=query)
        ).select_related('poliza')[:20]
        
        siniestros = Siniestro.objects.filter(
            Q(numero_siniestro__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(lugar_siniestro__icontains=query) |
            Q(poliza__numero_poliza__icontains=query)
        ).select_related('poliza', 'tipo_siniestro')[:20]
    
    context = {
        'query': query,
        'polizas': polizas,
        'facturas': facturas,
        'siniestros': siniestros,
        'total_resultados': len(polizas) + len(facturas) + len(siniestros),
    }
    
    return render(request, 'app/busqueda/resultados.html', context)


@login_required
def api_buscar(request):
    query = request.GET.get('q', '').strip()
    results = []
    
    if len(query) >= 2:
        try:
            # Buscar pólizas
            polizas = Poliza.objects.filter(
                Q(numero_poliza__icontains=query) |
                Q(compania_aseguradora__nombre__icontains=query) |
                Q(corredor_seguros__nombre__icontains=query)
            ).select_related('tipo_poliza', 'compania_aseguradora')[:5]
            
            for p in polizas:
                results.append({
                    'type': 'poliza',
                    'title': p.numero_poliza,
                    'subtitle': f'{p.compania_aseguradora.nombre} • {p.get_estado_display()}',
                    'url': f'/admin/app/poliza/{p.pk}/change/'
                })
            
            # Buscar facturas
            facturas = Factura.objects.filter(
                Q(numero_factura__icontains=query) |
                Q(concepto__icontains=query) |
                Q(poliza__numero_poliza__icontains=query)
            ).select_related('poliza')[:5]
            
            for f in facturas:
                monto = float(f.monto_total) if f.monto_total else 0
                results.append({
                    'type': 'factura',
                    'title': f.numero_factura,
                    'subtitle': f'${monto:,.2f} • {f.get_estado_display()}',
                    'url': f'/admin/app/factura/{f.pk}/change/'
                })
            
            # Buscar siniestros
            siniestros = Siniestro.objects.filter(
                Q(numero_siniestro__icontains=query) |
                Q(descripcion__icontains=query) |
                Q(poliza__numero_poliza__icontains=query)
            ).select_related('poliza')[:5]
            
            for s in siniestros:
                desc = s.descripcion[:40] + '...' if s.descripcion and len(s.descripcion) > 40 else (s.descripcion or 'Sin descripción')
                results.append({
                    'type': 'siniestro',
                    'title': s.numero_siniestro,
                    'subtitle': f'{s.get_estado_display()} • {desc}',
                    'url': f'/admin/app/siniestro/{s.pk}/change/'
                })
                
        except Exception as e:
            return JsonResponse({'results': [], 'error': str(e)}, status=200)
    
    return JsonResponse({'results': results})


# ============================================================================
# DASHBOARD ANALYTICS API
# ============================================================================

@login_required
@require_GET
def api_dashboard_summary(request):
    """
    Endpoint para obtener un resumen completo del dashboard.
    Parámetros:
        - period: Tipo de período (year, month, week, day)
    """
    period_type = request.GET.get('period', DashboardAnalyticsService.PERIOD_MONTH)
    if period_type not in DashboardAnalyticsService.PERIOD_CHOICES:
        period_type = DashboardAnalyticsService.PERIOD_MONTH
    
    summary = DashboardAnalyticsService.get_dashboard_summary(period_type)
    return JsonResponse(summary)


@login_required
@require_GET
def api_dashboard_comparative(request):
    """
    Endpoint para estadísticas comparativas entre períodos.
    Parámetros:
        - period: Tipo de período (year, month, week, day)
    """
    period_type = request.GET.get('period', DashboardAnalyticsService.PERIOD_MONTH)
    if period_type not in DashboardAnalyticsService.PERIOD_CHOICES:
        period_type = DashboardAnalyticsService.PERIOD_MONTH
    
    data = DashboardAnalyticsService.get_comparative_stats(period_type)
    return JsonResponse(data)


@login_required
@require_GET
def api_dashboard_trend(request):
    """
    Endpoint para datos de tendencia histórica.
    Parámetros:
        - period: Tipo de período (year, month, week, day)
        - count: Cantidad de períodos (default: 12)
    """
    period_type = request.GET.get('period', DashboardAnalyticsService.PERIOD_MONTH)
    if period_type not in DashboardAnalyticsService.PERIOD_CHOICES:
        period_type = DashboardAnalyticsService.PERIOD_MONTH
    
    try:
        periods_count = int(request.GET.get('count', 12))
        periods_count = min(max(periods_count, 1), 24)  # Entre 1 y 24 períodos
    except ValueError:
        periods_count = 12
    
    data = DashboardAnalyticsService.get_trend_data(period_type, periods_count)
    return JsonResponse(data)


@login_required
@require_GET
def api_dashboard_year_comparison(request):
    """
    Endpoint para comparación año a año.
    """
    data = DashboardAnalyticsService.get_year_over_year_comparison()
    return JsonResponse(data)


@login_required
@require_GET
def api_dashboard_filters(request):
    """
    Endpoint para obtener los filtros disponibles.
    Útil para poblar los selectores del frontend.
    """
    filters = DashboardFiltersService.get_available_filters()
    return JsonResponse(filters)


@login_required
@require_GET
def api_dashboard_filtered_stats(request):
    """
    Endpoint para obtener estadísticas filtradas.
    Soporta todos los filtros: fecha, compañía, corredor, tipo, estado.
    """
    filters = DashboardFiltersService.parse_filters_from_request(request)
    stats = DashboardFiltersService.get_filtered_stats(filters)
    return JsonResponse(stats)


@login_required
@require_GET
def api_dashboard_filtered_charts(request):
    """
    Endpoint para obtener datos de gráficos filtrados.
    """
    filters = DashboardFiltersService.parse_filters_from_request(request)
    charts = DashboardFiltersService.get_chart_data(filters)
    return JsonResponse(charts)


@login_required
@require_GET
def api_dashboard_filtered_lists(request):
    """
    Endpoint para obtener listas de registros filtrados.
    Parámetros:
        - limit: Cantidad máxima de registros (default: 5, max: 50)
    """
    filters = DashboardFiltersService.parse_filters_from_request(request)
    
    try:
        limit = int(request.GET.get('limit', 5))
        limit = min(max(limit, 1), 50)
    except ValueError:
        limit = 5
    
    lists = DashboardFiltersService.get_lists_data(filters, limit)
    return JsonResponse(lists)


@login_required
@require_GET
def api_dashboard_export(request):
    """
    Endpoint para exportar datos del dashboard en JSON.
    Útil para integraciones y reportes personalizados.
    """
    filters = DashboardFiltersService.parse_filters_from_request(request)
    export_data = DashboardFiltersService.export_filtered_data(filters)
    
    response = JsonResponse(export_data)
    response['Content-Disposition'] = 'attachment; filename="dashboard_export.json"'
    return response


# Vista personalizada de Login para manejar redirecciones inteligentes
class CustomLoginView(DjangoLoginView):
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        """
        Redirige al usuario según su origen:
        - Si viene del admin (/admin/) → redirige al admin
        - Si viene de la app web → redirige al dashboard
        - Si accede directamente → redirige al dashboard
        """
        # Obtener el parámetro 'next' de la URL
        next_url = self.request.GET.get('next', '')
        
        # Si hay un 'next' y es del admin, redirigir al admin
        if next_url and ('/admin/' in next_url or next_url.startswith('/admin')):
            return '/admin/'
        
        # Si hay un 'next' y no es del admin, usar ese
        if next_url and not next_url.startswith('/admin'):
            return next_url
        
        # Si no hay 'next', verificar el referer
        referer = self.request.META.get('HTTP_REFERER', '')
        if referer and '/admin/' in referer:
            return '/admin/'
        
        # Por defecto, redirigir al dashboard
        return reverse('dashboard')


# Vista personalizada de Logout que acepta GET
@login_required
def custom_logout(request):
    """
    Vista de logout que acepta tanto GET como POST.
    Hace logout del usuario y redirige al login.
    """
    logout(request)
    return redirect('login')


# =============================================================================
# VISTAS PARA NUEVOS MÓDULOS (Código en inglés, interfaz en español)
# =============================================================================

# --- RENOVACIONES DE PÓLIZAS ---

@login_required
def renewals_list(request):
    """Lista de renovaciones de pólizas con filtros"""
    renewals = PolicyRenewal.objects.select_related(
        'original_policy', 'original_policy__compania_aseguradora',
        'new_policy', 'quote', 'created_by'
    ).order_by('-due_date')
    
    # Filtros
    query = request.GET.get('q', '').strip()
    if query:
        renewals = renewals.filter(
            Q(renewal_number__icontains=query) |
            Q(original_policy__numero_poliza__icontains=query)
        )
    
    status = request.GET.get('status')
    if status:
        renewals = renewals.filter(status=status)
    
    decision = request.GET.get('decision')
    if decision:
        renewals = renewals.filter(decision=decision)
    
    # Paginación
    paginator = Paginator(renewals, 20)
    page = request.GET.get('page', 1)
    renewals_page = paginator.get_page(page)
    
    # Estadísticas
    stats = {
        'total': PolicyRenewal.objects.count(),
        'pending': PolicyRenewal.objects.filter(status='pending').count(),
        'in_progress': PolicyRenewal.objects.filter(status='in_progress').count(),
        'overdue': PolicyRenewal.objects.filter(
            status__in=['pending', 'in_progress'],
            due_date__lt=timezone.now().date()
        ).count(),
    }
    
    context = {
        'renewals': renewals_page,
        'stats': stats,
        'status_choices': PolicyRenewal.STATUS_CHOICES,
        'decision_choices': PolicyRenewal.DECISION_CHOICES,
        'query': query,
        'selected_status': status,
        'selected_decision': decision,
    }
    
    return render(request, 'app/renewals/list.html', context)


# --- COTIZACIONES ---

@login_required
def quotes_list(request):
    """Lista de cotizaciones con filtros"""
    quotes = Quote.objects.select_related(
        'policy_type', 'resulting_policy', 'requested_by'
    ).prefetch_related('options').order_by('-request_date')
    
    # Filtros
    query = request.GET.get('q', '').strip()
    if query:
        quotes = quotes.filter(
            Q(quote_number__icontains=query) |
            Q(title__icontains=query)
        )
    
    status = request.GET.get('status')
    if status:
        quotes = quotes.filter(status=status)
    
    priority = request.GET.get('priority')
    if priority:
        quotes = quotes.filter(priority=priority)
    
    # Paginación
    paginator = Paginator(quotes, 20)
    page = request.GET.get('page', 1)
    quotes_page = paginator.get_page(page)
    
    # Estadísticas
    stats = {
        'total': Quote.objects.count(),
        'draft': Quote.objects.filter(status='draft').count(),
        'sent': Quote.objects.filter(status='sent').count(),
        'accepted': Quote.objects.filter(status='accepted').count(),
        'converted': Quote.objects.filter(status='converted').count(),
    }
    
    context = {
        'quotes': quotes_page,
        'stats': stats,
        'status_choices': Quote.STATUS_CHOICES,
        'priority_choices': Quote.PRIORITY_CHOICES,
        'query': query,
        'selected_status': status,
        'selected_priority': priority,
    }
    
    return render(request, 'app/quotes/list.html', context)


# --- BIENES ASEGURADOS ---

@login_required
def assets_list(request):
    """Lista de bienes asegurados con filtros"""
    assets = InsuredAsset.objects.select_related(
        'policy', 'policy__compania_aseguradora', 'custodian', 'created_by'
    ).order_by('name')
    
    # Filtros
    query = request.GET.get('q', '').strip()
    if query:
        assets = assets.filter(
            Q(asset_code__icontains=query) |
            Q(name__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(brand__icontains=query)
        )
    
    status = request.GET.get('status')
    if status:
        assets = assets.filter(status=status)
    
    category = request.GET.get('category')
    if category:
        assets = assets.filter(category=category)
    
    covered = request.GET.get('covered')
    if covered == 'yes':
        assets = assets.filter(policy__isnull=False)
    elif covered == 'no':
        assets = assets.filter(policy__isnull=True)
    
    # Paginación
    paginator = Paginator(assets, 20)
    page = request.GET.get('page', 1)
    assets_page = paginator.get_page(page)
    
    # Estadísticas
    from django.db.models import Sum
    stats = {
        'total': InsuredAsset.objects.count(),
        'active': InsuredAsset.objects.filter(status='active').count(),
        'covered': InsuredAsset.objects.filter(policy__isnull=False).count(),
        'not_covered': InsuredAsset.objects.filter(policy__isnull=True).count(),
        'total_value': InsuredAsset.objects.aggregate(total=Sum('current_value'))['total'] or 0,
    }
    
    # Categorías únicas para el filtro
    categories = InsuredAsset.objects.values_list('category', flat=True).distinct().order_by('category')
    
    context = {
        'assets': assets_page,
        'stats': stats,
        'status_choices': InsuredAsset.STATUS_CHOICES,
        'categories': categories,
        'query': query,
        'selected_status': status,
        'selected_category': category,
        'selected_covered': covered,
    }
    
    return render(request, 'app/assets/list.html', context)


# --- CALENDARIO ---

@login_required
def calendar_view(request):
    """Vista del calendario interactivo"""
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    today = timezone.now().date()
    
    # Obtener eventos del mes actual y próximo
    start_range = today.replace(day=1) - timedelta(days=7)
    end_range = (today.replace(day=28) + timedelta(days=35)).replace(day=1) + timedelta(days=6)
    
    events = CalendarEvent.objects.filter(
        start_date__gte=start_range,
        start_date__lte=end_range
    ).select_related('policy', 'invoice', 'renewal', 'claim', 'quote')
    
    # Convertir eventos a formato para FullCalendar
    events_json = []
    for event in events:
        event_data = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat() if event.end_date else event.start_date.isoformat(),
            'color': event.color,
            'allDay': event.all_day,
            'extendedProps': {
                'type': event.event_type,
                'priority': event.priority,
                'description': event.description,
                'isCompleted': event.is_completed,
            }
        }
        if not event.all_day and event.start_time:
            event_data['start'] = f"{event.start_date.isoformat()}T{event.start_time.isoformat()}"
            if event.end_time:
                end_date = event.end_date or event.start_date
                event_data['end'] = f"{end_date.isoformat()}T{event.end_time.isoformat()}"
        events_json.append(event_data)
    
    # Próximos eventos (lista)
    upcoming_events = CalendarEvent.objects.filter(
        start_date__gte=today,
        is_completed=False
    ).order_by('start_date', 'start_time')[:10]
    
    # Eventos vencidos sin completar
    overdue_events = CalendarEvent.objects.filter(
        start_date__lt=today,
        is_completed=False
    ).order_by('-start_date')[:5]
    
    context = {
        'events_json': json.dumps(events_json),
        'upcoming_events': upcoming_events,
        'overdue_events': overdue_events,
        'event_type_choices': CalendarEvent.EVENT_TYPE_CHOICES,
        'priority_choices': CalendarEvent.PRIORITY_CHOICES,
        'today': today,
    }
    
    return render(request, 'app/calendar/view.html', context)


@login_required
@require_GET
def api_calendar_events(request):
    """API para obtener eventos del calendario (para FullCalendar)"""
    import json
    from datetime import datetime
    
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    events = CalendarEvent.objects.all()
    
    if start:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
        events = events.filter(start_date__gte=start_date)
    
    if end:
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00')).date()
        events = events.filter(start_date__lte=end_date)
    
    events_data = []
    for event in events:
        event_data = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': (event.end_date or event.start_date).isoformat(),
            'color': event.color,
            'allDay': event.all_day,
            'url': f'/admin/app/calendarevent/{event.id}/change/',
            'extendedProps': {
                'type': event.get_event_type_display(),
                'priority': event.get_priority_display(),
                'isCompleted': event.is_completed,
            }
        }
        events_data.append(event_data)
    
    return JsonResponse(events_data, safe=False)


@login_required
def generate_calendar_events(request):
    """Genera eventos automáticos del calendario basados en datos existentes"""
    from django.contrib import messages
    from django.utils import timezone
    
    today = timezone.now().date()
    created_count = 0
    
    # Generar eventos para pólizas por vencer
    expiring_policies = Poliza.objects.filter(
        estado__in=['vigente', 'por_vencer'],
        fecha_fin__gte=today,
        fecha_fin__lte=today + timezone.timedelta(days=60)
    )
    
    for policy in expiring_policies:
        event, created = CalendarEvent.objects.get_or_create(
            policy=policy,
            event_type='policy_expiry',
            defaults={
                'title': f'Vencimiento: {policy.numero_poliza}',
                'description': f'Vence la póliza {policy.numero_poliza} de {policy.compania_aseguradora}',
                'start_date': policy.fecha_fin,
                'priority': 'high' if (policy.fecha_fin - today).days <= 15 else 'medium',
                'is_auto_generated': True,
            }
        )
        if created:
            created_count += 1
    
    # Generar eventos para facturas por vencer
    pending_invoices = Factura.objects.filter(
        estado__in=['pendiente', 'parcial'],
        fecha_vencimiento__gte=today,
        fecha_vencimiento__lte=today + timezone.timedelta(days=30)
    )
    
    for invoice in pending_invoices:
        event, created = CalendarEvent.objects.get_or_create(
            invoice=invoice,
            event_type='invoice_due',
            defaults={
                'title': f'Vence factura: {invoice.numero_factura}',
                'description': f'Vence la factura {invoice.numero_factura} - ${invoice.saldo_pendiente:,.2f}',
                'start_date': invoice.fecha_vencimiento,
                'priority': 'high' if (invoice.fecha_vencimiento - today).days <= 7 else 'medium',
                'is_auto_generated': True,
            }
        )
        if created:
            created_count += 1
    
    # Generar eventos para renovaciones pendientes
    pending_renewals = PolicyRenewal.objects.filter(
        status__in=['pending', 'in_progress'],
        due_date__gte=today,
        due_date__lte=today + timezone.timedelta(days=45)
    )
    
    for renewal in pending_renewals:
        event, created = CalendarEvent.objects.get_or_create(
            renewal=renewal,
            event_type='renewal_due',
            defaults={
                'title': f'Renovación: {renewal.original_policy.numero_poliza}',
                'description': f'Fecha límite para renovar la póliza {renewal.original_policy.numero_poliza}',
                'start_date': renewal.due_date,
                'priority': 'critical' if (renewal.due_date - today).days <= 7 else 'high',
                'is_auto_generated': True,
            }
        )
        if created:
            created_count += 1
    
    messages.success(request, f'Se generaron {created_count} eventos automáticos.')
    return redirect('calendar_view')


# --- APROBACIONES DE PAGO ---

@login_required
def payment_approvals_list(request):
    """Lista de aprobaciones de pago pendientes"""
    approvals = PaymentApproval.objects.select_related(
        'payment', 'payment__factura', 'payment__factura__poliza', 'approver'
    ).order_by('-requested_at')
    
    # Filtros
    status = request.GET.get('status')
    if status:
        approvals = approvals.filter(status=status)
    else:
        # Por defecto mostrar solo pendientes
        approvals = approvals.filter(status='pending')
    
    level = request.GET.get('level')
    if level:
        approvals = approvals.filter(required_level=level)
    
    # Paginación
    paginator = Paginator(approvals, 20)
    page = request.GET.get('page', 1)
    approvals_page = paginator.get_page(page)
    
    # Estadísticas
    stats = {
        'pending': PaymentApproval.objects.filter(status='pending').count(),
        'approved_today': PaymentApproval.objects.filter(
            status='approved',
            decided_at__date=timezone.now().date()
        ).count(),
        'rejected_today': PaymentApproval.objects.filter(
            status='rejected',
            decided_at__date=timezone.now().date()
        ).count(),
    }
    
    context = {
        'approvals': approvals_page,
        'stats': stats,
        'status_choices': PaymentApproval.STATUS_CHOICES,
        'level_choices': PaymentApproval.APPROVAL_LEVEL_CHOICES,
        'selected_status': status or 'pending',
        'selected_level': level,
    }
    
    return render(request, 'app/approvals/list.html', context)


@login_required
@require_POST
def approve_payment(request, pk):
    """Aprobar un pago"""
    from django.contrib import messages
    
    approval = get_object_or_404(PaymentApproval, pk=pk)
    
    if approval.status != 'pending':
        messages.error(request, 'Esta aprobación ya fue procesada.')
        return redirect('payment_approvals_list')
    
    notes = request.POST.get('notes', '')
    approval.approve(request.user, notes)
    
    messages.success(request, f'Pago aprobado correctamente.')
    return redirect('payment_approvals_list')


@login_required
@require_POST
def reject_payment(request, pk):
    """Rechazar un pago"""
    from django.contrib import messages
    
    approval = get_object_or_404(PaymentApproval, pk=pk)
    
    if approval.status != 'pending':
        messages.error(request, 'Esta aprobación ya fue procesada.')
        return redirect('payment_approvals_list')
    
    notes = request.POST.get('notes', '')
    if not notes:
        messages.error(request, 'Debe proporcionar un motivo de rechazo.')
        return redirect('payment_approvals_list')
    
    approval.reject(request.user, notes)
    
    messages.warning(request, f'Pago rechazado.')
    return redirect('payment_approvals_list')


# =============================================================================
# DASHBOARD ESPECIALIZADO DE ANALYTICS
# =============================================================================

@login_required
def analytics_dashboard(request):
    """
    Dashboard especializado con analytics avanzados:
    - Ratio de siniestralidad por tipo de póliza
    - Tendencia indemnizaciones vs primas
    - Heatmap de ubicaciones
    - Predicción de renovación de primas
    """
    import json
    
    # Obtener datos del servicio
    summary = AdvancedAnalyticsService.get_dashboard_summary()
    loss_ratio_data = AdvancedAnalyticsService.get_loss_ratio_by_policy_type()
    trend_data = AdvancedAnalyticsService.get_claims_vs_premiums_trend(months=12)
    location_data = AdvancedAnalyticsService.get_claims_by_location()
    predictions = AdvancedAnalyticsService.predict_renewal_premium()
    claims_distribution = AdvancedAnalyticsService.get_claims_by_type_distribution()
    insurer_performance = AdvancedAnalyticsService.get_insurer_performance()
    
    context = {
        'summary': summary,
        'loss_ratio_data': loss_ratio_data,
        'trend_data_json': json.dumps(trend_data),
        'location_data': location_data,
        'location_data_json': json.dumps(location_data),
        'predictions': predictions,
        'claims_distribution_json': json.dumps(claims_distribution),
        'insurer_performance': insurer_performance,
    }
    
    return render(request, 'app/analytics/dashboard.html', context)


@login_required
@require_GET
def api_analytics_loss_ratio(request):
    """API para obtener ratio de siniestralidad"""
    data = AdvancedAnalyticsService.get_loss_ratio_by_policy_type()
    return JsonResponse({'data': data})


@login_required
@require_GET
def api_analytics_trend(request):
    """API para obtener tendencia de primas vs indemnizaciones"""
    months = int(request.GET.get('months', 12))
    data = AdvancedAnalyticsService.get_claims_vs_premiums_trend(months=months)
    return JsonResponse(data)


@login_required
@require_GET
def api_analytics_locations(request):
    """API para obtener datos de ubicaciones"""
    data = AdvancedAnalyticsService.get_claims_by_location()
    return JsonResponse({'data': data})


@login_required
@require_GET
def api_analytics_predictions(request):
    """API para obtener predicciones de renovación"""
    policy_id = request.GET.get('policy_id')
    if policy_id:
        data = AdvancedAnalyticsService.predict_renewal_premium(int(policy_id))
    else:
        data = AdvancedAnalyticsService.predict_renewal_premium()
    return JsonResponse(data)


@login_required
@require_GET
def api_analytics_insurers(request):
    """API para obtener rendimiento de aseguradoras"""
    data = AdvancedAnalyticsService.get_insurer_performance()
    return JsonResponse({'data': data})
