"""

Formularios Custom para el Sistema de Seguros.

Formularios Django para gestión de pólizas, siniestros, ramos y bienes asegurados.

"""


from django import forms

from django.forms import inlineformset_factory

from django.core.exceptions import ValidationError

from decimal import Decimal


from .models import (

    Poliza, DetallePolizaRamo,

    TipoRamo, GrupoRamo, SubgrupoRamo, BienAsegurado,

    # Alias de compatibilidad (deprecados)

    Ramo, SubtipoRamo,

    Siniestro, AdjuntoSiniestro, ChecklistSiniestro, ChecklistSiniestroConfig,

    GrupoBienes, Factura, Documento, Pago,

    CompaniaAseguradora, CorredorSeguros, TipoPoliza, TipoSiniestro,

    ResponsableCustodio, NotaCredito, ConfiguracionSistema

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

# FORMULARIOS DE ENTIDADES BASE (Compañías, Corredores, etc.)

# ==============================================================================


class CompaniaAseguradoraForm(forms.ModelForm):

    """Formulario para crear/editar compañías aseguradoras"""

    class Meta:

        model = CompaniaAseguradora

        fields = ['nombre', 'ruc', 'direccion', 'telefono', 'email',

                  'contacto_nombre', 'contacto_telefono', 'activo']

        widgets = {

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre de la compañía',

            }),

            'ruc': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': '13 dígitos',

                'maxlength': '13',

            }),

            'direccion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

                'placeholder': 'Dirección (opcional)',

            }),

            'telefono': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Teléfono (opcional)',

            }),

            'email': forms.EmailInput(attrs={

                'class': 'form-control',

                'placeholder': 'email@ejemplo.com',

            }),

            'contacto_nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del contacto',

            }),

            'contacto_telefono': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Teléfono del contacto',

            }),

            'activo': forms.CheckboxInput(attrs={

                'class': 'form-check-input',

            }),

        }

class CorredorSegurosForm(forms.ModelForm):

    """Formulario para crear/editar corredores de seguros"""

    class Meta:

        model = CorredorSeguros

        fields = ['compania_aseguradora', 'nombre', 'ruc', 'direccion', 'telefono', 'email',

                  'contacto_nombre', 'contacto_telefono', 'activo']

        widgets = {

            'compania_aseguradora': forms.Select(attrs={

                'class': 'form-control',

            }),

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del corredor/broker',

            }),

            'ruc': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': '13 dígitos',

                'maxlength': '13',

            }),

            'direccion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

            }),

            'telefono': forms.TextInput(attrs={

                'class': 'form-control',

            }),

            'email': forms.EmailInput(attrs={

                'class': 'form-control',

                'placeholder': 'email@broker.com',

            }),

            'contacto_nombre': forms.TextInput(attrs={

                'class': 'form-control',

            }),

            'contacto_telefono': forms.TextInput(attrs={

                'class': 'form-control',

            }),

            'activo': forms.CheckboxInput(attrs={

                'class': 'form-check-input',

            }),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Solo mostrar compañías activas

        self.fields['compania_aseguradora'].queryset = CompaniaAseguradora.objects.filter(activo=True)

class TipoSiniestroForm(forms.ModelForm):

    """Formulario para crear/editar tipos de siniestro"""

    class Meta:

        model = TipoSiniestro

        fields = ['nombre', 'descripcion', 'activo']

        widgets = {

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del tipo de siniestro',

            }),

            'descripcion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

            }),

            'activo': forms.CheckboxInput(attrs={

                'class': 'form-check-input',

            }),

        }

class ResponsableCustodioForm(forms.ModelForm):

    """Formulario para crear/editar responsables/custodios"""

    class Meta:

        model = ResponsableCustodio

        fields = ['nombre', 'cargo', 'departamento', 'email', 'telefono', 'activo']

        widgets = {

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre completo',

            }),

            'cargo': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Cargo (opcional)',

            }),

            'departamento': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Departamento/Área',

            }),

            'email': forms.EmailInput(attrs={

                'class': 'form-control',

                'placeholder': 'email@ejemplo.com',

            }),

            'telefono': forms.TextInput(attrs={

                'class': 'form-control',

            }),

            'activo': forms.CheckboxInput(attrs={

                'class': 'form-check-input',

            }),

        }

# ==============================================================================

