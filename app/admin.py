from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import (
    CompaniaAseguradora, CorredorSeguros, TipoPoliza, Poliza,
    Factura, Pago, TipoSiniestro, Siniestro, Documento, Alerta
)


@admin.register(CompaniaAseguradora)
class CompaniaAseguradoraAdmin(ModelAdmin):
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
class CorredorSegurosAdmin(ModelAdmin):
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
class TipoPolizaAdmin(ModelAdmin):
    list_display = ['nombre', 'descripcion', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']


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
class PolizaAdmin(ModelAdmin):
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
class FacturaAdmin(ModelAdmin):
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
        return format_html(
            '<span style="color: {}; font-weight: bold;">${:,.2f}</span>',
            color,
            saldo
        )

    @display(description='¿Puede Aplicar Descuento?', boolean=True)
    def puede_aplicar_descuento_display(self, obj):
        return obj.puede_aplicar_descuento

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo registro
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Pago)
class PagoAdmin(ModelAdmin):
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
class TipoSiniestroAdmin(ModelAdmin):
    list_display = ['nombre', 'descripcion', 'activo']
    list_filter = ['activo', 'nombre']
    search_fields = ['nombre', 'descripcion']


@admin.register(Siniestro)
class SiniestroAdmin(ModelAdmin):
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
        'poliza__compania_aseguradora'
    ]
    search_fields = [
        'numero_siniestro',
        'bien_nombre',
        'bien_codigo_activo',
        'responsable_custodio',
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
class DocumentoAdmin(ModelAdmin):
    list_display = [
        'nombre',
        'tipo_documento',
        'poliza',
        'siniestro',
        'factura',
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
    readonly_fields = ['fecha_subida', 'subido_por']
    date_hierarchy = 'fecha_subida'
    
    fieldsets = (
        ('Información del Documento', {
            'fields': ('tipo_documento', 'nombre', 'descripcion', 'archivo')
        }),
        ('Relaciones', {
            'fields': ('poliza', 'siniestro', 'factura')
        }),
        ('Auditoría', {
            'fields': ('subido_por', 'fecha_subida'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo registro
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Alerta)
class AlertaAdmin(ModelAdmin):
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
