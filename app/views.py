from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET, require_POST
from django.urls import reverse

from .models import Poliza, Factura, Siniestro, Alerta, CompaniaAseguradora, TipoPoliza, TipoSiniestro, CorredorSeguros
from .services import EstadisticasService, ExportacionService, ReportesService
from .services.pdf_reportes import PDFReportesService


@login_required
def dashboard(request):
    stats = EstadisticasService.get_dashboard_stats()
    kpis = EstadisticasService.get_kpis()
    polizas_por_vencer = EstadisticasService.get_polizas_proximas_vencer(dias=30, limit=5)
    facturas_pendientes = EstadisticasService.get_facturas_pendientes(limit=5)
    siniestros_recientes = EstadisticasService.get_siniestros_recientes(limit=5)
    
    graficos_polizas = ReportesService.get_datos_graficos_polizas()
    graficos_polizas_tipo = ReportesService.get_datos_graficos_polizas_por_tipo()
    graficos_facturas = ReportesService.get_datos_graficos_facturas()
    graficos_facturacion = ReportesService.get_datos_graficos_facturacion_mensual()
    graficos_siniestros = ReportesService.get_datos_graficos_siniestros_mensual()
    graficos_siniestros_tipo = ReportesService.get_datos_graficos_siniestros_por_tipo()
    graficos_comparativo = ReportesService.get_datos_graficos_comparativo()
    
    context = {
        'stats': stats,
        'kpis': kpis,
        'polizas_por_vencer': polizas_por_vencer,
        'facturas_pendientes': facturas_pendientes,
        'siniestros_recientes': siniestros_recientes,
        'graficos_polizas': graficos_polizas,
        'graficos_polizas_tipo': graficos_polizas_tipo,
        'graficos_facturas': graficos_facturas,
        'graficos_facturacion': graficos_facturacion,
        'graficos_siniestros': graficos_siniestros,
        'graficos_siniestros_tipo': graficos_siniestros_tipo,
        'graficos_comparativo': graficos_comparativo,
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