# FORMULARIOS DE CATÁLOGO DE RAMOS (JERARQUÍA)

# ==============================================================================


class TipoRamoForm(forms.ModelForm):

    """Formulario para crear/editar tipos de ramo (nivel superior)"""

    class Meta:

        model = TipoRamo

        fields = ['codigo', 'nombre', 'descripcion', 'activo']

        widgets = {

            'codigo': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Ej: RG para Ramos Generales',

            }),

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del tipo de ramo',

            }),

            'descripcion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 3,

                'placeholder': 'Descripción del tipo (opcional)',

            }),

            'activo': forms.CheckboxInput(attrs={

                'class': 'form-check-input',

            }),

        }

    def clean_codigo(self):

        codigo = self.cleaned_data.get('codigo', '').upper()

        if TipoRamo.objects.filter(codigo=codigo).exclude(pk=self.instance.pk).exists():

            raise ValidationError('Ya existe un tipo de ramo con este código.')

        return codigo

class GrupoRamoForm(forms.ModelForm):

    """Formulario para crear/editar grupos de ramo (segundo nivel)"""

    class Meta:

        model = GrupoRamo

        fields = ['tipo_ramo', 'codigo', 'nombre', 'descripcion', 'orden', 'activo']

        widgets = {

            'tipo_ramo': forms.Select(attrs={'class': 'form-select'}),

            'codigo': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Ej: G1, G2, VEH',

            }),

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del grupo',

            }),

            'descripcion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 3,

                'placeholder': 'Descripción del grupo (opcional)',

            }),

            'orden': forms.NumberInput(attrs={

                'class': 'form-control',

                'min': '0',

            }),

            'activo': forms.CheckboxInput(attrs={

                'class': 'form-check-input',

            }),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['tipo_ramo'].queryset = TipoRamo.objects.filter(activo=True)

    def clean_codigo(self):

        codigo = self.cleaned_data.get('codigo', '').upper()

        tipo_ramo = self.cleaned_data.get('tipo_ramo')

        if tipo_ramo:

            exists = GrupoRamo.objects.filter(

                tipo_ramo=tipo_ramo, codigo=codigo

            ).exclude(pk=self.instance.pk).exists()

            if exists:

                raise ValidationError('Ya existe un grupo con este código para el tipo seleccionado.')

        return codigo

class SubgrupoRamoForm(forms.ModelForm):

    """Formulario para crear/editar subgrupos de ramo (tercer nivel)"""

    class Meta:

        model = SubgrupoRamo

        fields = ['grupo_ramo', 'codigo', 'nombre', 'descripcion', 'orden', 'activo']

        widgets = {

            'grupo_ramo': forms.Select(attrs={'class': 'form-select'}),

            'codigo': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Código del subgrupo',

            }),

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del subgrupo',

            }),

            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),

            'orden': forms.NumberInput(attrs={

                'class': 'form-control',

                'min': '0',

            }),

            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['grupo_ramo'].queryset = GrupoRamo.objects.filter(activo=True)

# Alias para compatibilidad con código existente (deprecado)

RamoForm = GrupoRamoForm

SubtipoRamoForm = SubgrupoRamoForm


# ==============================================================================

# FORMULARIOS DE PÓLIZA

# ==============================================================================


