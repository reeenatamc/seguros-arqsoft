from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Pólizas
    path("polizas/", views.polizas_lista, name="polizas_lista"),
    path("polizas/exportar/", views.polizas_exportar, name="polizas_exportar"),
    # Desglose por Ramos
    path("desglose-ramos/", views.desglose_ramos_lista, name="desglose_ramos_lista"),
    path("desglose-ramos/exportar/", views.desglose_ramos_exportar, name="desglose_ramos_exportar"),
    # Facturas
    path("facturas/", views.facturas_lista, name="facturas_lista"),
    path("facturas/crear/", views.FacturaCreateView.as_view(), name="factura_crear"),
    path("facturas/<int:pk>/", views.FacturaDetailView.as_view(), name="factura_detalle"),
    path("facturas/<int:pk>/editar/", views.FacturaUpdateView.as_view(), name="factura_editar"),
    path("facturas/exportar/", views.facturas_exportar, name="facturas_exportar"),
    # Siniestros
    path("siniestros/", views.siniestros_lista, name="siniestros_lista"),
    path("siniestros/exportar/", views.siniestros_exportar, name="siniestros_exportar"),
    path("siniestros/email-pendientes/", views.siniestros_email_pendientes, name="siniestros_email_pendientes"),
    path(
        "siniestros/email/<int:pk>/procesar-auto/",
        views.siniestro_email_procesar_auto,
        name="siniestro_email_procesar_auto",
    ),
    path("siniestros/email/<int:pk>/completar/", views.siniestro_email_completar, name="siniestro_email_completar"),
    path("api/siniestros/email/count/", views.siniestros_email_count, name="siniestros_email_count"),
    # Alertas
    path("alertas/", views.alertas_lista, name="alertas_lista"),
    path("alertas/<int:pk>/leida/", views.alerta_marcar_leida, name="alerta_marcar_leida"),
    # Reportes
    path("reportes/", views.reportes_dashboard, name="reportes_dashboard"),
    path("reportes/polizas/", views.reportes_polizas, name="reportes_polizas"),
    path("reportes/polizas/pdf/", views.reportes_polizas_pdf, name="reportes_polizas_pdf"),
    path("reportes/siniestros/", views.reportes_siniestros, name="reportes_siniestros"),
    path("reportes/siniestros/pdf/", views.reportes_siniestros_pdf, name="reportes_siniestros_pdf"),
    path("reportes/facturas/pdf/", views.reportes_facturas_pdf, name="reportes_facturas_pdf"),
    path("reportes/ejecutivo/pdf/", views.reportes_ejecutivo_pdf, name="reportes_ejecutivo_pdf"),
    # Documentos
    path("documentos/", views.documentos_lista, name="documentos_lista"),
    path("documentos/crear/", views.DocumentoCreateView.as_view(), name="documento_crear"),
    path("documentos/<int:pk>/ver/", views.documento_ver, name="documento_ver"),
    path("documentos/<int:pk>/editar/", views.DocumentoUpdateView.as_view(), name="documento_editar"),
    path("documentos/<int:pk>/descargar/", views.documento_descargar, name="documento_descargar"),
    # Pagos
    path("pagos/crear/", views.PagoCreateView.as_view(), name="pago_crear"),
    path("pagos/<int:pk>/", views.PagoDetailView.as_view(), name="pago_detalle"),
    path("pagos/<int:pk>/editar/", views.PagoUpdateView.as_view(), name="pago_editar"),
    # Búsqueda Global
    path("buscar/", views.busqueda_global, name="busqueda_global"),
    # API endpoints
    path("api/stats/", views.api_stats, name="api_stats"),
    path("api/kpis/", views.api_kpis, name="api_kpis"),
    path("api/buscar/", views.api_buscar, name="api_buscar"),
    # Dashboard Analytics API
    path("api/dashboard/summary/", views.api_dashboard_summary, name="api_dashboard_summary"),
    path("api/dashboard/comparative/", views.api_dashboard_comparative, name="api_dashboard_comparative"),
    path("api/dashboard/trend/", views.api_dashboard_trend, name="api_dashboard_trend"),
    path("api/dashboard/year-comparison/", views.api_dashboard_year_comparison, name="api_dashboard_year_comparison"),
    # Dashboard Filters API (estilo Odoo)
    path("api/dashboard/filters/", views.api_dashboard_filters, name="api_dashboard_filters"),
    path("api/dashboard/filtered-stats/", views.api_dashboard_filtered_stats, name="api_dashboard_filtered_stats"),
    path("api/dashboard/filtered-charts/", views.api_dashboard_filtered_charts, name="api_dashboard_filtered_charts"),
    path("api/dashboard/filtered-lists/", views.api_dashboard_filtered_lists, name="api_dashboard_filtered_lists"),
    path("api/dashboard/export/", views.api_dashboard_export, name="api_dashboard_export"),
    # Renovaciones de Pólizas
    path("renovaciones/", views.renewals_list, name="renewals_list"),
    # Cotizaciones
    path("cotizaciones/", views.quotes_list, name="quotes_list"),
    # Bienes Asegurados
    path("bienes/", views.assets_list, name="assets_list"),
    # Calendario
    path("calendario/", views.calendar_view, name="calendar_view"),
    path("calendario/generar-eventos/", views.generate_calendar_events, name="generate_calendar_events"),
    path("api/calendario/eventos/", views.api_calendar_events, name="api_calendar_events"),
    # Aprobaciones de Pago
    path("aprobaciones/", views.payment_approvals_list, name="payment_approvals_list"),
    path("aprobaciones/<int:pk>/aprobar/", views.approve_payment, name="approve_payment"),
    path("aprobaciones/<int:pk>/rechazar/", views.reject_payment, name="reject_payment"),
    # Dashboard Analytics Especializado
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("api/analytics/loss-ratio/", views.api_analytics_loss_ratio, name="api_analytics_loss_ratio"),
    path("api/analytics/trend/", views.api_analytics_trend, name="api_analytics_trend"),
    path("api/analytics/locations/", views.api_analytics_locations, name="api_analytics_locations"),
    path("api/analytics/insurers/", views.api_analytics_insurers, name="api_analytics_insurers"),
    # =========================================================================
    # NUEVAS RUTAS - CREACIÓN RÁPIDA DE ENTIDADES (para popups)
    # =========================================================================
    # Compañías Aseguradoras
    path("aseguradoras/crear/", views.CompaniaAseguradoraCreateView.as_view(), name="aseguradora_crear"),
    # Corredores de Seguros
    path("corredores/crear/", views.CorredorSegurosCreateView.as_view(), name="corredor_crear"),
    # Tipos de Siniestro
    path("tipos-siniestro/crear/", views.TipoSiniestroCreateView.as_view(), name="tipo_siniestro_crear"),
    # Responsables/Custodios
    path("responsables/crear/", views.ResponsableCustodioCreateView.as_view(), name="responsable_crear"),
    # =========================================================================
    # SISTEMA DE RAMOS
    # =========================================================================
    # Ramos (Grupos de Ramo)
    path("ramos/", views.RamoListView.as_view(), name="ramos_lista"),
    path("ramos/crear/", views.RamoCreateView.as_view(), name="ramo_crear"),
    path("ramos/<int:pk>/editar/", views.RamoUpdateView.as_view(), name="ramo_editar"),
    path("ramos/inicializar/", views.inicializar_ramos_predefinidos, name="ramos_inicializar"),
    # Pólizas - CRUD Completo
    path("polizas/crear/", views.PolizaCreateView.as_view(), name="poliza_crear"),
    path("polizas/<int:pk>/", views.PolizaDetailView.as_view(), name="poliza_detalle"),
    path("polizas/<int:pk>/editar/", views.PolizaUpdateView.as_view(), name="poliza_editar"),
    # Siniestros - CRUD Completo
    path("siniestros/crear/", views.SiniestroCreateView.as_view(), name="siniestro_crear"),
    path("siniestros/<int:pk>/", views.SiniestroDetailView.as_view(), name="siniestro_detalle"),
    path("siniestros/<int:pk>/editar/", views.SiniestroUpdateView.as_view(), name="siniestro_editar"),
    # Acciones de Siniestros
    path("siniestros/<int:pk>/notificar-broker/", views.siniestro_notificar_broker, name="siniestro_notificar_broker"),
    path(
        "siniestros/<int:siniestro_pk>/checklist/<int:item_pk>/completar/",
        views.siniestro_marcar_checklist,
        name="siniestro_marcar_checklist",
    ),
    path("siniestros/<int:pk>/descargar-carta/", views.siniestro_descargar_carta, name="siniestro_descargar_carta"),
    path("siniestros/<int:pk>/descargar-recibo/", views.siniestro_descargar_recibo, name="siniestro_descargar_recibo"),
    path("siniestros/<int:pk>/subir-adjunto/", views.siniestro_subir_adjunto, name="siniestro_subir_adjunto"),
    path(
        "siniestros/<int:pk>/enviar-aseguradora/",
        views.siniestro_enviar_aseguradora,
        name="siniestro_enviar_aseguradora",
    ),
    # Adjuntos
    path("adjuntos/<int:pk>/firmar/", views.adjunto_firmar, name="adjunto_firmar"),
    # Grupos de Bienes
    path("grupos-bienes/", views.GrupoBienesListView.as_view(), name="grupos_bienes_lista"),
    path("grupos-bienes/crear/", views.GrupoBienesCreateView.as_view(), name="grupo_bienes_crear"),
    path("grupos-bienes/<int:pk>/", views.GrupoBienesDetailView.as_view(), name="grupo_bienes_detalle"),
    # Bienes Asegurados - CRUD
    path("bienes/crear/", views.BienAseguradoCreateView.as_view(), name="bien_asegurado_crear"),
    path("bienes/<int:pk>/", views.BienAseguradoDetailView.as_view(), name="bien_asegurado_detalle"),
    path("bienes/<int:pk>/editar/", views.BienAseguradoUpdateView.as_view(), name="bien_asegurado_editar"),
    # Reportes Avanzados
    path("reportes/siniestralidad/", views.reporte_siniestralidad, name="reporte_siniestralidad"),
    path("reportes/gasto-ramos/", views.reporte_gasto_ramos, name="reporte_gasto_ramos"),
    path("reportes/dias-gestion/", views.reporte_dias_gestion, name="reporte_dias_gestion"),
    path(
        "reportes/siniestros-dependencia/", views.reporte_siniestros_dependencia, name="reporte_siniestros_dependencia"
    ),
    # APIs Adicionales
    path("api/subtipos-ramo/", views.api_subtipos_ramo, name="api_subtipos_ramo"),
    path("api/corredores-por-compania/", views.api_corredores_por_compania, name="api_corredores_por_compania"),
    path("api/calcular-desglose-ramo/", views.api_calcular_desglose_ramo, name="api_calcular_desglose_ramo"),
    path("api/reporte-siniestralidad/", views.api_reporte_siniestralidad, name="api_reporte_siniestralidad"),
    # Configuración del Sistema
    path("configuracion/", views.configuracion_lista, name="configuracion_lista"),
    path("configuracion/<int:pk>/editar/", views.configuracion_editar, name="configuracion_editar"),
    path("configuracion/categoria/<str:categoria>/", views.configuracion_categoria, name="configuracion_categoria"),
    path("configuracion/restablecer/", views.configuracion_restablecer, name="configuracion_restablecer"),
    # Respaldos y Recuperación
    path("backups/", views.backups_lista, name="backups_lista"),
    path("backups/crear/", views.backup_crear, name="backup_crear"),
    path("backups/<int:pk>/descargar/", views.backup_descargar, name="backup_descargar"),
    path("backups/<int:pk>/eliminar/", views.backup_eliminar, name="backup_eliminar"),
    path("backups/<int:pk>/restaurar/", views.backup_restaurar, name="backup_restaurar"),
    path("backups/configuracion/", views.backup_configuracion, name="backup_configuracion"),
]
