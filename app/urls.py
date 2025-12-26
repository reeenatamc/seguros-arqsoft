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
]