class PolizaForm(forms.ModelForm):

    """Formulario principal para crear/editar pólizas"""

    class Meta:

        model = Poliza

        fields = [

            'numero_poliza', 'compania_aseguradora', 'corredor_seguros',

            'grupo_ramo', 'suma_asegurada', 'prima_neta', 'prima_total',

            'deducible', 'porcentaje_deducible', 'deducible_minimo',

            'coberturas', 'fecha_inicio', 'fecha_fin', 'estado',

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

            'grupo_ramo': forms.Select(attrs={

                'class': 'form-select',

            }),

            'suma_asegurada': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

            }),

            'prima_neta': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'placeholder': 'Prima sin impuestos',

            }),

            'prima_total': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'placeholder': 'Prima con impuestos y contribuciones',

            }),

            'deducible': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'placeholder': 'Monto fijo de deducible',

            }),

            'porcentaje_deducible': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'max': '100',

                'placeholder': '% del siniestro',

            }),

            'deducible_minimo': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'placeholder': 'Mínimo si usa %',

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

        # Filtrar grupos de ramo activos

        self.fields['grupo_ramo'].queryset = GrupoRamo.objects.filter(activo=True).order_by('orden', 'nombre')

        self.fields['grupo_ramo'].required = False

        # Campos opcionales

        self.fields['prima_neta'].required = False

        self.fields['prima_total'].required = False

        self.fields['deducible'].required = False

        self.fields['porcentaje_deducible'].required = False

        self.fields['deducible_minimo'].required = False

        # Si se selecciona una compañía, limitar los corredores a esa compañía

        compania = None

        if 'compania_aseguradora' in self.data:

            try:

                compania_id = int(self.data.get('compania_aseguradora'))

                compania = CompaniaAseguradora.objects.filter(activo=True).get(pk=compania_id)

            except (TypeError, ValueError, CompaniaAseguradora.DoesNotExist):

                compania = None

        elif self.instance.pk and self.instance.compania_aseguradora_id:

            compania = self.instance.compania_aseguradora

        if compania:

            self.fields['corredor_seguros'].queryset = CorredorSeguros.objects.filter(

                compania_aseguradora=compania, activo=True

            )

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

    """Formulario para detalle de póliza por ramo con cálculos en vivo"""

    class Meta:

        model = DetallePolizaRamo

        fields = [

            'grupo_ramo', 'subgrupo_ramo', 'numero_factura', 'documento_contable',

            'suma_asegurada', 'total_prima', 'emision', 'observaciones',

        ]

        widgets = {

            'grupo_ramo': forms.Select(attrs={'class': 'form-select grupo-ramo-select'}),

            'subgrupo_ramo': forms.Select(attrs={'class': 'form-select'}),

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

                'data-calc': 'suma_asegurada',

            }),

            'total_prima': forms.NumberInput(attrs={

                'class': 'form-control prima-input',

                'step': '0.01',

                'min': '0',

                'data-calc': 'total_prima',

            }),

            'emision': forms.NumberInput(attrs={

                'class': 'form-control bg-slate-50',

                'step': '0.01',

                'min': '0',

                'data-calc': 'emision',

                'readonly': 'readonly',

            }),

            'observaciones': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

            }),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Siempre limitar los grupos a los activos

        self.fields['grupo_ramo'].queryset = GrupoRamo.objects.filter(activo=True)

        # Por defecto, no obligamos el subgrupo y restringimos su queryset

        self.fields['subgrupo_ramo'].required = False

        self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.none()

        # Si viene un grupo_ramo en el POST, limitar los subgrupos a ese grupo

        if 'grupo_ramo' in self.data:

            try:

                grupo_id = int(self.data.get('grupo_ramo'))

                self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.filter(

                    grupo_ramo_id=grupo_id, activo=True

                ).order_by('orden', 'nombre')

            except (ValueError, TypeError):

                # Si algo falla en el parseo, dejamos queryset vacío

                pass

        elif self.instance.pk and self.instance.grupo_ramo_id:

            # En edición, mostrar solo los subgrupos del grupo ya asociado

            self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.filter(

                grupo_ramo=self.instance.grupo_ramo, activo=True

            ).order_by('orden', 'nombre')

    def clean_subgrupo_ramo(self):

        """

        Garantiza que el subgrupo seleccionado pertenezca al grupo elegido.

        """

        subgrupo = self.cleaned_data.get('subgrupo_ramo')

        grupo = self.cleaned_data.get('grupo_ramo')

        if subgrupo and grupo and subgrupo.grupo_ramo_id != grupo.id:

            raise ValidationError(

                "El subgrupo seleccionado no pertenece al grupo escogido."

            )

        return subgrupo

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

            'bien_asegurado', 'numero_siniestro', 'tipo_siniestro',

            'fecha_siniestro', 'ubicacion', 'causa', 'descripcion_detallada',

            'responsable_custodio', 'monto_estimado',

            'valor_reclamo', 'deducible_aplicado', 'depreciacion', 'suma_asegurada_bien',

            'email_broker', 'observaciones',

        ]

        widgets = {

            'bien_asegurado': forms.Select(attrs={

                'class': 'form-select',

                'data-placeholder': 'Seleccione un bien asegurado...',

            }),

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

            'deducible_aplicado': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'placeholder': 'Se calcula desde la póliza si no se especifica',

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

        # Bienes asegurados: activos de pólizas vigentes + el actual si existe

        bienes_qs = BienAsegurado.objects.filter(

            activo=True,

            poliza__estado__in=['vigente', 'por_vencer']

        ).select_related('poliza', 'subgrupo_ramo')

        if instance and instance.bien_asegurado_id:

            bienes_qs = bienes_qs | BienAsegurado.objects.filter(pk=instance.bien_asegurado_id)

        self.fields['bien_asegurado'].queryset = bienes_qs.distinct()

        self.fields['bien_asegurado'].required = False

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

        self.fields['responsable_custodio'].required = False

        # Prefill del email del broker desde la póliza cuando sea posible

        try:

            if not (instance and instance.email_broker):

                poliza_obj = None

                if 'poliza' in self.data:

                    poliza_id = self.data.get('poliza')

                    if poliza_id:

                        poliza_obj = Poliza.objects.select_related('corredor_seguros').filter(pk=poliza_id).first()

                elif 'bien_asegurado' in self.data:

                    bien_id = self.data.get('bien_asegurado')

                    if bien_id:

                        bien = BienAsegurado.objects.select_related('poliza__corredor_seguros').filter(pk=bien_id).first()

                        if bien:

                            poliza_obj = bien.poliza

                elif instance and instance.poliza_id:

                    poliza_obj = instance.poliza

                if poliza_obj and poliza_obj.corredor_seguros and poliza_obj.corredor_seguros.email:

                    self.fields['email_broker'].initial = poliza_obj.corredor_seguros.email

        except Exception:

            pass

        # Formatos de fecha compatibles con datetime-local

        self.fields['fecha_siniestro'].input_formats = [

            '%Y-%m-%dT%H:%M',

            '%Y-%m-%d %H:%M:%S',

            '%Y-%m-%d %H:%M',

        ]

        # Campos opcionales

        for field in ['valor_reclamo', 'deducible_aplicado', 'depreciacion',

                      'suma_asegurada_bien', 'email_broker', 'observaciones']:

            if field in self.fields:

                self.fields[field].required = False

    def clean(self):

        cleaned_data = super().clean()

        bien_asegurado = cleaned_data.get('bien_asegurado')

        # El bien asegurado es requerido (la póliza se obtiene de él)

        if not bien_asegurado:

            raise ValidationError(

                'Debe seleccionar un Bien Asegurado.'

            )

        return cleaned_data

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

        fields = ['nombre', 'descripcion', 'grupo_ramo', 'subgrupo_ramo', 'responsable', 'poliza', 'activo']

        widgets = {

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del grupo',

            }),

            'descripcion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

            }),

            'grupo_ramo': forms.Select(attrs={'class': 'form-select'}),

            'subgrupo_ramo': forms.Select(attrs={'class': 'form-select'}),

            'responsable': forms.Select(attrs={'class': 'form-select'}),

            'poliza': forms.Select(attrs={'class': 'form-select'}),

            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['grupo_ramo'].queryset = GrupoRamo.objects.filter(activo=True)

        self.fields['subgrupo_ramo'].required = False

        self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.none()

        # Si viene un grupo_ramo en el POST, limitar los subgrupos

        if 'grupo_ramo' in self.data:

            try:

                grupo_id = int(self.data.get('grupo_ramo'))

                self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.filter(

                    grupo_ramo_id=grupo_id, activo=True

                ).order_by('orden', 'nombre')

            except (ValueError, TypeError):

                pass

        elif self.instance.pk and self.instance.grupo_ramo_id:

            self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.filter(

                grupo_ramo=self.instance.grupo_ramo, activo=True

            ).order_by('orden', 'nombre')

        self.fields['responsable'].queryset = ResponsableCustodio.objects.filter(activo=True)

        self.fields['responsable'].required = False

        self.fields['poliza'].queryset = Poliza.objects.filter(estado__in=['vigente', 'por_vencer'])

        self.fields['poliza'].required = False

