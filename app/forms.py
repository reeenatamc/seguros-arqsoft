"""
Formularios Custom para el Sistema de Seguros.
Formularios Django para gestión de pólizas, siniestros, ramos y bienes asegurados.
"""

from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import (
    Poliza, DetallePolizaRamo, Ramo, SubtipoRamo,
    Siniestro, AdjuntoSiniestro, ChecklistSiniestro, ChecklistSiniestroConfig,
    GrupoBienes, InsuredAsset, Factura, Documento, Pago,
    CompaniaAseguradora, CorredorSeguros, TipoPoliza, TipoSiniestro,
    ResponsableCustodio, NotaCredito
)


# ==============================================================================
# WIDGETS PERSONALIZADOS
# ==============================================================================

class DateInput(forms.DateInput):
    """Widget de fecha con type=date para navegadores modernos"""
    input_type = 'date'

    def __init__(self, *args, **kwargs):
        # Formato compatible con inputs HTML date (YYYY-MM-DD)
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(*args, **kwargs)


class DateTimeInput(forms.DateTimeInput):
    """Widget de datetime-local para navegadores modernos"""
    input_type = 'datetime-local'

    # Formato compatible con inputs HTML datetime-local
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%dT%H:%M')
        super().__init__(*args, **kwargs)


# ==============================================================================
# FORMULARIOS DE RAMOS
# ==============================================================================

class RamoForm(forms.ModelForm):
    """Formulario para crear/editar ramos"""

    class Meta:
        model = Ramo
        fields = ['codigo', 'nombre', 'descripcion', 'activo']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: INC, ROB, VLI',
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del ramo',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del ramo (opcional)',
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').upper()
        if Ramo.objects.filter(codigo=codigo).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe un ramo con este código.')
        return codigo


class SubtipoRamoForm(forms.ModelForm):
    """Formulario para crear/editar subtipos de ramo"""

    class Meta:
        model = SubtipoRamo
        fields = ['ramo', 'codigo', 'nombre', 'descripcion', 'activo']
        widgets = {
            'ramo': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ==============================================================================
# FORMULARIOS DE PÓLIZA
# ==============================================================================

class PolizaForm(forms.ModelForm):
    """Formulario principal para crear/editar pólizas"""

    class Meta:
        model = Poliza
        fields = [
            'numero_poliza', 'compania_aseguradora', 'corredor_seguros',
            'tipo_poliza', 'suma_asegurada', 'coberturas',
            'fecha_inicio', 'fecha_fin', 'estado',
            'es_gran_contribuyente', 'observaciones',
        ]
        widgets = {
            'numero_poliza': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de póliza',
            }),
            'compania_aseguradora': forms.Select(attrs={
                'class': 'form-select',
            }),
            'corredor_seguros': forms.Select(attrs={
                'class': 'form-select',
            }),
            'tipo_poliza': forms.Select(attrs={
                'class': 'form-select',
            }),
            'suma_asegurada': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'coberturas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detalle de las coberturas de la póliza',
            }),
            'fecha_inicio': DateInput(attrs={'class': 'form-control'}),
            'fecha_fin': DateInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'es_gran_contribuyente': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales (opcional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo compañías y corredores activos
        self.fields['compania_aseguradora'].queryset = CompaniaAseguradora.objects.filter(activo=True)
        self.fields['corredor_seguros'].queryset = CorredorSeguros.objects.filter(activo=True)
        self.fields['tipo_poliza'].queryset = TipoPoliza.objects.filter(activo=True)

        # Si se selecciona una compañía, limitar los brokers al convenio con esa aseguradora
        compania = None
        if 'compania_aseguradora' in self.data:
            try:
                compania_id = int(self.data.get('compania_aseguradora'))
                compania = CompaniaAseguradora.objects.filter(activo=True).get(pk=compania_id)
            except (TypeError, ValueError, CompaniaAseguradora.DoesNotExist):
                compania = None
        elif self.instance.pk and self.instance.compania_aseguradora_id:
            compania = self.instance.compania_aseguradora

        if compania and compania.brokers.exists():
            self.fields['corredor_seguros'].queryset = compania.brokers.filter(activo=True)

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if fecha_inicio and fecha_fin:
            if fecha_inicio >= fecha_fin:
                raise ValidationError({
                    'fecha_fin': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })

        return cleaned_data


class DetallePolizaRamoForm(forms.ModelForm):
    """Formulario para detalle de póliza por ramo"""

    class Meta:
        model = DetallePolizaRamo
        fields = [
            'ramo', 'subtipo_ramo', 'numero_factura', 'documento_contable',
            'suma_asegurada', 'total_prima', 'emision', 'observaciones',
        ]
        widgets = {
            'ramo': forms.Select(attrs={'class': 'form-select ramo-select'}),
            'subtipo_ramo': forms.Select(attrs={'class': 'form-select'}),
            'numero_factura': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'N° Factura',
            }),
            'documento_contable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Doc. Contable',
            }),
            'suma_asegurada': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'total_prima': forms.NumberInput(attrs={
                'class': 'form-control prima-input',
                'step': '0.01',
                'min': '0',
            }),
            'emision': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Siempre limitar los ramos a los activos
        self.fields['ramo'].queryset = Ramo.objects.filter(activo=True)

        # Por defecto, no obligamos el subgrupo y restringimos su queryset
        self.fields['subtipo_ramo'].required = False
        self.fields['subtipo_ramo'].queryქვამset = SubtipoRamo.objects.none()

        # Si viene un ramo en el POST, limitar los subgrupos a ese ramo
        if 'ramo' in self.data:
            try:
                ramo_id = int(self.data.get('ramo'))
                self.fields['subtipo_ramo'].queryset = SubtipoRamo.objects.filter(
                    ramo_id=ramo_id, activo=True
                ).order_by('nombre')
            except (ValueError, TypeError):
                # Si algo falla en el parseo, dejamos queryset vacío
                pass
        elif self.instance.pk and self.instance.ramo_id:
            # En edición, mostrar solo los subgrupos del ramo ya asociado
            self.fields['subtipo_ramo'].queryset = SubtipoRamo.objects.filter(
                ramo=self.instance.ramo, activo=True
            ).order_by('nombre')

    def clean_subtipo_ramo(self):
        """
        Garantiza que el subgrupo seleccionado pertenezca al grupo (ramo) elegido.
        """
        subtipo = self.cleaned_data.get('subtipo_ramo')
        ramo = self.cleaned_data.get('ramo')

        if subtipo and ramo and subtipo.ramo_id != ramo.id:
            raise ValidationError(
                "El subgrupo seleccionado no pertenece al grupo (ramo) escogido."
            )

        return subtipo


