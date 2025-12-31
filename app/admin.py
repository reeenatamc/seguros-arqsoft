from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from simple_history.admin import SimpleHistoryAdmin
from import_export import resources, fields
from import_export.admin import ImportExportMixin
from import_export.widgets import ForeignKeyWidget, DateWidget, DateTimeWidget
from .models import (
    ConfiguracionSistema, CompaniaAseguradora, CorredorSeguros, TipoPoliza, 
    ResponsableCustodio, Poliza, Factura, Pago, TipoSiniestro, Siniestro, Documento, Alerta
)


# =============================================================================
# RECURSOS DE IMPORTACIÓN/EXPORTACIÓN
# =============================================================================

class CompaniaAseguradoraResource(resources.ModelResource):
    class Meta:
        model = CompaniaAseguradora
        import_id_fields = ['ruc']
        fields = ('nombre', 'ruc', 'direccion', 'telefono', 'email', 'contacto_principal', 'activa')
        export_order = fields


class CorredorSegurosResource(resources.ModelResource):
    class Meta:
        model = CorredorSeguros
        import_id_fields = ['ruc']
        fields = ('nombre', 'ruc', 'direccion', 'telefono', 'email', 'contacto_nombre', 'activo')
        export_order = fields


class TipoPolizaResource(resources.ModelResource):
    class Meta:
        model = TipoPoliza
        import_id_fields = ['nombre']
        fields = ('nombre', 'descripcion', 'activo')


class TipoSiniestroResource(resources.ModelResource):
    class Meta:
        model = TipoSiniestro
        import_id_fields = ['nombre']
        fields = ('nombre', 'descripcion', 'activo')


class PolizaResource(resources.ModelResource):
    compania_aseguradora = fields.Field(
        column_name='compania_aseguradora',
        attribute='compania_aseguradora',
        widget=ForeignKeyWidget(CompaniaAseguradora, 'nombre')
    )
    corredor_seguros = fields.Field(
        column_name='corredor_seguros',
        attribute='corredor_seguros',
        widget=ForeignKeyWidget(CorredorSeguros, 'nombre')
    )
    tipo_poliza = fields.Field(
        column_name='tipo_poliza',
        attribute='tipo_poliza',
        widget=ForeignKeyWidget(TipoPoliza, 'nombre')
    )
    fecha_inicio = fields.Field(
        column_name='fecha_inicio',
        attribute='fecha_inicio',
        widget=DateWidget(format='%Y-%m-%d')
    )
    fecha_fin = fields.Field(
        column_name='fecha_fin',
        attribute='fecha_fin',
        widget=DateWidget(format='%Y-%m-%d')
    )
    
    class Meta:
        model = Poliza
        import_id_fields = ['numero_poliza']
        fields = ('numero_poliza', 'compania_aseguradora', 'corredor_seguros', 'tipo_poliza',
                  'suma_asegurada', 'coberturas', 'fecha_inicio', 'fecha_fin', 'estado', 'observaciones')
        export_order = fields


class FacturaResource(resources.ModelResource):
    poliza = fields.Field(
        column_name='poliza',
        attribute='poliza',
        widget=ForeignKeyWidget(Poliza, 'numero_poliza')
    )
    fecha_emision = fields.Field(
        column_name='fecha_emision',
        attribute='fecha_emision',
        widget=DateWidget(format='%Y-%m-%d')
    )
    fecha_vencimiento = fields.Field(
        column_name='fecha_vencimiento',
        attribute='fecha_vencimiento',
        widget=DateWidget(format='%Y-%m-%d')
    )
    
    class Meta:
        model = Factura
        import_id_fields = ['numero_factura']
        fields = ('numero_factura', 'poliza', 'fecha_emision', 'fecha_vencimiento',
                  'subtotal', 'iva', 'monto_total', 'concepto', 'estado')
        export_order = fields