class BienAseguradoForm(forms.ModelForm):

    """

    Formulario UNIFICADO para crear/editar bienes asegurados.

    Combina campos de BienAsegurado + InsuredAsset (deprecado).

    """

    class Meta:

        model = BienAsegurado

        fields = [

            # Identificación

            'codigo_bien', 'nombre', 'descripcion', 'categoria',

            # Relaciones

            'poliza', 'subgrupo_ramo',

            # Características técnicas

            'marca', 'modelo', 'serie', 'codigo_activo', 'anio_fabricacion',

            # Ubicación detallada

            'ubicacion', 'edificio', 'piso', 'departamento',

            # Responsable

            'responsable_custodio',

            # Valores financieros

            'valor_compra', 'valor_actual', 'valor_asegurado', 'valor_comercial',

            # Estado y condición

            'estado', 'condicion',

            # Fechas

            'fecha_adquisicion', 'fecha_garantia',

            # Imagen y QR

            'imagen', 'codigo_qr',

            # Otros

            'grupo_bienes', 'observaciones',

        ]

        widgets = {

            'codigo_bien': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Código único del bien',

            }),

            'nombre': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Nombre del bien',

            }),

            'descripcion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

            }),

            'categoria': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Ej: Equipos de Cómputo, Vehículos',

            }),

            'poliza': forms.Select(attrs={'class': 'form-select'}),

            'subgrupo_ramo': forms.Select(attrs={'class': 'form-select'}),

            'marca': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Marca',

            }),

            'modelo': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Modelo',

            }),

            'serie': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Número de serie',

            }),

            'codigo_activo': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Código de activo fijo institucional',

            }),

            'anio_fabricacion': forms.NumberInput(attrs={

                'class': 'form-control',

                'min': '1900',

                'max': '2100',

            }),

            'ubicacion': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Ubicación general',

            }),

            'edificio': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Edificio',

            }),

            'piso': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Piso',

            }),

            'departamento': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Departamento/Área',

            }),

            'responsable_custodio': forms.Select(attrs={'class': 'form-select'}),

            'valor_compra': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0.01',

            }),

            'valor_actual': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

            }),

            'valor_asegurado': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0.01',

            }),

            'valor_comercial': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

            }),

            'estado': forms.Select(attrs={'class': 'form-select'}),

            'condicion': forms.Select(attrs={'class': 'form-select'}),

            'fecha_adquisicion': DateInput(attrs={'class': 'form-control'}),

            'fecha_garantia': DateInput(attrs={'class': 'form-control'}),

            'imagen': forms.FileInput(attrs={'class': 'form-control'}),

            'codigo_qr': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Código QR',

            }),

            'grupo_bienes': forms.Select(attrs={'class': 'form-select'}),

            'observaciones': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

            }),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Pólizas vigentes o por vencer

        self.fields['poliza'].queryset = Poliza.objects.filter(

            estado__in=['vigente', 'por_vencer']

        ).select_related('compania_aseguradora', 'grupo_ramo')

        # Subgrupos: depende de si hay una póliza seleccionada con grupo_ramo

        self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.filter(activo=True)

        # Si hay una póliza seleccionada con grupo_ramo, filtrar subgrupos

        poliza_id = None

        if 'poliza' in self.data:

            try:

                poliza_id = int(self.data.get('poliza'))

            except (ValueError, TypeError):

                pass

        elif self.instance.pk and self.instance.poliza_id:

            poliza_id = self.instance.poliza_id

        if poliza_id:

            try:

                poliza = Poliza.objects.get(pk=poliza_id)

                if poliza.grupo_ramo_id:

                    self.fields['subgrupo_ramo'].queryset = SubgrupoRamo.objects.filter(

                        grupo_ramo_id=poliza.grupo_ramo_id, activo=True

                    ).order_by('orden', 'nombre')

            except Poliza.DoesNotExist:

                pass

        self.fields['responsable_custodio'].queryset = ResponsableCustodio.objects.filter(activo=True)

        self.fields['responsable_custodio'].required = False

        self.fields['grupo_bienes'].queryset = GrupoBienes.objects.filter(activo=True)

        self.fields['grupo_bienes'].required = False

        # Campos opcionales

        self.fields['categoria'].required = False

        self.fields['edificio'].required = False

        self.fields['piso'].required = False

        self.fields['departamento'].required = False

        self.fields['valor_compra'].required = False

        self.fields['valor_actual'].required = False

        self.fields['valor_comercial'].required = False

        self.fields['condicion'].required = False

        self.fields['fecha_adquisicion'].required = False

        self.fields['fecha_garantia'].required = False

        self.fields['anio_fabricacion'].required = False

        self.fields['imagen'].required = False

        self.fields['codigo_qr'].required = False