# Formset para detalles de ramo en póliza
DetallePolizaRamoFormSet = inlineformset_factory(
    Poliza,
    DetallePolizaRamo,
    form=DetallePolizaRamoForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


# ==============================================================================
# FORMULARIOS DE SINIESTRO
# ==============================================================================

class SiniestroForm(forms.ModelForm):
    """Formulario principal para crear/editar siniestros"""

    class Meta:
        model = Siniestro
        fields = [
            'poliza', 'numero_siniestro', 'tipo_siniestro',
            'fecha_siniestro', 'ubicacion', 'causa', 'descripcion_detallada',
            'bien_nombre', 'bien_marca', 'bien_modelo', 'bien_serie', 'bien_codigo_activo',
            'responsable_custodio', 'monto_estimado',
            'valor_reclamo', 'deducible', 'depreciacion', 'suma_asegurada_bien',
            'email_broker', 'observaciones',
        ]
        widgets = {
            'poliza': forms.Select(attrs={'class': 'form-select'}),
            'numero_siniestro': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de siniestro',
            }),
            'tipo_siniestro': forms.Select(attrs={'class': 'form-select'}),
            'fecha_siniestro': DateTimeInput(
                attrs={'class': 'form-control'},
            ),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ubicación del siniestro',
            }),
            'causa': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Causa del siniestro',
            }),
            'descripcion_detallada': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción detallada del siniestro',
            }),
            'bien_nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del bien afectado',
            }),
            'bien_marca': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Marca',
            }),
            'bien_modelo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Modelo',
            }),
            'bien_serie': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de serie',
            }),
            'bien_codigo_activo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código de activo',
            }),
            'responsable_custodio': forms.Select(attrs={'class': 'form-select'}),
            'monto_estimado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'valor_reclamo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'deducible': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'depreciacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'suma_asegurada_bien': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'email_broker': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@broker.com',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Obtener la instancia actual si existe (modo edición)
        instance = getattr(self, 'instance', None)

        # Polizas: incluir vigentes/por_vencer + la póliza actual si existe
        polizas_qs = Poliza.objects.filter(
            estado__in=['vigente', 'por_vencer']
        ).select_related('compania_aseguradora')
        
        if instance and instance.poliza_id:
            # Incluir la póliza actual aunque tenga otro estado
            polizas_qs = polizas_qs | Poliza.objects.filter(pk=instance.poliza_id)
        
        self.fields['poliza'].queryset = polizas_qs.distinct()
        
        # Tipos de siniestro: activos + el actual si existe
        tipos_qs = TipoSiniestro.objects.filter(activo=True)
        if instance and instance.tipo_siniestro_id:
            tipos_qs = tipos_qs | TipoSiniestro.objects.filter(pk=instance.tipo_siniestro_id)
        self.fields['tipo_siniestro'].queryset = tipos_qs.distinct()
        
        # Responsables: activos + el actual si existe
        responsables_qs = ResponsableCustodio.objects.filter(activo=True)
        if instance and instance.responsable_custodio_id:
            responsables_qs = responsables_qs | ResponsableCustodio.objects.filter(pk=instance.responsable_custodio_id)
        self.fields['responsable_custodio'].queryset = responsables_qs.distinct()

        # Prefill del email del broker desde la póliza cuando sea posible
        # Solo si el campo está vacío para no pisar cambios manuales
        try:
            if not (instance and instance.email_broker):
                poliza_obj = None
                if 'poliza' in self.data:
                    poliza_id = self.data.get('poliza')
                    if poliza_id:
                        poliza_obj = Poliza.objects.select_related('corredor_seguros').filter(pk=poliza_id).first()
                elif instance and instance.poliza_id:
                    poliza_obj = instance.poliza

                if poliza_obj and poliza_obj.corredor_seguros and poliza_obj.corredor_seguros.email:
                    self.fields['email_broker'].initial = poliza_obj.corredor_seguros.email
        except Exception:
            # Prefill es best-effort; no debe romper el formulario si algo falla
            pass

        # Asegurar que el campo fecha_siniestro use formatos compatibles con datetime-local
        # para que se muestre correctamente al editar y acepte el valor enviado.
        self.fields['fecha_siniestro'].input_formats = [
            '%Y-%m-%dT%H:%M',      # formato de input datetime-local
            '%Y-%m-%d %H:%M:%S',   # formato que Django suele guardar
            '%Y-%m-%d %H:%M',      # variante sin segundos
        ]

        # Campos opcionales
        for field in ['valor_reclamo', 'deducible', 'depreciacion', 'suma_asegurada_bien', 'email_broker']:
            self.fields[field].required = False


