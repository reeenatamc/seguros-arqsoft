from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Pólizas
    path('polizas/', views.polizas_lista, name='polizas_lista'),
    path('polizas/exportar/', views.polizas_exportar, name='polizas_exportar'),
    
    # Facturas
    path('facturas/', views.facturas_lista, name='facturas_lista'),
    path('facturas/exportar/', views.facturas_exportar, name='facturas_exportar'),
    
    # Siniestros
    path('siniestros/', views.siniestros_lista, name='siniestros_lista'),
    path('siniestros/exportar/', views.siniestros_exportar, name='siniestros_exportar'),
    
    # Alertas
    path('alertas/', views.alertas_lista, name='alertas_lista'),
    path('alertas/<int:pk>/leida/', views.alerta_marcar_leida, name='alerta_marcar_leida'),
    
    # Reportes
    path('reportes/', views.reportes_dashboard, name='reportes_dashboard'),
    path('reportes/polizas/', views.reportes_polizas, name='reportes_polizas'),
    path('reportes/polizas/pdf/', views.reportes_polizas_pdf, name='reportes_polizas_pdf'),
    path('reportes/siniestros/', views.reportes_siniestros, name='reportes_siniestros'),
    path('reportes/siniestros/pdf/', views.reportes_siniestros_pdf, name='reportes_siniestros_pdf'),
    path('reportes/facturas/pdf/', views.reportes_facturas_pdf, name='reportes_facturas_pdf'),
    path('reportes/ejecutivo/pdf/', views.reportes_ejecutivo_pdf, name='reportes_ejecutivo_pdf'),
    
    # Documentos
    path('documentos/', views.documentos_lista, name='documentos_lista'),
    path('documentos/<int:pk>/ver/', views.documento_ver, name='documento_ver'),
    path('documentos/<int:pk>/descargar/', views.documento_descargar, name='documento_descargar'),
    
    # Búsqueda Global
    path('buscar/', views.busqueda_global, name='busqueda_global'),
    
    # API endpoints
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/kpis/', views.api_kpis, name='api_kpis'),
    path('api/buscar/', views.api_buscar, name='api_buscar'),
    
    # Dashboard Analytics API
    path('api/dashboard/summary/', views.api_dashboard_summary, name='api_dashboard_summary'),
    path('api/dashboard/comparative/', views.api_dashboard_comparative, name='api_dashboard_comparative'),
    path('api/dashboard/trend/', views.api_dashboard_trend, name='api_dashboard_trend'),
    path('api/dashboard/year-comparison/', views.api_dashboard_year_comparison, name='api_dashboard_year_comparison'),
    
    # Dashboard Filters API (estilo Odoo)
    path('api/dashboard/filters/', views.api_dashboard_filters, name='api_dashboard_filters'),
    path('api/dashboard/filtered-stats/', views.api_dashboard_filtered_stats, name='api_dashboard_filtered_stats'),
    path('api/dashboard/filtered-charts/', views.api_dashboard_filtered_charts, name='api_dashboard_filtered_charts'),
    path('api/dashboard/filtered-lists/', views.api_dashboard_filtered_lists, name='api_dashboard_filtered_lists'),
    path('api/dashboard/export/', views.api_dashboard_export, name='api_dashboard_export'),
    
    # Renovaciones de Pólizas
    path('renovaciones/', views.renewals_list, name='renewals_list'),
    
    # Cotizaciones
    path('cotizaciones/', views.quotes_list, name='quotes_list'),
    
    # Bienes Asegurados
    path('bienes/', views.assets_list, name='assets_list'),
    
    # Calendario
    path('calendario/', views.calendar_view, name='calendar_view'),
    path('calendario/generar-eventos/', views.generate_calendar_events, name='generate_calendar_events'),
    path('api/calendario/eventos/', views.api_calendar_events, name='api_calendar_events'),
    
    # Aprobaciones de Pago
    path('aprobaciones/', views.payment_approvals_list, name='payment_approvals_list'),
    path('aprobaciones/<int:pk>/aprobar/', views.approve_payment, name='approve_payment'),
    path('aprobaciones/<int:pk>/rechazar/', views.reject_payment, name='reject_payment'),
    
    # Dashboard Analytics Especializado
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('api/analytics/loss-ratio/', views.api_analytics_loss_ratio, name='api_analytics_loss_ratio'),
    path('api/analytics/trend/', views.api_analytics_trend, name='api_analytics_trend'),
    path('api/analytics/locations/', views.api_analytics_locations, name='api_analytics_locations'),
    path('api/analytics/predictions/', views.api_analytics_predictions, name='api_analytics_predictions'),
    path('api/analytics/insurers/', views.api_analytics_insurers, name='api_analytics_insurers'),
]