# ==============================================================================

# FORMULARIOS DE FACTURA

# ==============================================================================


class FacturaForm(forms.ModelForm):

    """Formulario para crear/editar facturas con cálculos en vivo"""

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

                'data-calc': 'subtotal',

            }),

            'iva': forms.NumberInput(attrs={

                'class': 'form-control bg-slate-50',

                'step': '0.01',

                'min': '0',

                'data-calc': 'iva',

                'readonly': 'readonly',

            }),

            'contribucion_superintendencia': forms.NumberInput(attrs={

                'class': 'form-control bg-slate-50',

                'step': '0.01',

                'min': '0',

                'data-calc': 'contribucion_superintendencia',

                'readonly': 'readonly',

            }),

            'contribucion_seguro_campesino': forms.NumberInput(attrs={

                'class': 'form-control bg-slate-50',

                'step': '0.01',

                'min': '0',

                'data-calc': 'contribucion_seguro_campesino',

                'readonly': 'readonly',

            }),

            'retenciones': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'data-calc': 'retenciones',

            }),

            'descuento_pronto_pago': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0',

                'data-calc': 'descuento_pronto_pago',

            }),

            'monto_total': forms.NumberInput(attrs={

                'class': 'form-control bg-emerald-50 font-semibold',

                'step': '0.01',

                'min': '0',

                'data-calc': 'monto_total',

                'readonly': 'readonly',

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

    """Formulario para crear/editar pagos con validación de saldo en vivo"""

    class Meta:

        model = Pago

        fields = [

            'factura', 'monto', 'fecha_pago', 'forma_pago',

            'referencia', 'observaciones',

        ]

        widgets = {

            'factura': forms.Select(attrs={

                'class': 'form-select',

                'data-calc': 'factura',

            }),

            'monto': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0.01',

                'data-calc': 'monto',

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

        import json

        facturas = Factura.objects.filter(

            estado__in=['pendiente', 'parcial', 'vencida']

        )

        self.fields['factura'].queryset = facturas

        # Crear diccionario de saldos para JavaScript

        saldos = {str(f.pk): float(f.saldo_pendiente) for f in facturas}

        self.fields['factura'].widget.attrs['data-saldos'] = json.dumps(saldos)

        # Mejorar labels con saldo visible

        choices = [('', '-- Seleccionar factura --')]

        for f in facturas:

            choices.append((f.pk, f'{f.numero_factura} (Saldo: ${f.saldo_pendiente:,.2f})'))

        self.fields['factura'].choices = choices

# ==============================================================================

# FORMULARIOS DE NOTA DE CRÉDITO

# ==============================================================================


class NotaCreditoForm(forms.ModelForm):

    """Formulario para crear/editar notas de crédito con validación de saldo"""

    class Meta:

        model = NotaCredito

        fields = ['factura', 'numero', 'fecha_emision', 'monto', 'motivo', 'documento']

        widgets = {

            'factura': forms.Select(attrs={

                'class': 'form-select',

                'data-calc': 'factura',

            }),

            'numero': forms.TextInput(attrs={

                'class': 'form-control',

                'placeholder': 'Número de nota de crédito',

            }),

            'fecha_emision': DateInput(attrs={'class': 'form-control'}),

            'monto': forms.NumberInput(attrs={

                'class': 'form-control',

                'step': '0.01',

                'min': '0.01',

                'data-calc': 'monto',

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

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        import json

        # Incluir saldo de factura para validación JS

        facturas = Factura.objects.all()

        saldos = {str(f.pk): float(f.monto_total or 0) for f in facturas}

        self.fields['factura'].widget.attrs['data-saldos'] = json.dumps(saldos)

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

# ==============================================================================

# FORMULARIOS DE CONFIGURACIÓN DEL SISTEMA

# ==============================================================================


class ConfiguracionSistemaForm(forms.ModelForm):

    """

    Formulario para editar configuraciones del sistema.

    Valida según el tipo de dato configurado.

    """

    class Meta:

        model = ConfiguracionSistema

        fields = ['valor', 'descripcion']

        widgets = {

            'valor': forms.Textarea(attrs={

                'class': 'form-control font-mono text-sm',

                'rows': 3,

            }),

            'descripcion': forms.Textarea(attrs={

                'class': 'form-control',

                'rows': 2,

            }),

        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Ajustar widget según el tipo

        if self.instance and self.instance.pk:

            tipo = self.instance.tipo

            if tipo == 'decimal':

                self.fields['valor'].widget = forms.NumberInput(attrs={

                    'class': 'form-control',

                    'step': '0.001',

                })

                self.fields['valor'].help_text = 'Ingrese un valor decimal (ej: 0.035 para 3.5%)'

            elif tipo == 'entero':

                self.fields['valor'].widget = forms.NumberInput(attrs={

                    'class': 'form-control',

                    'step': '1',

                })

                self.fields['valor'].help_text = 'Ingrese un número entero'

            elif tipo == 'texto':

                self.fields['valor'].widget = forms.TextInput(attrs={

                    'class': 'form-control',

                })

                self.fields['valor'].help_text = 'Ingrese el texto'

            elif tipo == 'json':

                self.fields['valor'].widget = forms.Textarea(attrs={

                    'class': 'form-control font-mono text-sm',

                    'rows': 6,

                })

                self.fields['valor'].help_text = 'Ingrese JSON válido'

    def clean_valor(self):

        """Valida el valor según el tipo de configuración."""

        valor = self.cleaned_data.get('valor', '')

        if not self.instance or not self.instance.pk:

            return valor

        tipo = self.instance.tipo

        if tipo == 'decimal':

            try:

                Decimal(valor)

            except (ValueError, TypeError, Exception):

                raise ValidationError('Debe ser un valor decimal válido (ej: 0.035)')

        elif tipo == 'entero':

            try:

                int(valor)

            except (ValueError, TypeError, Exception):

                raise ValidationError('Debe ser un número entero válido')

        elif tipo == 'json':

            import json

            try:

                json.loads(valor)

            except json.JSONDecodeError as e:

                raise ValidationError(f'JSON inválido: {str(e)}')

        return valor

class ConfiguracionBulkForm(forms.Form):

    """

    Formulario para edición masiva de configuraciones por categoría.

    Se genera dinámicamente según las configuraciones existentes.

    """

    def __init__(self, *args, categoria=None, **kwargs):

        super().__init__(*args, **kwargs)

        # Filtrar configuraciones por categoría

        qs = ConfiguracionSistema.objects.all()

        if categoria:

            qs = qs.filter(categoria=categoria)

        # Crear un campo por cada configuración

        for config in qs:

            field_name = f'config_{config.pk}'

            if config.tipo == 'decimal':

                self.fields[field_name] = forms.DecimalField(

                    label=config.clave.replace('_', ' ').title(),

                    initial=config.valor,

                    required=True,

                    decimal_places=4,

                    help_text=config.descripcion,

                    widget=forms.NumberInput(attrs={

                        'class': 'form-control',

                        'step': '0.0001',

                    })

                )

            elif config.tipo == 'entero':

                self.fields[field_name] = forms.IntegerField(

                    label=config.clave.replace('_', ' ').title(),

                    initial=config.valor,

                    required=True,

                    help_text=config.descripcion,

                    widget=forms.NumberInput(attrs={

                        'class': 'form-control',

                        'step': '1',

                    })

                )

            elif config.tipo == 'json':

                self.fields[field_name] = forms.CharField(

                    label=config.clave.replace('_', ' ').title(),

                    initial=config.valor,

                    required=True,

                    help_text=config.descripcion,

                    widget=forms.Textarea(attrs={

                        'class': 'form-control font-mono text-sm',

                        'rows': 4,

                    })

                )

            else:  # texto

                self.fields[field_name] = forms.CharField(

                    label=config.clave.replace('_', ' ').title(),

                    initial=config.valor,

                    required=True,

                    help_text=config.descripcion,

                    widget=forms.TextInput(attrs={

                        'class': 'form-control',

                    })

                )

            # Guardar referencia al objeto config

            self.fields[field_name].config_instance = config

    def save(self):

        """Guarda todas las configuraciones modificadas."""

        saved = []

        for field_name, field in self.fields.items():

            if hasattr(field, 'config_instance'):

                config = field.config_instance

                nuevo_valor = str(self.cleaned_data[field_name])

                if config.valor != nuevo_valor:

                    config.valor = nuevo_valor

                    config.full_clean()

                    config.save()

                    saved.append(config.clave)

        return saved