class SiniestroGestionForm(forms.ModelForm):
    """Formulario para gestión de estado de siniestro"""

    class Meta:
        model = Siniestro
        fields = [
            'estado', 'fecha_envio_aseguradora', 'fecha_respuesta_aseguradora',
            'monto_indemnizado', 'fecha_liquidacion',
            'fecha_firma_indemnizacion', 'valor_pagado', 'fecha_pago',
            'observaciones',
        ]
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_envio_aseguradora': DateInput(attrs={'class': 'form-control'}),
            'fecha_respuesta_aseguradora': DateInput(attrs={'class': 'form-control'}),
            'monto_indemnizado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'fecha_liquidacion': DateInput(attrs={'class': 'form-control'}),
            'fecha_firma_indemnizacion': DateTimeInput(attrs={'class': 'form-control'}),
            'valor_pagado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
            }),
            'fecha_pago': DateInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Formatos compatibles para todos los campos de fecha / fecha-hora
        date_formats = ['%Y-%m-%d']
        datetime_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']

        self.fields['fecha_envio_aseguradora'].input_formats = date_formats
        self.fields['fecha_respuesta_aseguradora'].input_formats = date_formats
        self.fields['fecha_liquidacion'].input_formats = date_formats
        self.fields['fecha_pago'].input_formats = date_formats
        self.fields['fecha_firma_indemnizacion'].input_formats = datetime_formats


class AdjuntoSiniestroForm(forms.ModelForm):
    """Formulario para adjuntos de siniestro"""

    class Meta:
        model = AdjuntoSiniestro
        fields = ['tipo_adjunto', 'nombre', 'descripcion', 'archivo', 'requiere_firma']
        widgets = {
            'tipo_adjunto': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del documento',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descripción (opcional)',
            }),
            'archivo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'requiere_firma': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