class SiniestroResource(resources.ModelResource):
    poliza = fields.Field(
        column_name='poliza',
        attribute='poliza',
        widget=ForeignKeyWidget(Poliza, 'numero_poliza')
    )
    tipo_siniestro = fields.Field(
        column_name='tipo_siniestro',
        attribute='tipo_siniestro',
        widget=ForeignKeyWidget(TipoSiniestro, 'nombre')
    )
    fecha_siniestro = fields.Field(
        column_name='fecha_siniestro',
        attribute='fecha_siniestro',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )
    
    class Meta:
        model = Siniestro
        import_id_fields = ['numero_siniestro']
        fields = ('numero_siniestro', 'poliza', 'tipo_siniestro', 'fecha_siniestro',
                  'descripcion', 'lugar_siniestro', 'monto_estimado', 'monto_indemnizado', 'estado')
        export_order = fields


class HistoryModelAdmin(ImportExportMixin, ModelAdmin, SimpleHistoryAdmin):
    """
    Clase base que combina Unfold ModelAdmin con SimpleHistoryAdmin e ImportExportMixin
    para modelos que tienen auditoría de cambios y soporte de importación/exportación.
    """
    history_list_display = ['changed_fields', 'history_user']
    
    def changed_fields(self, obj):
        """Muestra los campos que cambiaron."""
        if obj.prev_record:
            delta = obj.diff_against(obj.prev_record)
            changed = [change.field for change in delta.changes]
            if changed:
                return ', '.join(changed)
        return 'Creación inicial'
    changed_fields.short_description = 'Campos modificados'