# Formset para adjuntos de siniestro
AdjuntoSiniestroFormSet = inlineformset_factory(
    Siniestro,
    AdjuntoSiniestro,
    form=AdjuntoSiniestroForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class ChecklistSiniestroForm(forms.ModelForm):
    """Formulario para items de checklist de siniestro"""

    class Meta:
        model = ChecklistSiniestro
        fields = ['completado', 'observaciones']
        widgets = {
            'completado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Observaciones',
            }),
        }


# ==============================================================================
# FORMULARIOS DE BIENES ASEGURADOS
# ==============================================================================

class GrupoBienesForm(forms.ModelForm):
    """Formulario para crear/editar grupos de bienes"""

    class Meta:
        model = GrupoBienes
        fields = ['nombre', 'descripcion', 'ramo', 'subtipo_ramo', 'responsable', 'poliza', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del grupo',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
            'ramo': forms.Select(attrs={'class': 'form-select'}),
            'subtipo_ramo': forms.Select(attrs={'class': 'form-select'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
            'poliza': forms.Select(attrs={'class': 'form-select'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ramo'].queryset = Ramo.objects.filter(activo=True)
        self.fields['subtipo_ramo'].required = False
        self.fields['responsable'].queryset = ResponsableCustodio.objects.filter(activo=True)
        self.fields['responsable'].required = False
        self.fields['poliza'].queryset = Poliza.objects.filter(estado__in=['vigente', 'por_vencer'])
        self.fields['poliza'].required = False


class BienAseguradoForm(forms.ModelForm):
    """Formulario para crear/editar bienes asegurados"""

    class Meta:
        model = InsuredAsset
        fields = [
            'asset_code', 'name', 'description', 'category',
            'brand', 'model', 'serial_number',
            'location', 'building', 'floor', 'department',
            'purchase_value', 'current_value', 'insured_value',
            'purchase_date', 'warranty_expiry',
            'status', 'condition',
            'policy', 'custodian', 'grupo',
            'notes',
        ]
        widgets = {
            'asset_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código de activo único',
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del bien',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Categoría',
            }),
            'brand': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Marca',
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Modelo',
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de serie',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ubicación',
            }),
            'building': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Edificio',
            }),
            'floor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Piso',
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Departamento',
            }),
            'purchase_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'current_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'insured_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'purchase_date': DateInput(attrs={'class': 'form-control'}),
            'warranty_expiry': DateInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'policy': forms.Select(attrs={'class': 'form-select'}),
            'custodian': forms.Select(attrs={'class': 'form-select'}),
            'grupo': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['policy'].queryset = Poliza.objects.filter(
            estado__in=['vigente', 'por_vencer']
        ).select_related('compania_aseguradora')
        self.fields['policy'].required = False
        self.fields['custodian'].queryset = ResponsableCustodio.objects.filter(activo=True)
        self.fields['grupo'].queryset = GrupoBienes.objects.filter(activo=True)
        self.fields['grupo'].required = False
        self.fields['insured_value'].required = False
        self.fields['warranty_expiry'].required = False


# ==============================================================================
# FORMULARIOS DE FACTURA
# ==============================================================================

class FacturaForm(forms.ModelForm):
    """Formulario para crear/editar facturas"""

    class Meta:
        model = Factura
        fields = [
            'poliza', 'numero_factura', 'fecha_emision', 'fecha_vencimiento',
            'subtotal', 'iva', 'contribucion_superintendencia',
            'contribucion_seguro_campesino', 'retenciones', 'descuento_pronto_pago',
            'monto_total', 'estado',
        ]
        widgets = {
            'poliza': forms.Select(attrs={'class': 'form-select'}),
            'numero_factura': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de factura',
            }),
            'fecha_emision': DateInput(attrs={'class': 'form-control'}),
            'fecha_vencimiento': DateInput(attrs={'class': 'form-control'}),
            'subtotal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'iva': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'contribucion_superintendencia': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'contribucion_seguro_campesino': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'retenciones': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'descuento_pronto_pago': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'monto_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['poliza'].queryset = Poliza.objects.filter(
            estado__in=['vigente', 'por_vencer']
        ).select_related('compania_aseguradora')


# ==============================================================================
# FORMULARIOS DE DOCUMENTO
# ==============================================================================