class ImportExportModelAdmin(ImportExportMixin, ModelAdmin):
    """
    Clase base que combina Unfold ModelAdmin con ImportExportMixin
    para modelos sin historial pero con soporte de importación/exportación.
    """
    pass


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(ModelAdmin):
    icon_name = "settings"
    list_display = ['clave', 'valor', 'tipo', 'categoria', 'descripcion_corta']
    list_filter = ['categoria', 'tipo']
    search_fields = ['clave', 'descripcion']
    list_editable = ['valor']
    
    fieldsets = (
        ('Configuración', {
            'fields': ('clave', 'valor', 'tipo')
        }),
        ('Clasificación', {
            'fields': ('categoria', 'descripcion')
        }),
    )
    
    def descripcion_corta(self, obj):
        if len(obj.descripcion) > 50:
            return obj.descripcion[:50] + '...'
        return obj.descripcion
    descripcion_corta.short_description = 'Descripción'
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CompaniaAseguradora)
class CompaniaAseguradoraAdmin(ImportExportModelAdmin):
    icon_name = "business"
    resource_class = CompaniaAseguradoraResource
    list_display = ['nombre', 'ruc', 'telefono', 'email', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'ruc', 'email', 'contacto_nombre']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'ruc', 'activo')
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email', 'contacto_nombre', 'contacto_telefono')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CorredorSeguros)
class CorredorSegurosAdmin(ImportExportModelAdmin):
    icon_name = "handshake"
    resource_class = CorredorSegurosResource
    list_display = ['nombre', 'ruc', 'telefono', 'email', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre', 'ruc', 'email', 'contacto_nombre']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'ruc', 'activo')
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email', 'contacto_nombre', 'contacto_telefono')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TipoPoliza)
class TipoPolizaAdmin(ImportExportModelAdmin):
    icon_name = "category"
    resource_class = TipoPolizaResource
    list_display = ['nombre', 'descripcion', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']


@admin.register(ResponsableCustodio)
class ResponsableCustodioAdmin(ImportExportModelAdmin):
    icon_name = "person"
    list_display = ['nombre', 'cargo', 'departamento', 'email', 'telefono', 'activo']
    list_filter = ['activo', 'departamento']
    search_fields = ['nombre', 'cargo', 'departamento', 'email']
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'cargo', 'departamento')
        }),
        ('Contacto', {
            'fields': ('email', 'telefono')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']


class DocumentoInline(TabularInline):
    model = Documento
    extra = 0
    fields = ['tipo_documento', 'nombre', 'archivo', 'fecha_subida']
    readonly_fields = ['fecha_subida']


class FacturaInline(TabularInline):
    model = Factura
    extra = 0
    fields = ['numero_factura', 'fecha_emision', 'monto_total', 'estado']
    readonly_fields = ['monto_total']


class SiniestroInline(TabularInline):
    model = Siniestro
    extra = 0
    fields = ['numero_siniestro', 'tipo_siniestro', 'fecha_siniestro', 'estado']


@admin.register(Poliza)
class PolizaAdmin(HistoryModelAdmin):
    icon_name = "verified"
    resource_class = PolizaResource
    list_display = [
        'numero_poliza', 
        'compania_aseguradora', 
        'tipo_poliza', 
        'suma_asegurada_formatted',
        'fecha_inicio', 
        'fecha_fin',
        'estado_badge',
        'dias_vencer'
    ]
    list_filter = [
        'estado', 
        'compania_aseguradora', 
        'tipo_poliza', 
        'fecha_inicio',
        'fecha_fin'
    ]
    search_fields = [
        'numero_poliza', 
        'compania_aseguradora__nombre', 
        'corredor_seguros__nombre',
        'coberturas'
    ]
    readonly_fields = [
        'estado', 
        'fecha_creacion', 
        'fecha_modificacion', 
        'creado_por',
        'dias_para_vencer_display',
        'esta_vigente_display'
    ]
    date_hierarchy = 'fecha_inicio'
    inlines = [DocumentoInline, FacturaInline, SiniestroInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_poliza', 'compania_aseguradora', 'corredor_seguros', 'tipo_poliza')
        }),
        ('Coberturas y Montos', {
            'fields': ('suma_asegurada', 'coberturas')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio', 'fecha_fin', 'estado', 'dias_para_vencer_display', 'esta_vigente_display')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    @display(description='Suma Asegurada', ordering='suma_asegurada')
    def suma_asegurada_formatted(self, obj):
        return f"${obj.suma_asegurada:,.2f}"

    @display(description='Estado', ordering='estado')
    def estado_badge(self, obj):
        colors = {
            'vigente': 'green',
            'vencida': 'red',
            'cancelada': 'gray',
            'por_vencer': 'orange'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )

    @display(description='Días para Vencer')
    def dias_vencer(self, obj):
        dias = obj.dias_para_vencer
        if dias > 30:
            color = 'green'
        elif dias > 0:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} días</span>',
            color,
            dias
        )

    @display(description='Días para Vencer')
    def dias_para_vencer_display(self, obj):
        return f"{obj.dias_para_vencer} días"

    @display(description='¿Está Vigente?', boolean=True)
    def esta_vigente_display(self, obj):
        return obj.esta_vigente

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo registro
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


class PagoInline(TabularInline):
    model = Pago
    extra = 0
    fields = ['fecha_pago', 'monto', 'forma_pago', 'referencia', 'estado']


@admin.register(Factura)
class FacturaAdmin(HistoryModelAdmin):
    icon_name = "receipt"
    resource_class = FacturaResource
    list_display = [
        'numero_factura',
        'poliza',
        'fecha_emision',
        'fecha_vencimiento',
        'subtotal_formatted',
        'monto_total_formatted',
        'estado_badge',
        'saldo_pendiente_display'
    ]
    list_filter = [
        'estado',
        'fecha_emision',
        'fecha_vencimiento',
        'poliza__compania_aseguradora'
    ]
    search_fields = [
        'numero_factura',
        'poliza__numero_poliza',
        'poliza__compania_aseguradora__nombre'
    ]
    readonly_fields = [
        'contribucion_superintendencia',
        'contribucion_seguro_campesino',
        'descuento_pronto_pago',
        'monto_total',
        'estado',
        'fecha_creacion',
        'fecha_modificacion',
        'creado_por',
        'saldo_pendiente_display',
        'puede_aplicar_descuento_display'
    ]
    date_hierarchy = 'fecha_emision'
    inlines = [PagoInline, DocumentoInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('poliza', 'numero_factura', 'fecha_emision', 'fecha_vencimiento')
        }),
        ('Montos', {
            'fields': (
                'subtotal',
                'iva',
                'contribucion_superintendencia',
                'contribucion_seguro_campesino',
                'retenciones',
                'descuento_pronto_pago',
                'monto_total'
            )
        }),
        ('Estado y Descuentos', {
            'fields': ('estado', 'saldo_pendiente_display', 'puede_aplicar_descuento_display')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    @display(description='Subtotal', ordering='subtotal')
    def subtotal_formatted(self, obj):
        return f"${obj.subtotal:,.2f}"

    @display(description='Monto Total', ordering='monto_total')
    def monto_total_formatted(self, obj):
        return f"${obj.monto_total:,.2f}"

    @display(description='Estado', ordering='estado')
    def estado_badge(self, obj):
        colors = {
            'pendiente': 'orange',
            'pagada': 'green',
            'parcial': 'blue',
            'vencida': 'red'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )

    @display(description='Saldo Pendiente')
    def saldo_pendiente_display(self, obj):
        saldo = obj.saldo_pendiente
        color = 'green' if saldo == 0 else 'red'
        saldo_formatted = f"${saldo:,.2f}"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            saldo_formatted
        )

    @display(description='¿Puede Aplicar Descuento?', boolean=True)
    def puede_aplicar_descuento_display(self, obj):
        return obj.puede_aplicar_descuento

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo registro
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Pago)
class PagoAdmin(HistoryModelAdmin):
    icon_name = "payments"
    list_display = [
        'referencia',
        'factura',
        'fecha_pago',
        'monto_formatted',
        'forma_pago',
        'estado_badge'
    ]
    list_filter = [
        'estado',
        'forma_pago',
        'fecha_pago'
    ]
    search_fields = [
        'referencia',
        'factura__numero_factura',
        'factura__poliza__numero_poliza'
    ]
    readonly_fields = ['fecha_creacion', 'registrado_por']
    date_hierarchy = 'fecha_pago'
    
    fieldsets = (
        ('Información del Pago', {
            'fields': ('factura', 'fecha_pago', 'monto', 'forma_pago', 'referencia')
        }),
        ('Estado', {
            'fields': ('estado', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('registrado_por', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )

    @display(description='Monto', ordering='monto')
    def monto_formatted(self, obj):
        return f"${obj.monto:,.2f}"

    @display(description='Estado', ordering='estado')
    def estado_badge(self, obj):
        colors = {
            'pendiente': 'orange',
            'aprobado': 'green',
            'rechazado': 'red'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo registro
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(TipoSiniestro)
class TipoSiniestroAdmin(ImportExportModelAdmin):
    icon_name = "label"
    resource_class = TipoSiniestroResource
    list_display = ['nombre', 'descripcion', 'activo']
    list_filter = ['activo', 'nombre']
    search_fields = ['nombre', 'descripcion']


@admin.register(Siniestro)
class SiniestroAdmin(HistoryModelAdmin):
    icon_name = "warning"
    resource_class = SiniestroResource
    list_display = [
        'numero_siniestro',
        'tipo_siniestro',
        'bien_nombre',
        'poliza',
        'fecha_siniestro',
        'monto_estimado_formatted',
        'estado_badge',
        'dias_desde_registro_display',
        'alerta_documentacion',
        'alerta_respuesta'
    ]
    list_filter = [
        'estado',
        'tipo_siniestro',
        'fecha_siniestro',
        'poliza__compania_aseguradora',
        'responsable_custodio'
    ]
    search_fields = [
        'numero_siniestro',
        'bien_nombre',
        'bien_codigo_activo',
        'responsable_custodio__nombre',
        'responsable_custodio__departamento',
        'poliza__numero_poliza'
    ]
    readonly_fields = [
        'fecha_registro',
        'fecha_modificacion',
        'creado_por',
        'dias_desde_registro_display',
        'requiere_alerta_documentacion_display',
        'dias_espera_respuesta_display',
        'requiere_alerta_respuesta_display'
    ]
    date_hierarchy = 'fecha_siniestro'
    inlines = [DocumentoInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_siniestro', 'poliza', 'tipo_siniestro', 'fecha_siniestro')
        }),
        ('Bien Asegurado', {
            'fields': (
                'bien_nombre',
                'bien_modelo',
                'bien_serie',
                'bien_marca',
                'bien_codigo_activo'
            )
        }),
        ('Detalles del Siniestro', {
            'fields': (
                'responsable_custodio',
                'ubicacion',
                'causa',
                'descripcion_detallada'
            )
        }),
        ('Montos', {
            'fields': ('monto_estimado', 'monto_indemnizado')
        }),
        ('Estado y Gestión', {
            'fields': (
                'estado',
                'fecha_envio_aseguradora',
                'fecha_respuesta_aseguradora',
                'fecha_liquidacion',
                'dias_desde_registro_display',
                'requiere_alerta_documentacion_display',
                'dias_espera_respuesta_display',
                'requiere_alerta_respuesta_display'
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_registro', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    @display(description='Monto Estimado', ordering='monto_estimado')
    def monto_estimado_formatted(self, obj):
        return f"${obj.monto_estimado:,.2f}"

    @display(description='Estado', ordering='estado')
    def estado_badge(self, obj):
        colors = {
            'registrado': 'blue',
            'documentacion_pendiente': 'orange',
            'enviado_aseguradora': 'purple',
            'en_evaluacion': 'teal',
            'aprobado': 'green',
            'rechazado': 'red',
            'liquidado': 'darkgreen',
            'cerrado': 'gray'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_estado_display()
        )

    @display(description='Días desde Registro')
    def dias_desde_registro_display(self, obj):
        dias = obj.dias_desde_registro
        color = 'green' if dias < 30 else 'orange' if dias < 60 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} días</span>',
            color,
            dias
        )

    @display(description='⚠️ Doc', boolean=True)
    def alerta_documentacion(self, obj):
        return obj.requiere_alerta_documentacion

    @display(description='⚠️ Resp', boolean=True)
    def alerta_respuesta(self, obj):
        return obj.requiere_alerta_respuesta

    @display(description='Requiere Alerta Documentación', boolean=True)
    def requiere_alerta_documentacion_display(self, obj):
        return obj.requiere_alerta_documentacion

    @display(description='Días Espera Respuesta')
    def dias_espera_respuesta_display(self, obj):
        dias = obj.dias_espera_respuesta
        if dias > 0:
            color = 'orange' if dias <= 8 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} días</span>',
                color,
                dias
            )
        return "N/A"

    @display(description='Requiere Alerta Respuesta', boolean=True)
    def requiere_alerta_respuesta_display(self, obj):
        return obj.requiere_alerta_respuesta

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo registro
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Documento)
class DocumentoAdmin(HistoryModelAdmin):
    icon_name = "description"
    list_display = [
        'nombre',
        'tipo_documento',
        'acciones_documento',
        'poliza',
        'siniestro',
        'factura',
        'tamanio_display',
        'fecha_subida',
        'subido_por'
    ]
    list_filter = [
        'tipo_documento',
        'fecha_subida'
    ]
    search_fields = [
        'nombre',
        'descripcion',
        'poliza__numero_poliza',
        'siniestro__numero_siniestro',
        'factura__numero_factura'
    ]
    readonly_fields = ['fecha_subida', 'subido_por', 'preview_documento']
    date_hierarchy = 'fecha_subida'
    
    fieldsets = (
        ('Información del Documento', {
            'fields': ('tipo_documento', 'nombre', 'descripcion', 'archivo', 'preview_documento')
        }),
        ('Relaciones', {
            'fields': ('poliza', 'siniestro', 'factura')
        }),
        ('Auditoría', {
            'fields': ('subido_por', 'fecha_subida'),
            'classes': ('collapse',)
        }),
    )
    
    @display(description="Acciones", ordering="archivo")
    def acciones_documento(self, obj):
        if obj.archivo:
            return format_html(
                '<a href="/documentos/{}/ver/" class="text-primary-600 hover:text-primary-700 mr-3" '
                'title="Ver documento"><i class="fas fa-eye"></i></a>'
                '<a href="/documentos/{}/descargar/" class="text-emerald-600 hover:text-emerald-700" '
                'title="Descargar"><i class="fas fa-download"></i></a>',
                obj.pk, obj.pk
            )
        return "-"
    
    @display(description="Tamaño")
    def tamanio_display(self, obj):
        return obj.tamanio_formateado
    
    @display(description="Vista Previa")
    def preview_documento(self, obj):
        if not obj.archivo:
            return "Sin archivo"
        
        ext = obj.extension.lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return format_html(
                '<div style="max-width: 400px;">'
                '<img src="{}" style="max-width: 100%; max-height: 300px; border-radius: 8px; '
                'box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />'
                '<div style="margin-top: 10px;">'
                '<a href="/documentos/{}/ver/" class="button" style="margin-right: 8px;">Ver completo</a>'
                '<a href="/documentos/{}/descargar/" class="button">Descargar</a>'
                '</div></div>',
                obj.archivo.url, obj.pk, obj.pk
            )
        elif ext == '.pdf':
            return format_html(
                '<div style="max-width: 600px;">'
                '<iframe src="{}" width="100%" height="400" style="border: 1px solid #e5e7eb; '
                'border-radius: 8px;"></iframe>'
                '<div style="margin-top: 10px;">'
                '<a href="/documentos/{}/ver/" class="button" style="margin-right: 8px;">Ver en visor</a>'
                '<a href="/documentos/{}/descargar/" class="button">Descargar</a>'
                '</div></div>',
                obj.archivo.url, obj.pk, obj.pk
            )
        else:
            icon_class = 'fa-file'
            icon_color = '#64748b'
            if ext in ['.doc', '.docx']:
                icon_class = 'fa-file-word'
                icon_color = '#2563eb'
            elif ext in ['.xls', '.xlsx']:
                icon_class = 'fa-file-excel'
                icon_color = '#059669'
            
            return format_html(
                '<div style="text-align: center; padding: 20px; background: #f8fafc; '
                'border-radius: 8px; max-width: 300px;">'
                '<i class="fas {} fa-3x" style="color: {};"></i>'
                '<p style="margin: 10px 0; color: #64748b;">Vista previa no disponible</p>'
                '<a href="/documentos/{}/descargar/" class="button">Descargar archivo</a>'
                '</div>',
                icon_class, icon_color, obj.pk
            )

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo registro
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Alerta)
class AlertaAdmin(ModelAdmin):
    icon_name = "notifications"
    list_display = [
        'titulo',
        'tipo_alerta',
        'poliza',
        'factura',
        'siniestro',
        'estado_badge',
        'fecha_creacion',
        'fecha_envio'
    ]
    list_filter = [
        'tipo_alerta',
        'estado',
        'fecha_creacion'
    ]
    search_fields = [
        'titulo',
        'mensaje',
        'poliza__numero_poliza',
        'factura__numero_factura',
        'siniestro__numero_siniestro'
    ]
    readonly_fields = ['fecha_creacion', 'fecha_envio', 'fecha_lectura']
    date_hierarchy = 'fecha_creacion'
    filter_horizontal = ['destinatarios']
    
    fieldsets = (
        ('Información de la Alerta', {
            'fields': ('tipo_alerta', 'titulo', 'mensaje', 'estado')
        }),
        ('Relaciones', {
            'fields': ('poliza', 'factura', 'siniestro')
        }),
        ('Destinatarios', {
            'fields': ('destinatarios',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_envio', 'fecha_lectura'),
            'classes': ('collapse',)
        }),
    )

    @display(description='Estado', ordering='estado')
    def estado_badge(self, obj):
        colors = {
            'pendiente': 'orange',
            'enviada': 'blue',
            'leida': 'purple',
            'atendida': 'green'
        }
        color = colors.get(obj.estado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )

    actions = ['marcar_como_enviadas', 'marcar_como_leidas']

    @admin.action(description='Marcar como enviadas')
    def marcar_como_enviadas(self, request, queryset):
        for alerta in queryset:
            alerta.marcar_como_enviada()
        self.message_user(request, f"{queryset.count()} alertas marcadas como enviadas.")

    @admin.action(description='Marcar como leídas')
    def marcar_como_leidas(self, request, queryset):
        for alerta in queryset:
            alerta.marcar_como_leida()
        self.message_user(request, f"{queryset.count()} alertas marcadas como leídas.")