class DocumentoForm(forms.ModelForm):
    """Formulario para crear/editar documentos"""

    class Meta:
        model = Documento
        fields = [
            'nombre', 'tipo_documento', 'archivo', 'descripcion',
            'poliza', 'siniestro', 'factura',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del documento',
            }),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del documento',
            }),
            'poliza': forms.Select(attrs={'class': 'form-select'}),
            'siniestro': forms.Select(attrs={'class': 'form-select'}),
            'factura': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['poliza'].queryset = Poliza.objects.all()
        self.fields['poliza'].required = False
        self.fields['siniestro'].queryset = Siniestro.objects.all()
        self.fields['siniestro'].required = False
        self.fields['factura'].queryset = Factura.objects.all()
        self.fields['factura'].required = False


# ==============================================================================
# FORMULARIOS DE PAGO
# ==============================================================================

class PagoForm(forms.ModelForm):
    """Formulario para crear/editar pagos"""

    class Meta:
        model = Pago
        fields = [
            'factura', 'monto', 'fecha_pago', 'forma_pago',
            'referencia', 'observaciones',
        ]
        widgets = {
            'factura': forms.Select(attrs={'class': 'form-select'}),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
            }),
            'fecha_pago': DateInput(attrs={'class': 'form-control'}),
            'forma_pago': forms.Select(attrs={'class': 'form-select'}),
            'referencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de referencia o comprobante',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['factura'].queryset = Factura.objects.filter(
            estado__in=['pendiente', 'parcial', 'vencida']
        )


# ==============================================================================
# FORMULARIOS DE NOTA DE CRÉDITO
# ==============================================================================

class NotaCreditoForm(forms.ModelForm):
    """Formulario para crear/editar notas de crédito"""

    class Meta:
        model = NotaCredito
        fields = ['factura', 'numero', 'fecha_emision', 'monto', 'motivo', 'documento']
        widgets = {
            'factura': forms.Select(attrs={'class': 'form-select'}),
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de nota de crédito',
            }),
            'fecha_emision': DateInput(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
            }),
            'motivo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Motivo de la nota de crédito',
            }),
            'documento': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }


# ==============================================================================
# FORMULARIOS DE CONFIGURACIÓN DE CHECKLIST
# ==============================================================================

class ChecklistSiniestroConfigForm(forms.ModelForm):
    """Formulario para configurar items de checklist por tipo de siniestro"""

    class Meta:
        model = ChecklistSiniestroConfig
        fields = ['tipo_siniestro', 'nombre', 'descripcion', 'es_obligatorio', 'orden', 'activo']
        widgets = {
            'tipo_siniestro': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del item',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
            }),
            'es_obligatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'orden': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_siniestro'].queryset = TipoSiniestro.objects.filter(activo=True)


# ==============================================================================
# FORMULARIOS DE FILTROS Y BÚSQUEDA
# ==============================================================================

class FiltroPolizasForm(forms.Form):
    """Formulario de filtros para lista de pólizas"""

    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + list(Poliza.ESTADO_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    compania = forms.ModelChoiceField(
        queryset=CompaniaAseguradora.objects.filter(activo=True),
        required=False,
        empty_label='Todas las compañías',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    tipo = forms.ModelChoiceField(
        queryset=TipoPoliza.objects.filter(activo=True),
        required=False,
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'}),
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'}),
    )


class FiltroSiniestrosForm(forms.Form):
    """Formulario de filtros para lista de siniestros"""

    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + list(Siniestro.ESTADO_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    tipo = forms.ModelChoiceField(
        queryset=TipoSiniestro.objects.filter(activo=True),
        required=False,
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'}),
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=DateInput(attrs={'class': 'form-control'}),
    )


class FiltroReportesForm(forms.Form):
    """Formulario de filtros para reportes"""

    fecha_desde = forms.DateField(
        required=True,
        widget=DateInput(attrs={'class': 'form-control'}),
        label='Fecha desde',
    )
    fecha_hasta = forms.DateField(
        required=True,
        widget=DateInput(attrs={'class': 'form-control'}),
        label='Fecha hasta',
    )
    compania = forms.ModelChoiceField(
        queryset=CompaniaAseguradora.objects.filter(activo=True),
        required=False,
        empty_label='Todas las compañías',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    tipo_poliza = forms.ModelChoiceField(
        queryset=TipoPoliza.objects.filter(activo=True),
        required=False,
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
