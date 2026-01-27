from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Sum, Count
from decimal import Decimal
from datetime import timedelta, datetime
import re

from simple_history.models import HistoricalRecords

from .validators import validate_document


# ==================== MANAGERS PERSONALIZADOS (DRY) ====================
# Centralizan reglas de negocio para evitar duplicación de lógica de filtrado

class PolizaManager(models.Manager):
    """
    Manager personalizado para Póliza.
    Centraliza las reglas de negocio sobre estados y vencimientos.
    
    Uso:
        Poliza.objects.vigentes()
        Poliza.objects.por_vencer(dias=30)
        Poliza.objects.activas()
    """
    
    def vigentes(self):
        """Pólizas en estado vigente."""
        return self.filter(estado='vigente')
    
    def por_vencer(self, dias=None):
        """
        Pólizas que vencen en los próximos X días.
        
        Args:
            dias: Días para considerar "por vencer". Si es None, usa configuración del sistema.
        """
        if dias is None:
            # Importación tardía para evitar circular import
            from django.apps import apps
            ConfiguracionSistema = apps.get_model('app', 'ConfiguracionSistema')
            dias = ConfiguracionSistema.get_config('DIAS_ALERTA_VENCIMIENTO_POLIZA', 30)
        
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=dias)
        
        return self.filter(
            estado__in=['vigente', 'por_vencer'],
            fecha_fin__gte=hoy,
            fecha_fin__lte=fecha_limite
        )
    
    def vencidas(self):
        """Pólizas vencidas (fecha_fin < hoy)."""
        hoy = timezone.now().date()
        return self.filter(fecha_fin__lt=hoy)
    
    def activas(self):
        """Pólizas vigentes o por vencer (pueden recibir siniestros)."""
        return self.filter(estado__in=['vigente', 'por_vencer'])
    
    def canceladas(self):
        """Pólizas canceladas."""
        return self.filter(estado='cancelada')
    
    def vencen_en_rango(self, dias_inicio=0, dias_fin=30):
        """Pólizas que vencen entre X y Y días desde hoy."""
        hoy = timezone.now().date()
        fecha_inicio = hoy + timedelta(days=dias_inicio)
        fecha_limite = hoy + timedelta(days=dias_fin)
        
        return self.filter(
            estado__in=['vigente', 'por_vencer'],
            fecha_fin__gte=fecha_inicio,
            fecha_fin__lte=fecha_limite
        )
    
    def requieren_renovacion(self, dias=60):
        """Pólizas que requieren iniciar proceso de renovación."""
        return self.por_vencer(dias=dias)
    
    def con_estadisticas(self):
        """Pólizas con estadísticas agregadas (siniestros, facturas)."""
        return self.annotate(
            total_siniestros=Count('siniestros'),
            total_facturas=Count('facturas'),
            total_facturado=Sum('facturas__monto_total')
        )


class FacturaManager(models.Manager):
    """
    Manager personalizado para Factura.
    Centraliza las reglas de negocio sobre estados de pago.
    """
    
    def pendientes(self):
        """Facturas pendientes de pago (parcial o total)."""
        return self.filter(estado__in=['pendiente', 'parcial'])
    
    def por_vencer(self, dias=None):
        """Facturas que vencen en los próximos X días."""
        if dias is None:
            dias = 30
        
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=dias)
        
        return self.filter(
            estado__in=['pendiente', 'parcial'],
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=fecha_limite
        )
    
    def vencidas(self):
        """Facturas vencidas (no pagadas y fecha_vencimiento < hoy)."""
        hoy = timezone.now().date()
        return self.filter(
            estado__in=['pendiente', 'parcial', 'vencida'],
            fecha_vencimiento__lt=hoy
        )
    
    def pagadas(self):
        """Facturas completamente pagadas."""
        return self.filter(estado='pagada')
    
    def de_polizas_activas(self):
        """Facturas de pólizas vigentes o por vencer."""
        return self.filter(poliza__estado__in=['vigente', 'por_vencer'])
    
    def con_saldo_pendiente(self):
        """Facturas que tienen saldo por pagar."""
        return self.filter(estado__in=['pendiente', 'parcial', 'vencida'])


class SiniestroManager(models.Manager):
    """
    Manager personalizado para Siniestro.
    Centraliza las reglas de negocio sobre estados y gestión.
    """
    
    def pendientes_documentacion(self, dias_alerta=None):
        """
        Siniestros con documentación pendiente que requieren atención.
        
        Args:
            dias_alerta: Días después de los cuales se considera urgente.
        """
        if dias_alerta is None:
            from django.apps import apps
            ConfiguracionSistema = apps.get_model('app', 'ConfiguracionSistema')
            dias_alerta = ConfiguracionSistema.get_config('DIAS_ALERTA_DOCUMENTACION_SINIESTRO', 30)
        
        fecha_limite = timezone.now() - timedelta(days=dias_alerta)
        
        return self.filter(
            estado='documentacion_pendiente',
            fecha_registro__lt=fecha_limite
        )
    
    def esperando_respuesta(self, dias_alerta=None):
        """
        Siniestros enviados a aseguradora esperando respuesta.
        
        Args:
            dias_alerta: Días después de los cuales se considera demorado.
        """
        if dias_alerta is None:
            from django.apps import apps
            ConfiguracionSistema = apps.get_model('app', 'ConfiguracionSistema')
            dias_alerta = ConfiguracionSistema.get_config('DIAS_ALERTA_RESPUESTA_ASEGURADORA', 8)
        
        fecha_limite = timezone.now().date() - timedelta(days=dias_alerta)
        
        return self.filter(
            estado='enviado_aseguradora',
            fecha_envio_aseguradora__lt=fecha_limite,
            fecha_respuesta_aseguradora__isnull=True
        )
    
    def abiertos(self):
        """Siniestros que no están cerrados ni rechazados."""
        return self.exclude(estado__in=['cerrado', 'rechazado'])
    
    def en_proceso(self):
        """Siniestros en alguna etapa de procesamiento."""
        return self.filter(estado__in=[
            'registrado', 
            'documentacion_pendiente', 
            'enviado_aseguradora', 
            'en_evaluacion'
        ])
    
    def resueltos(self):
        """Siniestros aprobados, liquidados o cerrados."""
        return self.filter(estado__in=['aprobado', 'liquidado', 'cerrado'])
    
    def de_polizas_activas(self):
        """Siniestros de pólizas vigentes o por vencer."""
        return self.filter(poliza__estado__in=['vigente', 'por_vencer'])
    
    def requieren_atencion(self):
        """
        Siniestros que requieren atención urgente:
        - Documentación pendiente por más de X días
        - Esperando respuesta por más de X días
        """
        from django.apps import apps
        ConfiguracionSistema = apps.get_model('app', 'ConfiguracionSistema')
        dias_doc = ConfiguracionSistema.get_config('DIAS_ALERTA_DOCUMENTACION_SINIESTRO', 30)
        dias_resp = ConfiguracionSistema.get_config('DIAS_ALERTA_RESPUESTA_ASEGURADORA', 8)
        
        ahora = timezone.now()
        fecha_doc = ahora - timedelta(days=dias_doc)
        fecha_resp = ahora.date() - timedelta(days=dias_resp)
        
        return self.filter(
            Q(estado='documentacion_pendiente', fecha_registro__lt=fecha_doc) |
            Q(estado='enviado_aseguradora', 
              fecha_envio_aseguradora__lt=fecha_resp,
              fecha_respuesta_aseguradora__isnull=True)
        )
    
    def con_estadisticas_gestion(self):
        """Siniestros con días de gestión calculados."""
        ahora = timezone.now()
        return self.annotate(
            dias_gestion=models.ExpressionWrapper(
                ahora - models.F('fecha_registro'),
                output_field=models.DurationField()
            )
        )


class BienAseguradoManager(models.Manager):
    """
    Manager personalizado para BienAsegurado.
    """
    
    def activos(self):
        """Bienes en estado activo."""
        return self.filter(estado='activo')
    
    def de_polizas_activas(self):
        """Bienes de pólizas vigentes o por vencer."""
        return self.filter(poliza__estado__in=['vigente', 'por_vencer'])
    
    def sin_siniestros(self):
        """Bienes que nunca han tenido siniestros."""
        return self.filter(siniestros__isnull=True)
    
    def con_siniestros(self):
        """Bienes que han tenido al menos un siniestro."""
        return self.filter(siniestros__isnull=False).distinct()
    
    def por_responsable(self, responsable):
        """Bienes asignados a un responsable específico."""
        return self.filter(responsable_custodio=responsable)


# ==================== CONSTANTES Y VALIDADORES ====================

validador_ruc = RegexValidator(
    regex=r'^\d{13}$',
    message='El RUC debe contener exactamente 13 dígitos numéricos.',
    code='invalid_ruc'
)


# ==================== MODELOS ====================

class ConfiguracionSistema(models.Model):
    clave = models.CharField(max_length=100, unique=True, verbose_name="Clave")
    valor = models.TextField(verbose_name="Valor")  # TextField para soportar JSON
    tipo = models.CharField(max_length=20, choices=[
        ('decimal', 'Decimal'),
        ('entero', 'Entero'),
        ('texto', 'Texto'),
        ('json', 'JSON'),  # Nuevo tipo para estructuras complejas
    ], default='texto', verbose_name="Tipo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    categoria = models.CharField(max_length=50, choices=[
        ('facturas', 'Facturas y Pagos'),
        ('polizas', 'Pólizas'),
        ('siniestros', 'Siniestros'),
        ('general', 'General'),
    ], default='general', verbose_name="Categoría")
    
    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"
        ordering = ['categoria', 'clave']
    
    def __str__(self):
        return f"{self.clave} = {self.valor}"

    def clean(self):
        """
        Validaciones usando el registro de validadores extensible.
        
        Para agregar nuevas validaciones, registrar en:
        app/services/configuracion/validators.py
        
        Ejemplo:
            from app.services.configuracion import registro_validadores, RangoNumericoValidator
            registro_validadores.registrar('MI_CONFIG', RangoNumericoValidator(min_valor=1, max_valor=100))
        """
        super().clean()

        # Usar el registro de validadores extensible
        from app.services.configuracion import validar_configuracion
        
        errores = validar_configuracion(self.clave, self.valor, self.tipo)
        if errores:
            raise ValidationError(errores)

    def get_valor_tipado(self):
        if self.tipo == 'decimal':
            return Decimal(self.valor)
        elif self.tipo == 'entero':
            return int(self.valor)
        elif self.tipo == 'json':
            import json
            try:
                return json.loads(self.valor)
            except (json.JSONDecodeError, TypeError):
                return None
        return self.valor
    
    @classmethod
    def get_config(cls, clave, default=None):
        try:
            config = cls.objects.get(clave=clave)
            return config.get_valor_tipado()
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def inicializar_valores_default(cls):
        configs_default = [
            {
                'clave': 'PORCENTAJE_SUPERINTENDENCIA',
                'valor': '0.035',
                'tipo': 'decimal',
                'descripcion': 'Porcentaje de contribución a la Superintendencia (3.5%)',
                'categoria': 'facturas'
            },
            {
                'clave': 'PORCENTAJE_SEGURO_CAMPESINO',
                'valor': '0.005',
                'tipo': 'decimal',
                'descripcion': 'Porcentaje de contribución al Seguro Campesino (0.5%)',
                'categoria': 'facturas'
            },
            {
                'clave': 'PORCENTAJE_DESCUENTO_PRONTO_PAGO',
                'valor': '0.05',
                'tipo': 'decimal',
                'descripcion': 'Porcentaje de descuento por pronto pago (5%)',
                'categoria': 'facturas'
            },
            {
                'clave': 'DIAS_LIMITE_DESCUENTO_PRONTO_PAGO',
                'valor': '20',
                'tipo': 'entero',
                'descripcion': 'Días límite para aplicar descuento por pronto pago',
                'categoria': 'facturas'
            },
            {
                'clave': 'DIAS_ALERTA_VENCIMIENTO_POLIZA',
                'valor': '30',
                'tipo': 'entero',
                'descripcion': 'Días antes del vencimiento para alertar sobre pólizas',
                'categoria': 'polizas'
            },
            {
                'clave': 'DIAS_ALERTA_DOCUMENTACION_SINIESTRO',
                'valor': '30',
                'tipo': 'entero',
                'descripcion': 'Días máximos para completar documentación de siniestro',
                'categoria': 'siniestros'
            },
            {
                'clave': 'DIAS_ALERTA_RESPUESTA_ASEGURADORA',
                'valor': '8',
                'tipo': 'entero',
                'descripcion': 'Días de espera para respuesta de aseguradora',
                'categoria': 'siniestros'
            },
            {
                'clave': 'EMAIL_GERENTE_SINIESTROS',
                'valor': 'gerente.seguros@utpl.edu.ec',
                'tipo': 'texto',
                'descripcion': 'Correo electrónico del gerente de seguros para notificaciones de cierre',
                'categoria': 'siniestros'
            },
            {
                'clave': 'FIRMANTE_CARTA_NOMBRE',
                'valor': 'Nombre del Firmante',
                'tipo': 'texto',
                'descripcion': 'Nombre que aparecerá como firmante en cartas y recibos',
                'categoria': 'siniestros'
            },
            {
                'clave': 'FIRMANTE_CARTA_CARGO',
                'valor': 'Seguros / Inventarios',
                'tipo': 'texto',
                'descripcion': 'Cargo que aparecerá como firmante en cartas y recibos',
                'categoria': 'siniestros'
            },
            {
                'clave': 'FIRMANTE_DEPARTAMENTO',
                'valor': 'Dirección Administrativa Financiera',
                'tipo': 'texto',
                'descripcion': 'Departamento del firmante',
                'categoria': 'siniestros'
            },
            {
                'clave': 'FIRMANTE_TELEFONO',
                'valor': '3701444 ext. 2282',
                'tipo': 'texto',
                'descripcion': 'Teléfono del firmante',
                'categoria': 'siniestros'
            },
            {
                'clave': 'FIRMANTE_EMAIL',
                'valor': 'nlpizarro@utpl.edu.ec',
                'tipo': 'texto',
                'descripcion': 'Email del firmante',
                'categoria': 'siniestros'
            },
            {
                'clave': 'PORCENTAJE_IVA',
                'valor': '0.15',
                'tipo': 'decimal',
                'descripcion': 'Porcentaje de IVA aplicable (15%)',
                'categoria': 'facturas'
            },
            {
                'clave': 'TABLA_TASAS_EMISION',
                'valor': '[{"limite": 250, "tasa": "0.50"}, {"limite": 500, "tasa": "1.00"}, {"limite": 1000, "tasa": "3.00"}, {"limite": 2000, "tasa": "5.00"}, {"limite": 4000, "tasa": "7.00"}, {"limite": null, "tasa": "9.00"}]',
                'tipo': 'json',
                'descripcion': 'Tabla de tasas de emisión por rangos de prima. Formato: [{limite: número, tasa: "decimal"}]. El último debe tener limite: null.',
                'categoria': 'facturas'
            },
            # ===== CONFIGURACIONES DE NOTIFICACIONES =====
            {
                'clave': 'EMAIL_GERENCIA_ADMINISTRATIVA',
                'valor': 'gerencia.admin@utpl.edu.ec',
                'tipo': 'texto',
                'descripcion': 'Email de gerencia administrativa para notificar cierres de siniestros',
                'categoria': 'siniestros'
            },
            {
                'clave': 'HORAS_PLAZO_LIQUIDACION',
                'valor': '72',
                'tipo': 'entero',
                'descripcion': 'Horas hábiles de plazo para liquidación después de firma',
                'categoria': 'siniestros'
            },
        ]
        
        for config_data in configs_default:
            cls.objects.get_or_create(
                clave=config_data['clave'],
                defaults=config_data
            )

class CompaniaAseguradora(models.Model):
    """Modelo para las compañías aseguradoras"""
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre de la Compañía")
    ruc = models.CharField(
        max_length=13, 
        unique=True, 
        validators=[validador_ruc],
        verbose_name="RUC"
    )
    direccion = models.TextField(blank=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    contacto_nombre = models.CharField(max_length=200, blank=True, verbose_name="Nombre del Contacto")
    contacto_telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono del Contacto")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    # Nota: La relación con corredores se maneja desde CorredorSeguros.compania_aseguradora

    class Meta:
        verbose_name = "Compañía Aseguradora"
        verbose_name_plural = "Compañías Aseguradoras"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
    
    @property
    def corredores_activos(self):
        """Retorna los corredores activos de esta compañía"""
        return self.corredores.filter(activo=True)


class CorredorSeguros(models.Model):
    """Modelo para los corredores de seguros - pertenecen a una compañía aseguradora"""
    compania_aseguradora = models.ForeignKey(
        CompaniaAseguradora,
        on_delete=models.PROTECT,
        related_name='corredores',
        verbose_name="Compañía Aseguradora"
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Corredor")
    ruc = models.CharField(
        max_length=13, 
        unique=True, 
        validators=[validador_ruc],
        verbose_name="RUC"
    )
    direccion = models.TextField(blank=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    contacto_nombre = models.CharField(max_length=200, blank=True, verbose_name="Nombre del Contacto")
    contacto_telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono del Contacto")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Corredor de Seguros"
        verbose_name_plural = "Corredores de Seguros"
        ordering = ['compania_aseguradora__nombre', 'nombre']
        unique_together = ['compania_aseguradora', 'nombre']  # Un corredor único por compañía

    def __str__(self):
        return f"{self.nombre} ({self.compania_aseguradora.nombre})"


class TipoPoliza(models.Model):
    """Modelo para los tipos de póliza"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Tipo de Póliza")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de Póliza"
        verbose_name_plural = "Tipos de Póliza"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ResponsableCustodio(models.Model):
    """Modelo para responsables/custodios de bienes asegurados"""
    nombre = models.CharField(max_length=200, verbose_name="Nombre Completo")
    cargo = models.CharField(max_length=200, blank=True, verbose_name="Cargo")
    departamento = models.CharField(max_length=200, blank=True, verbose_name="Departamento/Área")
    email = models.EmailField(blank=True, verbose_name="Email")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Responsable/Custodio"
        verbose_name_plural = "Responsables/Custodios"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
        ]

    def __str__(self):
        if self.departamento:
            return f"{self.nombre} - {self.departamento}"
        return self.nombre


class Poliza(models.Model):
    """Modelo principal para las pólizas de seguros"""
    ESTADO_CHOICES = [
        ('vigente', 'Vigente'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
        ('por_vencer', 'Por Vencer'),
    ]

    # Información básica
    numero_poliza = models.CharField(max_length=100, unique=True, verbose_name="Número de Póliza")
    compania_aseguradora = models.ForeignKey(CompaniaAseguradora, on_delete=models.PROTECT, 
                                            related_name='polizas', verbose_name="Compañía Aseguradora")
    corredor_seguros = models.ForeignKey(CorredorSeguros, on_delete=models.PROTECT, 
                                        related_name='polizas', verbose_name="Corredor de Seguros")
    tipo_poliza = models.ForeignKey(TipoPoliza, on_delete=models.PROTECT, 
                                   related_name='polizas', verbose_name="Tipo de Póliza")
    
    # Clasificación de ramo (grupo al que pertenece la póliza)
    grupo_ramo = models.ForeignKey('GrupoRamo', on_delete=models.PROTECT,
                                   related_name='polizas', verbose_name="Grupo de Ramo",
                                   null=True, blank=True,
                                   help_text="Categoría de la póliza según clasificación de ramos")
    
    # Coberturas y sumas
    suma_asegurada = models.DecimalField(max_digits=15, decimal_places=2, 
                                        validators=[MinValueValidator(Decimal('0.01'))],
                                        verbose_name="Suma Asegurada")
    coberturas = models.TextField(verbose_name="Coberturas Detalladas")
    
    # Prima del seguro (campos agregados para modelado correcto)
    prima_neta = models.DecimalField(max_digits=15, decimal_places=2,
                                     validators=[MinValueValidator(Decimal('0.00'))],
                                     default=Decimal('0.00'),
                                     verbose_name="Prima Neta",
                                     help_text="Costo base del seguro sin impuestos ni contribuciones")
    prima_total = models.DecimalField(max_digits=15, decimal_places=2,
                                      validators=[MinValueValidator(Decimal('0.00'))],
                                      default=Decimal('0.00'),
                                      verbose_name="Prima Total",
                                      help_text="Prima neta + IVA + contribuciones")
    
    # Deducible (característica del contrato, no del siniestro)
    deducible = models.DecimalField(max_digits=15, decimal_places=2,
                                    validators=[MinValueValidator(Decimal('0.00'))],
                                    default=Decimal('0.00'),
                                    verbose_name="Deducible",
                                    help_text="Monto que asume el asegurado en cada siniestro")
    porcentaje_deducible = models.DecimalField(max_digits=5, decimal_places=2,
                                               validators=[MinValueValidator(Decimal('0.00')),
                                                          MaxValueValidator(Decimal('100.00'))],
                                               default=Decimal('0.00'),
                                               verbose_name="% Deducible",
                                               help_text="Porcentaje del siniestro que asume el asegurado (alternativo al monto fijo)")
    deducible_minimo = models.DecimalField(max_digits=15, decimal_places=2,
                                           validators=[MinValueValidator(Decimal('0.00'))],
                                           default=Decimal('0.00'),
                                           verbose_name="Deducible Mínimo",
                                           help_text="Monto mínimo de deducible cuando se usa porcentaje")
    
    # Fechas
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio de Vigencia")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin de Vigencia")
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='vigente', verbose_name="Estado")
    
    # Observaciones
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    # Gran Contribuyente (activa retenciones automáticas)
    es_gran_contribuyente = models.BooleanField(
        default=False,
        verbose_name="Es Gran Contribuyente",
        help_text="Si está activo, se aplicarán retenciones de prima (1%) e IVA (100%)"
    )

    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  related_name='polizas_creadas', verbose_name="Creado por")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    # Historial de cambios
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    # Manager personalizado (centraliza reglas de negocio)
    objects = PolizaManager()

    class Meta:
        verbose_name = "Póliza"
        verbose_name_plural = "Pólizas"
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['numero_poliza']),
            models.Index(fields=['estado', 'fecha_fin']),
        ]

    def __str__(self):
        return f"{self.numero_poliza} - {self.compania_aseguradora}"

    @property
    def dias_para_vencer(self):
        try:
            if not self.fecha_fin:
                return 0
            hoy = timezone.now().date()
            if self.fecha_fin > hoy:
                return (self.fecha_fin - hoy).days
            return 0
        except (TypeError, AttributeError):
            return 0

    @property
    def esta_vigente(self):
        try:
            if not self.fecha_inicio or not self.fecha_fin:
                return False
            hoy = timezone.now().date()
            return self.fecha_inicio <= hoy <= self.fecha_fin
        except (TypeError, AttributeError):
            return False

    # Propiedades calculadas para totales consolidados de ramos
    @property
    def total_suma_asegurada_ramos(self):
        """Retorna la suma total asegurada de todos los ramos"""
        return self.detalles_ramo.aggregate(
            total=models.Sum('suma_asegurada')
        )['total'] or Decimal('0.00')

    @property
    def total_prima_ramos(self):
        """
        Retorna la prima total de todos los ramos.
        Si existe valor pre-calculado con annotate(), lo usa para evitar query adicional.
        """
        # Usar valor pre-calculado si existe (desde annotate en la vista)
        if hasattr(self, 'total_prima_calculado') and self.total_prima_calculado is not None:
            return self.total_prima_calculado
        # Fallback a aggregate (genera query adicional)
        return self.detalles_ramo.aggregate(
            total=models.Sum('total_prima')
        )['total'] or Decimal('0.00')

    @property
    def total_facturado_ramos(self):
        """Retorna el total facturado de todos los ramos"""
        return self.detalles_ramo.aggregate(
            total=models.Sum('total_facturado')
        )['total'] or Decimal('0.00')

    @property
    def total_valor_por_pagar_ramos(self):
        """Retorna el valor total por pagar de todos los ramos"""
        return self.detalles_ramo.aggregate(
            total=models.Sum('valor_por_pagar')
        )['total'] or Decimal('0.00')

    @property
    def total_retenciones_ramos(self):
        """Retorna el total de retenciones de todos los ramos"""
        totales = self.detalles_ramo.aggregate(
            prima=models.Sum('retencion_prima'),
            iva=models.Sum('retencion_iva')
        )
        return (totales['prima'] or Decimal('0.00')) + (totales['iva'] or Decimal('0.00'))

    @property
    def cantidad_ramos(self):
        """Retorna la cantidad de ramos asociados"""
        return self.detalles_ramo.count()

    def calcular_deducible_aplicable(self, monto_siniestro):
        """
        Calcula el deducible aplicable para un monto de siniestro.
        Cálculo puro sin dependencias de servicios.
        """
        deducible_fijo = self.deducible or Decimal('0.00')
        porcentaje = self.porcentaje_deducible or Decimal('0.00')
        minimo = self.deducible_minimo or Decimal('0.00')
        
        if porcentaje > 0:
            deducible_porcentaje = (porcentaje / 100) * monto_siniestro
            if minimo > 0:
                deducible_porcentaje = max(deducible_porcentaje, minimo)
            return max(deducible_fijo, deducible_porcentaje)
        
        return deducible_fijo


class Factura(models.Model):
    """Modelo para las facturas emitidas por las aseguradoras"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('parcial', 'Pago Parcial'),
        ('vencida', 'Vencida'),
    ]

    # Relación con póliza
    poliza = models.ForeignKey(Poliza, on_delete=models.PROTECT, 
                              related_name='facturas', verbose_name="Póliza")
    
    # Información de la factura
    numero_factura = models.CharField(max_length=100, unique=True, verbose_name="Número de Factura")
    fecha_emision = models.DateField(verbose_name="Fecha de Emisión")
    fecha_vencimiento = models.DateField(verbose_name="Fecha de Vencimiento")
    
    # Montos
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, 
                                  validators=[MinValueValidator(Decimal('0.01'))],
                                  verbose_name="Subtotal")
    iva = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                             verbose_name="IVA")
    contribucion_superintendencia = models.DecimalField(max_digits=15, decimal_places=2, 
                                                       default=Decimal('0.00'),
                                                       verbose_name="Contribución Superintendencia (3.5%)")
    contribucion_seguro_campesino = models.DecimalField(max_digits=15, decimal_places=2, 
                                                       default=Decimal('0.00'),
                                                       verbose_name="Contribución Seguro Campesino (0.5%)")
    retenciones = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                     verbose_name="Retenciones")
    descuento_pronto_pago = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                               verbose_name="Descuento por Pronto Pago")
    monto_total = models.DecimalField(max_digits=15, decimal_places=2, 
                                     validators=[MinValueValidator(Decimal('0.01'))],
                                     verbose_name="Monto Total")
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado")
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='facturas_creadas', verbose_name="Creado por")
    
    # Historial de cambios
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    # Manager personalizado (centraliza reglas de negocio)
    objects = FacturaManager()

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ['-fecha_emision']
        indexes = [
            models.Index(fields=['numero_factura']),
            models.Index(fields=['estado', 'fecha_vencimiento']),
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.poliza.numero_poliza}"

    def _calcular_total_pagado(self):
        """Calcula el total de pagos aprobados (método auxiliar de datos)."""
        if not self.pk:
            return Decimal('0.00')
        
        total = self.pagos.filter(estado='aprobado').aggregate(
            total=models.Sum('monto')
        )['total']
        
        return total if total is not None else Decimal('0.00')

    @property
    def saldo_pendiente(self):
        """
        Retorna el saldo pendiente de pago.
        """
        if not self.monto_total:
            return Decimal('0.00')
        
        total_pagado = self._calcular_total_pagado()
        saldo = self.monto_total - total_pagado
        return saldo if saldo > Decimal('0.00') else Decimal('0.00')

    @property
    def puede_aplicar_descuento(self):
        try:
            if not self.fecha_emision or self.estado == 'pagada':
                return False
            
            hoy = timezone.now().date()
            dias_limite = ConfiguracionSistema.get_config('DIAS_LIMITE_DESCUENTO_PRONTO_PAGO', 20)
            fecha_limite = self.fecha_emision + timedelta(days=dias_limite)
            return hoy <= fecha_limite
        except (TypeError, AttributeError):
            return False
    
    @property
    def dias_para_vencimiento(self):
        try:
            if not self.fecha_vencimiento:
                return 0
            
            hoy = timezone.now().date()
            if self.fecha_vencimiento > hoy:
                return (self.fecha_vencimiento - hoy).days
            return 0
        except (TypeError, AttributeError):
            return 0
    
    @property
    def esta_vencida(self):
        try:
            if not self.fecha_vencimiento:
                return False
            return timezone.now().date() > self.fecha_vencimiento
        except (TypeError, AttributeError):
            return False


class Pago(models.Model):
    """Modelo para registrar los pagos realizados a las facturas"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    FORMA_PAGO_CHOICES = [
        ('transferencia', 'Transferencia Bancaria'),
        ('cheque', 'Cheque'),
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta de Crédito'),
    ]

    # Relación con factura
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, 
                               related_name='pagos', verbose_name="Factura")
    
    # Información del pago
    fecha_pago = models.DateField(verbose_name="Fecha de Pago")
    monto = models.DecimalField(max_digits=15, decimal_places=2, 
                               validators=[MinValueValidator(Decimal('0.01'))],
                               verbose_name="Monto Pagado")
    forma_pago = models.CharField(max_length=20, choices=FORMA_PAGO_CHOICES, 
                                 verbose_name="Forma de Pago")
    referencia = models.CharField(max_length=200, blank=True, 
                                 verbose_name="Número de Referencia/Comprobante")
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', 
                            verbose_name="Estado")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                      related_name='pagos_registrados', verbose_name="Registrado por")
    
    # Historial de cambios
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Pago {self.referencia} - ${self.monto} ({self.fecha_pago})"



class TipoSiniestro(models.Model):
    """Modelo para los tipos de siniestro"""
    TIPO_CHOICES = [
        ('daño', 'Daño'),
        ('robo', 'Robo'),
        ('hurto', 'Hurto'),
        ('incendio', 'Incendio'),
        ('inundacion', 'Inundación'),
        ('terremoto', 'Terremoto'),
        ('vandalismo', 'Vandalismo'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=50, choices=TIPO_CHOICES, unique=True, 
                            verbose_name="Tipo de Siniestro")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de Siniestro"
        verbose_name_plural = "Tipos de Siniestro"
        ordering = ['nombre']

    def __str__(self):
        return self.get_nombre_display()


class Siniestro(models.Model):
    """Modelo para registrar los siniestros"""
    ESTADO_CHOICES = [
        # Flujo inicial (reporte del custodio)
        ('registrado', 'Registrado'),
        
        # Flujo con broker
        ('notificado_broker', 'Notificado al Broker'),
        ('documentacion_lista', 'Documentación Lista'),
        
        # Flujo con aseguradora
        ('enviado_aseguradora', 'Enviado a Aseguradora'),
        
        # Flujo de indemnización
        ('recibo_recibido', 'Recibo Recibido'),
        ('en_disputa', 'En Disputa'),
        ('recibo_firmado', 'Recibo Firmado'),
        ('pendiente_liquidacion', 'Pendiente Liquidación'),
        ('vencido', 'Vencido (72h)'),
        ('liquidado', 'Liquidado'),
        
        # Estados finales
        ('cerrado', 'Cerrado'),
        ('rechazado', 'Rechazado'),
        ('rechazado', 'Rechazado'),
    ]

    # Relación principal con Bien Asegurado (nuevo modelo relacional)
    bien_asegurado = models.ForeignKey('BienAsegurado', on_delete=models.PROTECT,
                                       related_name='siniestros', verbose_name="Bien Asegurado",
                                       null=True, blank=True,
                                       help_text="Bien específico afectado por el siniestro")
    
    # Relación con póliza (mantener para compatibilidad, se obtiene del bien_asegurado si existe)
    poliza = models.ForeignKey(Poliza, on_delete=models.PROTECT, 
                              related_name='siniestros', verbose_name="Póliza",
                              null=True, blank=True,
                              help_text="Póliza asociada (se obtiene automáticamente del bien asegurado)")
    
    # Información del siniestro
    numero_siniestro = models.CharField(max_length=100, unique=True, 
                                       verbose_name="Número de Siniestro")
    tipo_siniestro = models.ForeignKey(TipoSiniestro, on_delete=models.PROTECT, 
                                      related_name='siniestros', verbose_name="Tipo de Siniestro")
    fecha_siniestro = models.DateTimeField(verbose_name="Fecha y Hora del Siniestro")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    # Información del bien asegurado (campos legacy, se obtienen del bien_asegurado si existe)
    bien_nombre = models.CharField(max_length=200, verbose_name="Nombre del Bien",
                                   blank=True, default='',
                                   help_text="Campo legacy: usar bien_asegurado en su lugar")
    bien_modelo = models.CharField(max_length=100, blank=True, verbose_name="Modelo")
    bien_serie = models.CharField(max_length=100, blank=True, verbose_name="Número de Serie")
    bien_marca = models.CharField(max_length=100, blank=True, verbose_name="Marca")
    bien_codigo_activo = models.CharField(max_length=100, blank=True, verbose_name="Código de Activo")
    
    # Detalles del siniestro
    responsable_custodio = models.ForeignKey(ResponsableCustodio, on_delete=models.PROTECT,
                                            related_name='siniestros', verbose_name="Responsable/Custodio",
                                            null=True, blank=True)
    ubicacion = models.CharField(max_length=300, verbose_name="Ubicación del Siniestro")
    causa = models.TextField(verbose_name="Causa del Siniestro")
    descripcion_detallada = models.TextField(verbose_name="Descripción Detallada")
    
    # Montos
    monto_estimado = models.DecimalField(max_digits=15, decimal_places=2,
                                        validators=[MinValueValidator(Decimal('0.01'))],
                                        verbose_name="Monto Estimado del Daño")
    monto_indemnizado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                           verbose_name="Monto Indemnizado")

    # Campos de valoración del siniestro
    valor_reclamo = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                        verbose_name="Valor del Reclamo (según proforma)")
    deducible_aplicado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                             verbose_name="Deducible Aplicado",
                                             help_text="Deducible efectivamente aplicado en este siniestro (calculado desde la póliza)")
    depreciacion = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                       verbose_name="Depreciación")
    suma_asegurada_bien = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                              verbose_name="Suma Asegurada del Bien")

    # Datos del broker para este siniestro
    email_broker = models.EmailField(blank=True, verbose_name="Email del Broker",
                                     help_text="Email específico para este siniestro")

    # Estado y fechas de gestión
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='registrado',
                            verbose_name="Estado")
    fecha_envio_aseguradora = models.DateField(null=True, blank=True,
                                              verbose_name="Fecha de Envío a Aseguradora")
    fecha_respuesta_aseguradora = models.DateField(null=True, blank=True,
                                                  verbose_name="Fecha de Respuesta de Aseguradora")
    fecha_liquidacion = models.DateField(null=True, blank=True, verbose_name="Fecha de Liquidación")

    # Nuevas fechas de gestión mejorada
    fecha_notificacion_broker = models.DateTimeField(null=True, blank=True,
                                                     verbose_name="Fecha de Notificación al Broker")
    fecha_respuesta_broker = models.DateTimeField(null=True, blank=True,
                                                  verbose_name="Fecha de Respuesta del Broker")
    email_respuesta_broker = models.CharField(max_length=255, blank=True,
                                              verbose_name="Email Respuesta Broker",
                                              help_text="Email de donde llegó la respuesta del broker")
    fecha_respuesta_esperada = models.DateField(null=True, blank=True,
                                                verbose_name="Fecha de Respuesta Esperada (5 días hábiles)")
    fecha_notificacion_responsable = models.DateField(null=True, blank=True,
                                                      verbose_name="Fecha de Notificación al Responsable")
    fecha_firma_indemnizacion = models.DateTimeField(null=True, blank=True,
                                                     verbose_name="Fecha de Firma del Recibo de Indemnización")
    fecha_limite_deposito = models.DateField(null=True, blank=True,
                                             verbose_name="Fecha Límite de Depósito (72h)")

    # Datos de pago
    valor_pagado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                       verbose_name="Valor Pagado")
    fecha_pago = models.DateField(null=True, blank=True, verbose_name="Fecha de Pago")

    # =========================================================================
    # FLUJO DE INDEMNIZACIÓN
    # =========================================================================
    
    # Recibo de indemnización (recibido de la aseguradora)
    recibo_indemnizacion = models.FileField(
        upload_to='siniestros/recibos/%Y/%m/',
        null=True, blank=True,
        verbose_name="Recibo de Indemnización",
        help_text="PDF del recibo enviado por la aseguradora"
    )
    fecha_recibo_recibido = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha Recepción Recibo"
    )
    email_origen_recibo = models.CharField(
        max_length=255, blank=True,
        verbose_name="Email Origen",
        help_text="Dirección de email de donde se recibió el recibo"
    )
    
    # Firma del recibo (aceptación UTPL)
    recibo_firmado = models.FileField(
        upload_to='siniestros/recibos_firmados/%Y/%m/',
        null=True, blank=True,
        verbose_name="Recibo Firmado",
        help_text="PDF del recibo firmado por UTPL"
    )
    conforme_indemnizacion = models.BooleanField(
        default=False,
        verbose_name="Conforme con Indemnización",
        help_text="Indica si UTPL está de acuerdo con el monto propuesto"
    )
    
    # Disputa
    en_disputa = models.BooleanField(default=False, verbose_name="En Disputa")
    motivo_disputa = models.TextField(
        blank=True,
        verbose_name="Motivo de Disputa",
        help_text="Razón por la cual no se acepta el recibo"
    )
    fecha_disputa = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de Disputa"
    )
    resolucion_disputa = models.TextField(
        blank=True,
        verbose_name="Resolución de Disputa",
        help_text="Cómo se resolvió la disputa"
    )
    
    # Envío a liquidación (inicia contador 72h)
    fecha_envio_liquidacion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha Envío a Liquidación",
        help_text="Fecha en que se envió el recibo firmado. Inicia las 72h hábiles."
    )
    fecha_limite_liquidacion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha Límite Liquidación",
        help_text="72 horas hábiles desde el envío"
    )
    notificacion_72h_enviada = models.BooleanField(
        default=False,
        verbose_name="Notificación 72h Enviada",
        help_text="Se envió recordatorio por vencimiento de plazo"
    )
    
    # Liquidación
    monto_liquidado = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name="Monto Liquidado",
        help_text="Monto efectivamente depositado por la aseguradora"
    )
    numero_comprobante = models.CharField(
        max_length=100, blank=True,
        verbose_name="Número de Comprobante",
        help_text="Referencia de la transferencia o pago"
    )
    motivo_diferencia_monto = models.TextField(
        blank=True,
        verbose_name="Motivo Diferencia de Monto",
        help_text="Explicación si el monto liquidado difiere del aprobado"
    )
    
    # Cierre
    fecha_cierre = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de Cierre"
    )

    # Observaciones
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  related_name='siniestros_creados', verbose_name="Creado por")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    # Historial de cambios
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    # Manager personalizado (centraliza reglas de negocio)
    objects = SiniestroManager()

    class Meta:
        verbose_name = "Siniestro"
        verbose_name_plural = "Siniestros"
        ordering = ['-fecha_siniestro']
        indexes = [
            models.Index(fields=['numero_siniestro']),
            models.Index(fields=['estado', 'fecha_siniestro']),
            models.Index(fields=['bien_asegurado']),
        ]

    def __str__(self):
        nombre_bien = self.get_nombre_bien()
        return f"{self.numero_siniestro} - {nombre_bien}"

    def get_nombre_bien(self):
        """Obtiene el nombre del bien, priorizando bien_asegurado sobre campos legacy"""
        if self.bien_asegurado_id:
            return self.bien_asegurado.nombre
        return self.bien_nombre or "Sin bien especificado"

    def get_poliza(self):
        """Obtiene la póliza, priorizando la del bien_asegurado"""
        if self.bien_asegurado_id:
            return self.bien_asegurado.poliza
        return self.poliza

    @property
    def poliza_efectiva(self):
        """Propiedad para obtener la póliza efectiva"""
        return self.get_poliza()

    @property
    def clasificacion_bien(self):
        """Obtiene la clasificación del bien si usa bien_asegurado"""
        if self.bien_asegurado_id:
            return self.bien_asegurado.clasificacion_completa
        return None

    @property
    def deducible_calculado(self):
        """Calcula el deducible desde la póliza según el monto del siniestro"""
        poliza = self.get_poliza()
        if poliza and self.monto_estimado:
            return poliza.calcular_deducible_aplicable(self.monto_estimado)
        return Decimal('0.00')

    @property
    def monto_a_indemnizar(self):
        """
        Calcula el monto estimado a indemnizar.
        Cálculo puro: monto - deducible - depreciación
        """
        monto = self.monto_estimado or Decimal('0.00')
        deducible = self.deducible_aplicado or self.deducible_calculado
        depreciacion = self.depreciacion or Decimal('0.00')
        
        resultado = monto - deducible - depreciacion
        return max(resultado, Decimal('0.00'))

    # =========================================================================
    # PROPIEDADES DE INFRASEGURO (Valor asegurado < Valor de reposición)
    # =========================================================================
    
    @property
    def valor_reposicion_bien(self):
        """
        Obtiene el valor de reposición del bien (valor actual o comercial).
        El valor de reposición es el costo de reemplazar el bien en el mercado.
        """
        if not self.bien_asegurado_id:
            return None
        
        bien = self.bien_asegurado
        # Prioridad: valor_comercial > valor_actual > valor_compra
        return bien.valor_comercial or bien.valor_actual or bien.valor_compra
    
    @property
    def valor_asegurado_bien(self):
        """Obtiene el valor asegurado del bien vinculado."""
        if self.bien_asegurado_id:
            return self.bien_asegurado.valor_asegurado
        return None
    
    @property
    def tiene_infraseguro(self):
        """
        Detecta si existe infraseguro (valor asegurado < valor de reposición).
        El infraseguro afecta el cálculo de la indemnización aplicando regla proporcional.
        """
        valor_asegurado = self.valor_asegurado_bien
        valor_reposicion = self.valor_reposicion_bien
        
        if not valor_asegurado or not valor_reposicion:
            return False
        
        return valor_asegurado < valor_reposicion
    
    @property
    def porcentaje_cobertura(self):
        """
        Calcula el porcentaje de cobertura: (Valor Asegurado / Valor Reposición) * 100
        Si hay infraseguro, este porcentaje será menor a 100%.
        """
        valor_asegurado = self.valor_asegurado_bien
        valor_reposicion = self.valor_reposicion_bien
        
        if not valor_asegurado or not valor_reposicion or valor_reposicion == 0:
            return Decimal('100.00')
        
        porcentaje = (valor_asegurado / valor_reposicion) * 100
        return min(porcentaje.quantize(Decimal('0.01')), Decimal('100.00'))
    
    @property
    def monto_infraseguro(self):
        """
        Calcula el monto de infraseguro (diferencia entre valor de reposición y asegurado).
        """
        valor_asegurado = self.valor_asegurado_bien
        valor_reposicion = self.valor_reposicion_bien
        
        if not valor_asegurado or not valor_reposicion:
            return Decimal('0.00')
        
        diferencia = valor_reposicion - valor_asegurado
        return max(diferencia, Decimal('0.00'))
    
    @property
    def indemnizacion_con_regla_proporcional(self):
        """
        Calcula la indemnización aplicando la regla proporcional por infraseguro.
        
        Fórmula: Indemnización = (Valor Asegurado / Valor Reposición) * Pérdida
        
        Donde Pérdida = Monto estimado - Deducible - Depreciación
        """
        if not self.tiene_infraseguro:
            return self.monto_a_indemnizar
        
        porcentaje = self.porcentaje_cobertura / 100
        indemnizacion_ajustada = self.monto_a_indemnizar * porcentaje
        
        return indemnizacion_ajustada.quantize(Decimal('0.01'))
    
    @property
    def perdida_por_infraseguro(self):
        """
        Calcula cuánto pierde el asegurado por tener infraseguro.
        """
        if not self.tiene_infraseguro:
            return Decimal('0.00')
        
        return self.monto_a_indemnizar - self.indemnizacion_con_regla_proporcional
    
    @property
    def alerta_infraseguro(self):
        """
        Retorna información de alerta de infraseguro para mostrar en la UI.
        """
        if not self.tiene_infraseguro:
            return None
        
        return {
            'tipo': 'warning',
            'titulo': 'Infraseguro detectado',
            'mensaje': f'El valor asegurado (${self.valor_asegurado_bien:,.2f}) es inferior al valor de reposición (${self.valor_reposicion_bien:,.2f}).',
            'detalle': f'Cobertura: {self.porcentaje_cobertura}%. Se aplicará regla proporcional.',
            'perdida_estimada': self.perdida_por_infraseguro,
            'indemnizacion_ajustada': self.indemnizacion_con_regla_proporcional,
        }

    @property
    def dias_desde_registro(self):
        try:
            if not self.fecha_registro:
                return 0
            hoy = timezone.now()
            return (hoy - self.fecha_registro).days
        except (TypeError, AttributeError):
            return 0

    @property
    def requiere_alerta_documentacion(self):
        try:
            dias_alerta = ConfiguracionSistema.get_config('DIAS_ALERTA_DOCUMENTACION_SINIESTRO', 30)
            return (
                self.dias_desde_registro > dias_alerta and 
                self.estado == 'documentacion_pendiente'
            )
        except (TypeError, AttributeError):
            return False

    @property
    def dias_espera_respuesta(self):
        try:
            if self.fecha_envio_aseguradora and not self.fecha_respuesta_aseguradora:
                hoy = timezone.now().date()
                return (hoy - self.fecha_envio_aseguradora).days
            return 0
        except (TypeError, AttributeError):
            return 0

    @property
    def requiere_alerta_respuesta(self):
        try:
            dias_alerta = ConfiguracionSistema.get_config('DIAS_ALERTA_RESPUESTA_ASEGURADORA', 8)
            return (
                self.dias_espera_respuesta > dias_alerta and 
                self.estado == 'enviado_aseguradora'
            )
        except (TypeError, AttributeError):
            return False
    
    @property
    def tiempo_total_gestion(self):
        try:
            if self.fecha_liquidacion and self.fecha_registro:
                return (self.fecha_liquidacion - self.fecha_registro.date()).days
            return self.dias_desde_registro
        except (TypeError, AttributeError):
            return 0
    
    @property
    def porcentaje_indemnizado(self):
        try:
            if self.monto_indemnizado and self.monto_estimado and self.monto_estimado > 0:
                return (self.monto_indemnizado / self.monto_estimado) * 100
            return 0
        except (TypeError, AttributeError, ZeroDivisionError):
            return 0

    @property
    def dias_gestion(self):
        """Calcula los días totales de gestión del siniestro"""
        try:
            if self.fecha_pago:
                # Si ya se pagó, calcular desde registro hasta pago
                return (self.fecha_pago - self.fecha_registro.date()).days
            elif self.fecha_liquidacion:
                return (self.fecha_liquidacion - self.fecha_registro.date()).days
            else:
                # Si aún está en proceso, calcular hasta hoy
                return (timezone.now().date() - self.fecha_registro.date()).days
        except (TypeError, AttributeError):
            return 0

    @property
    def alerta_respuesta_aseguradora(self):
        """
        Verifica si han pasado más de 5 días hábiles sin respuesta de aseguradora.
        Retorna True si se debe mostrar alerta.
        """
        try:
            if self.fecha_envio_aseguradora and not self.fecha_respuesta_aseguradora:
                dias = (timezone.now().date() - self.fecha_envio_aseguradora).days
                # Aproximación: 5 días hábiles ≈ 7 días calendario
                return dias > 7
            return False
        except (TypeError, AttributeError):
            return False

    @property
    def alerta_notificar_responsable(self):
        """
        Verifica si han pasado más de 15 días sin notificar al responsable.
        Retorna True si se debe mostrar alerta.
        """
        try:
            if not self.fecha_notificacion_responsable:
                dias = (timezone.now().date() - self.fecha_registro.date()).days
                return dias > 15
            return False
        except (TypeError, AttributeError):
            return False

    @property
    def alerta_deposito_pendiente(self):
        """
        Verifica si han pasado más de 72 horas después de la firma sin recibir pago.
        Retorna True si se debe mostrar alerta.
        """
        try:
            if self.fecha_firma_indemnizacion and not self.fecha_pago:
                horas = (timezone.now() - self.fecha_firma_indemnizacion).total_seconds() / 3600
                return horas > 72
            return False
        except (TypeError, AttributeError):
            return False

    @property
    def valor_indemnizacion_calculado(self):
        """Calcula el valor de indemnización: valor_reclamo - deducible - depreciación"""
        try:
            valor = self.valor_reclamo or Decimal('0.00')
            deducible = self.deducible or Decimal('0.00')
            depreciacion = self.depreciacion or Decimal('0.00')
            return max(valor - deducible - depreciacion, Decimal('0.00'))
        except (TypeError, AttributeError):
            return Decimal('0.00')

    # =========================================================================
    # MÉTODOS DEL FLUJO DE INDEMNIZACIÓN
    # =========================================================================
    
    def calcular_fecha_limite_habil(self, fecha_inicio, horas=72):
        """
        Calcula la fecha límite excluyendo fines de semana.
        72 horas hábiles = 3 días hábiles
        """
        dias_habiles = horas // 24  # 3 días
        fecha = fecha_inicio
        dias_contados = 0
        
        while dias_contados < dias_habiles:
            fecha += timedelta(days=1)
            # Lunes=0, Domingo=6
            if fecha.weekday() < 5:  # Lunes a Viernes
                dias_contados += 1
        
        return fecha
    
    @property
    def horas_restantes_liquidacion(self):
        """Calcula las horas restantes para la liquidación."""
        if not self.fecha_limite_liquidacion:
            return None
        
        ahora = timezone.now()
        if ahora >= self.fecha_limite_liquidacion:
            return 0
        
        delta = self.fecha_limite_liquidacion - ahora
        return max(0, delta.total_seconds() / 3600)
    
    @property
    def plazo_vencido(self):
        """Indica si el plazo de 72h hábiles ha vencido."""
        if not self.fecha_limite_liquidacion:
            return False
        return timezone.now() >= self.fecha_limite_liquidacion
    
    @property
    def diferencia_monto(self):
        """Calcula la diferencia entre monto aprobado y liquidado."""
        if not self.monto_liquidado or not self.monto_a_indemnizar:
            return None
        return self.monto_liquidado - self.monto_a_indemnizar
    
    @property
    def tiene_diferencia_monto(self):
        """Indica si hay diferencia entre montos."""
        diferencia = self.diferencia_monto
        if diferencia is None:
            return False
        return abs(diferencia) > Decimal('0.01')
    
    @property
    def porcentaje_diferencia_monto(self):
        """Calcula el porcentaje de diferencia."""
        if not self.monto_a_indemnizar or self.monto_a_indemnizar == 0:
            return None
        diferencia = self.diferencia_monto
        if diferencia is None:
            return None
        return (diferencia / self.monto_a_indemnizar) * 100

    # =========================================================================
    # MÉTODOS DE TRANSICIÓN DE ESTADO (Flujo tipo Odoo)
    # =========================================================================
    
    def notificar_broker(self):
        """
        Transición: registrado → notificado_broker
        Registra que se notificó al broker y espera su respuesta.
        """
        if self.estado != 'registrado':
            raise ValueError(f"No se puede notificar al broker desde estado '{self.estado}'")
        
        self.fecha_notificacion_broker = timezone.now()
        self.estado = 'notificado_broker'
        self.save(update_fields=['fecha_notificacion_broker', 'estado'])
    
    def registrar_respuesta_broker(self, email_origen=''):
        """
        Transición: notificado_broker → documentacion_lista
        Registra que el broker respondió y la documentación está lista.
        """
        if self.estado != 'notificado_broker':
            raise ValueError(f"No se puede registrar respuesta del broker desde estado '{self.estado}'")
        
        self.fecha_respuesta_broker = timezone.now()
        self.email_respuesta_broker = email_origen
        self.estado = 'documentacion_lista'
        self.save(update_fields=['fecha_respuesta_broker', 'email_respuesta_broker', 'estado'])
    
    def enviar_a_aseguradora(self):
        """
        Transición: documentacion_lista → enviado_aseguradora
        Registra que se enviaron los documentos a la aseguradora.
        """
        if self.estado != 'documentacion_lista':
            raise ValueError(f"No se puede enviar a aseguradora desde estado '{self.estado}'")
        
        self.fecha_envio_aseguradora = timezone.now().date()
        self.estado = 'enviado_aseguradora'
        self.save(update_fields=['fecha_envio_aseguradora', 'estado'])
    
    def registrar_recibo_indemnizacion(self, archivo, email_origen='', monto_indemnizado=None,
                                        perdida_bruta=None, deducible=None, depreciacion=None):
        """
        Transición: enviado_aseguradora → recibo_recibido
        Registra que llegó el recibo de indemnización de la aseguradora.
        
        Args:
            archivo: El archivo PDF del recibo
            email_origen: Email de donde llegó el recibo
            monto_indemnizado: El monto neto que la aseguradora pagará (LA SUMA DE)
            perdida_bruta: Valor de pérdida bruta (monto estimado del daño)
            deducible: Deducible aplicado por la aseguradora
            depreciacion: Depreciación aplicada
        """
        if self.estado != 'enviado_aseguradora':
            raise ValueError(f"No se puede registrar recibo desde estado '{self.estado}'")
        
        self.recibo_indemnizacion = archivo
        self.fecha_recibo_recibido = timezone.now()
        self.email_origen_recibo = email_origen
        self.fecha_respuesta_aseguradora = timezone.now().date()
        
        # Monto neto a indemnizar (LA SUMA DE)
        if monto_indemnizado:
            self.monto_indemnizado = Decimal(str(monto_indemnizado))
        
        # Valoración del siniestro desde el recibo
        if perdida_bruta:
            self.monto_estimado = Decimal(str(perdida_bruta))
        if deducible:
            self.deducible_aplicado = Decimal(str(deducible))
        if depreciacion:
            self.depreciacion = Decimal(str(depreciacion))
        
        self.estado = 'recibo_recibido'
        self.save(update_fields=[
            'recibo_indemnizacion', 'fecha_recibo_recibido', 
            'email_origen_recibo', 'fecha_respuesta_aseguradora',
            'monto_indemnizado', 'monto_estimado', 'deducible_aplicado',
            'depreciacion', 'estado'
        ])
    
    def firmar_recibo(self, archivo_firmado):
        """
        Transición: recibo_recibido → recibo_firmado
        Registra que se firmó el recibo de indemnización.
        """
        if self.estado != 'recibo_recibido':
            raise ValueError(f"No se puede firmar recibo desde estado '{self.estado}'")
        
        self.recibo_firmado = archivo_firmado
        self.conforme_indemnizacion = True
        self.fecha_firma_indemnizacion = timezone.now()
        self.estado = 'recibo_firmado'
        self.save(update_fields=[
            'recibo_firmado', 'conforme_indemnizacion',
            'fecha_firma_indemnizacion', 'estado'
        ])
    
    @property
    def puede_notificar_broker(self):
        """Indica si se puede notificar al broker."""
        return self.estado == 'registrado'
    
    @property
    def puede_enviar_aseguradora(self):
        """Indica si se puede enviar a la aseguradora."""
        return self.estado == 'documentacion_lista'
    
    @property
    def esperando_respuesta_broker(self):
        """Indica si está esperando respuesta del broker."""
        return self.estado == 'notificado_broker'
    
    @property
    def esperando_recibo_aseguradora(self):
        """Indica si está esperando recibo de la aseguradora."""
        return self.estado == 'enviado_aseguradora'
    
    def iniciar_liquidacion(self):
        """
        Marca el siniestro como enviado a liquidación e inicia el contador de 72h.
        """
        ahora = timezone.now()
        self.fecha_envio_liquidacion = ahora
        self.fecha_limite_liquidacion = self.calcular_fecha_limite_habil(ahora, 72)
        self.estado = 'pendiente_liquidacion'
        self.save(update_fields=[
            'fecha_envio_liquidacion', 
            'fecha_limite_liquidacion', 
            'estado'
        ])
    
    def registrar_disputa(self, motivo):
        """Marca el siniestro en disputa."""
        self.en_disputa = True
        self.motivo_disputa = motivo
        self.fecha_disputa = timezone.now()
        self.estado = 'en_disputa'
        self.save(update_fields=[
            'en_disputa', 'motivo_disputa', 'fecha_disputa', 'estado'
        ])
    
    def resolver_disputa(self, resolucion):
        """Resuelve la disputa y vuelve a estado recibo_recibido."""
        self.resolucion_disputa = resolucion
        self.en_disputa = False
        self.estado = 'recibo_recibido'
        self.save(update_fields=[
            'resolucion_disputa', 'en_disputa', 'estado'
        ])
    
    def registrar_liquidacion(self, monto, comprobante, motivo_diferencia='', fecha_pago=None):
        """
        Registra la liquidación del siniestro.
        
        Args:
            monto: Monto efectivamente pagado por la aseguradora
            comprobante: Número de comprobante del depósito
            motivo_diferencia: Motivo si hay diferencia entre monto ofrecido y pagado
            fecha_pago: Fecha del depósito (default: hoy)
        """
        self.monto_liquidado = monto
        self.valor_pagado = monto  # El valor pagado es el mismo que el liquidado
        self.numero_comprobante = comprobante
        self.motivo_diferencia_monto = motivo_diferencia
        self.fecha_liquidacion = timezone.now().date()
        self.fecha_pago = fecha_pago or timezone.now().date()
        self.estado = 'liquidado'
        self.save(update_fields=[
            'monto_liquidado', 'valor_pagado', 'numero_comprobante', 
            'motivo_diferencia_monto', 'fecha_liquidacion', 'fecha_pago', 'estado'
        ])
    
    def cerrar_siniestro(self):
        """Cierra el siniestro."""
        self.fecha_cierre = timezone.now()
        self.estado = 'cerrado'
        self.save(update_fields=['fecha_cierre', 'estado'])
    
    @property
    def puede_firmar_recibo(self):
        """Indica si se puede firmar el recibo."""
        return self.estado == 'recibo_recibido' and self.recibo_indemnizacion
    
    @property
    def puede_disputar(self):
        """Indica si se puede iniciar disputa."""
        return self.estado == 'recibo_recibido'
    
    @property
    def puede_enviar_liquidacion(self):
        """Indica si se puede enviar a liquidación."""
        return self.estado == 'recibo_firmado' and self.recibo_firmado
    
    @property
    def puede_registrar_liquidacion(self):
        """Indica si se puede registrar la liquidación."""
        return self.estado in ['pendiente_liquidacion', 'vencido']
    
    @property
    def adjuntos_fotos(self):
        """Retorna solo los adjuntos de tipo 'fotos'."""
        return list(self.adjuntos.filter(tipo_adjunto='fotos'))


class Documento(models.Model):
    """Modelo para almacenar documentos asociados a pólizas y siniestros"""
    TIPO_DOCUMENTO_CHOICES = [
        ('poliza', 'Póliza de Seguro'),
        ('factura', 'Factura'),
        ('comprobante_pago', 'Comprobante de Pago'),
        ('informe_tecnico', 'Informe Técnico'),
        ('denuncia', 'Denuncia'),
        ('proforma', 'Proforma'),
        ('carta_formal', 'Carta Formal'),
        ('fotografia', 'Fotografía'),
        ('otro', 'Otro'),
    ]
    
    # Tamaño máximo de archivo: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Relaciones opcionales
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='documentos', verbose_name="Póliza")
    siniestro = models.ForeignKey(Siniestro, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='documentos', verbose_name="Siniestro")
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='documentos', verbose_name="Factura")
    
    # Información del documento
    tipo_documento = models.CharField(max_length=30, choices=TIPO_DOCUMENTO_CHOICES, 
                                     verbose_name="Tipo de Documento")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Documento")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    archivo = models.FileField(
        upload_to='documentos/%Y/%m/', 
        verbose_name="Archivo",
        validators=[validate_document],
        help_text="Archivos permitidos: PDF, imágenes (JPG, PNG), documentos Office. Máximo 10MB."
    )
    
    # Auditoría
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='documentos_subidos', verbose_name="Subido por")
    
    # Historial de cambios
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios",
        excluded_fields=['archivo']  # No guardar el archivo en el historial
    )

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_documento_display()})"
    
    @property
    def extension(self):
        """Retorna la extensión del archivo."""
        import os
        if self.archivo:
            return os.path.splitext(self.archivo.name)[1].lower()
        return ''
    
    @property
    def tamanio_formateado(self):
        """Retorna el tamaño del archivo formateado."""
        from django.template.defaultfilters import filesizeformat
        if self.archivo:
            try:
                return filesizeformat(self.archivo.size)
            except (OSError, ValueError):
                return 'N/A'
        return 'N/A'
    
    @property
    def entidad_relacionada(self):
        """Retorna la entidad principal a la que está relacionado el documento."""
        if self.poliza:
            return f"Póliza {self.poliza.numero_poliza}"
        elif self.siniestro:
            return f"Siniestro {self.siniestro.numero_siniestro}"
        elif self.factura:
            return f"Factura {self.factura.numero_factura}"
        return "Sin relación"


# ==================== MODELOS DE CHECKLIST Y ADJUNTOS DE SINIESTRO ====================

class ChecklistSiniestroConfig(models.Model):
    """
    Configuración de items de checklist para siniestros.
    Permite definir los documentos/pasos requeridos por tipo de siniestro.
    """
    tipo_siniestro = models.ForeignKey(TipoSiniestro, on_delete=models.CASCADE,
                                       related_name='checklist_config',
                                       verbose_name="Tipo de Siniestro")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Item")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    es_obligatorio = models.BooleanField(default=True, verbose_name="Es Obligatorio")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Configuración de Checklist de Siniestro"
        verbose_name_plural = "Configuraciones de Checklist de Siniestro"
        ordering = ['tipo_siniestro', 'orden', 'nombre']
        unique_together = ['tipo_siniestro', 'nombre']

    def __str__(self):
        return f"{self.tipo_siniestro.get_nombre_display()} - {self.nombre}"


class ChecklistSiniestro(models.Model):
    """
    Instancia de checklist para un siniestro específico.
    Registra el estado de completado de cada item.
    """
    siniestro = models.ForeignKey(Siniestro, on_delete=models.CASCADE,
                                  related_name='checklist_items',
                                  verbose_name="Siniestro")
    config_item = models.ForeignKey(ChecklistSiniestroConfig, on_delete=models.PROTECT,
                                    related_name='instancias',
                                    verbose_name="Item de Checklist")
    completado = models.BooleanField(default=False, verbose_name="Completado")
    fecha_completado = models.DateTimeField(null=True, blank=True,
                                            verbose_name="Fecha de Completado")
    completado_por = models.ForeignKey(User, on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='checklist_completados',
                                       verbose_name="Completado por")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Item de Checklist de Siniestro"
        verbose_name_plural = "Items de Checklist de Siniestro"
        ordering = ['siniestro', 'config_item__orden']
        unique_together = ['siniestro', 'config_item']

    def __str__(self):
        estado = "✓" if self.completado else "○"
        return f"{estado} {self.config_item.nombre}"

    def marcar_completado(self, usuario):
        """Marca el item como completado"""
        self.completado = True
        self.fecha_completado = timezone.now()
        self.completado_por = usuario
        self.save()


class AdjuntoSiniestro(models.Model):
    """
    Modelo para documentos específicos de siniestro.
    Incluye soporte para firma electrónica.
    """
    TIPO_ADJUNTO_CHOICES = [
        ('informe', 'Informe'),
        ('proforma', 'Proforma'),
        ('salvamento', 'Acta de Salvamento'),
        ('preexistencia', 'Certificado de Preexistencia'),
        ('carta_formal', 'Carta Formal'),
        ('recibo_indemnizacion', 'Recibo de Indemnización'),
        ('fotos', 'Fotografías'),
        ('peritaje', 'Informe de Peritaje'),
        ('policia', 'Denuncia/Parte Policial'),
        ('otro', 'Otro'),
    ]

    siniestro = models.ForeignKey(Siniestro, on_delete=models.CASCADE,
                                  related_name='adjuntos',
                                  verbose_name="Siniestro")
    tipo_adjunto = models.CharField(max_length=30, choices=TIPO_ADJUNTO_CHOICES,
                                    verbose_name="Tipo de Adjunto")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Documento")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    archivo = models.FileField(upload_to='siniestros/adjuntos/%Y/%m/',
                               verbose_name="Archivo",
                               validators=[validate_document])
    
    # Vinculación con checklist
    checklist_item = models.ForeignKey(
        'ChecklistSiniestro', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='adjuntos_vinculados',
        verbose_name="Item del Checklist"
    )

    # Firma electrónica (para documentos que requieren firma)
    requiere_firma = models.BooleanField(default=False, verbose_name="Requiere Firma")
    firmado = models.BooleanField(default=False, verbose_name="Firmado")
    hash_firma = models.CharField(max_length=64, blank=True, verbose_name="Hash de Firma (SHA256)")
    fecha_firma = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Firma")
    firmado_por = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='documentos_firmados',
                                    verbose_name="Firmado por")
    ip_firma = models.GenericIPAddressField(null=True, blank=True,
                                            verbose_name="IP de Firma")

    # Auditoría
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='adjuntos_siniestro_subidos',
                                   verbose_name="Subido por")

    class Meta:
        verbose_name = "Adjunto de Siniestro"
        verbose_name_plural = "Adjuntos de Siniestro"
        ordering = ['siniestro', 'tipo_adjunto', '-fecha_subida']

    def __str__(self):
        return f"{self.get_tipo_adjunto_display()} - {self.nombre}"

    def aplicar_firma(self, usuario, ip=None):
        """Aplica firma electrónica al documento"""
        import hashlib

        if not self.archivo:
            raise ValidationError("No se puede firmar un documento sin archivo.")

        # Generar hash del archivo
        hasher = hashlib.sha256()
        for chunk in self.archivo.chunks():
            hasher.update(chunk)

        self.hash_firma = hasher.hexdigest()
        self.firmado = True
        self.fecha_firma = timezone.now()
        self.firmado_por = usuario
        self.ip_firma = ip
        self.save()

    @property
    def extension(self):
        """Retorna la extensión del archivo"""
        import os
        if self.archivo:
            return os.path.splitext(self.archivo.name)[1].lower()
        return ''


class Alerta(models.Model):
    """Modelo para gestionar las alertas automáticas del sistema"""
    TIPO_ALERTA_CHOICES = [
        ('vencimiento_poliza', 'Vencimiento de Póliza'),
        ('pago_pendiente', 'Pago Pendiente'),
        ('documentacion_pendiente', 'Documentación Pendiente'),
        ('respuesta_aseguradora', 'Respuesta de Aseguradora Pendiente'),
        ('pronto_pago', 'Descuento por Pronto Pago Disponible'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('leida', 'Leída'),
        ('atendida', 'Atendida'),
    ]

    # Relaciones opcionales
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='alertas', verbose_name="Póliza")
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='alertas', verbose_name="Factura")
    siniestro = models.ForeignKey(Siniestro, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='alertas', verbose_name="Siniestro")
    
    # Información de la alerta
    tipo_alerta = models.CharField(max_length=30, choices=TIPO_ALERTA_CHOICES, 
                                  verbose_name="Tipo de Alerta")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    mensaje = models.TextField(verbose_name="Mensaje")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', 
                            verbose_name="Estado")
    
    # Destinatarios
    destinatarios = models.ManyToManyField(User, related_name='alertas_recibidas', 
                                          verbose_name="Destinatarios")
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_envio = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío")
    fecha_lectura = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Lectura")

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.titulo} - {self.estado}"

    def marcar_como_enviada(self):
        """Marca la alerta como enviada"""
        self.estado = 'enviada'
        self.fecha_envio = timezone.now()
        self.save()

    def marcar_como_leida(self):
        """Marca la alerta como leída"""
        self.estado = 'leida'
        self.fecha_lectura = timezone.now()
        self.save()


# ==================== MODELO NOTIFICACIÓN EMAIL ====================

class NotificacionEmail(models.Model):
    """
    Modelo para gestionar notificaciones por email del sistema.
    Registra todas las notificaciones enviadas y su estado.
    """
    TIPO_NOTIFICACION_CHOICES = [
        ('siniestro_broker', 'Siniestro a Broker'),
        ('siniestro_responsable', 'Siniestro a Responsable'),
        ('siniestro_cierre', 'Cierre de Siniestro'),
        ('alerta_respuesta', 'Alerta de Respuesta Pendiente'),
        ('alerta_deposito', 'Alerta de Depósito Pendiente'),
        ('poliza_vencimiento', 'Vencimiento de Póliza'),
        ('factura_vencimiento', 'Vencimiento de Factura'),
        ('renovacion_pendiente', 'Renovación Pendiente'),
        ('otro', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
        ('rebotado', 'Rebotado'),
    ]

    tipo = models.CharField(max_length=30, choices=TIPO_NOTIFICACION_CHOICES,
                           verbose_name="Tipo de Notificación")
    destinatario = models.EmailField(verbose_name="Destinatario")
    cc = models.TextField(blank=True, verbose_name="CC (separados por coma)")
    asunto = models.CharField(max_length=300, verbose_name="Asunto")
    contenido = models.TextField(verbose_name="Contenido del Email")
    contenido_html = models.TextField(blank=True, verbose_name="Contenido HTML")

    # Relaciones opcionales
    siniestro = models.ForeignKey(Siniestro, on_delete=models.CASCADE,
                                  null=True, blank=True,
                                  related_name='notificaciones_email',
                                  verbose_name="Siniestro")
    poliza = models.ForeignKey(Poliza, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='notificaciones_email',
                               verbose_name="Póliza")
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE,
                                null=True, blank=True,
                                related_name='notificaciones_email',
                                verbose_name="Factura")

    # Estado y tracking
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES,
                             default='pendiente', verbose_name="Estado")
    enviado = models.BooleanField(default=False, verbose_name="Enviado")
    fecha_envio = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío")
    intentos = models.PositiveIntegerField(default=0, verbose_name="Intentos de Envío")
    error_mensaje = models.TextField(blank=True, verbose_name="Mensaje de Error")

    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='notificaciones_creadas',
                                   verbose_name="Creado por")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Notificación de Email"
        verbose_name_plural = "Notificaciones de Email"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['tipo', 'estado']),
            models.Index(fields=['fecha_creacion']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.destinatario}"

    def marcar_como_enviado(self):
        """Marca la notificación como enviada"""
        self.enviado = True
        self.estado = 'enviado'
        self.fecha_envio = timezone.now()
        self.save()

    def registrar_error(self, mensaje):
        """Registra un error de envío"""
        self.intentos += 1
        self.error_mensaje = mensaje
        if self.intentos >= 3:
            self.estado = 'fallido'
        self.save()


# ==================== MODELO NOTA DE CRÉDITO ====================

class NotaCredito(models.Model):
    """
    Modelo para notas de crédito asociadas a facturas.
    """
    ESTADO_CHOICES = [
        ('emitida', 'Emitida'),
        ('aplicada', 'Aplicada'),
        ('anulada', 'Anulada'),
    ]

    factura = models.ForeignKey(Factura, on_delete=models.PROTECT,
                                related_name='notas_credito',
                                verbose_name="Factura")
    numero = models.CharField(max_length=100, unique=True,
                             verbose_name="Número de Nota de Crédito")
    fecha_emision = models.DateField(verbose_name="Fecha de Emisión")
    monto = models.DecimalField(max_digits=15, decimal_places=2,
                               validators=[MinValueValidator(Decimal('0.01'))],
                               verbose_name="Monto")
    motivo = models.TextField(verbose_name="Motivo")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES,
                             default='emitida', verbose_name="Estado")

    # Documento adjunto
    documento = models.FileField(upload_to='notas_credito/%Y/%m/',
                                null=True, blank=True,
                                verbose_name="Documento")

    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='notas_credito_creadas',
                                   verbose_name="Creado por")
    fecha_creacion = models.DateTimeField(auto_now_add=True,
                                          verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True,
                                              verbose_name="Fecha de Modificación")

    # Historial
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    class Meta:
        verbose_name = "Nota de Crédito"
        verbose_name_plural = "Notas de Crédito"
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"NC-{self.numero} - ${self.monto}"



# ==================== NUEVOS MODELOS (Código en inglés, interfaz en español) ====================

class Quote(models.Model):
    """
    Modelo para cotizaciones/proformas de seguros.
    Permite comparar opciones de diferentes aseguradoras antes de contratar.
    """
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('sent', 'Enviada'),
        ('under_review', 'En Revisión'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
        ('expired', 'Expirada'),
        ('converted', 'Convertida a Póliza'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]

    # Identificación
    quote_number = models.CharField(max_length=100, unique=True, verbose_name="Número de Cotización")
    title = models.CharField(max_length=200, verbose_name="Título/Descripción")
    
    # Tipo de seguro solicitado
    policy_type = models.ForeignKey(TipoPoliza, on_delete=models.PROTECT,
                                    related_name='quotes', verbose_name="Tipo de Póliza")
    
    # Valores
    sum_insured = models.DecimalField(max_digits=15, decimal_places=2,
                                      validators=[MinValueValidator(Decimal('0.01'))],
                                      verbose_name="Suma a Asegurar")
    coverage_details = models.TextField(verbose_name="Detalle de Coberturas Solicitadas")
    
    # Fechas
    request_date = models.DateField(verbose_name="Fecha de Solicitud")
    valid_until = models.DateField(verbose_name="Válida Hasta")
    desired_start_date = models.DateField(verbose_name="Fecha de Inicio Deseada")
    desired_end_date = models.DateField(verbose_name="Fecha de Fin Deseada")
    
    # Estado y prioridad
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft',
                              verbose_name="Estado")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium',
                                verbose_name="Prioridad")
    
    # Relación con póliza resultante (si se convierte)
    resulting_policy = models.ForeignKey(Poliza, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='source_quote', verbose_name="Póliza Resultante")
    
    # Notas y observaciones
    notes = models.TextField(blank=True, verbose_name="Notas Internas")
    rejection_reason = models.TextField(blank=True, verbose_name="Motivo de Rechazo")
    
    # Auditoría
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name='quotes_requested', verbose_name="Solicitado por")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    # Historial
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    class Meta:
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['quote_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.quote_number} - {self.title}"
    
    @property
    def is_expired(self):
        """Verifica si la cotización ha expirado"""
        if not self.valid_until:
            return False
        return timezone.now().date() > self.valid_until
    
    @property
    def days_until_expiry(self):
        """Días restantes hasta que expire"""
        if self.valid_until:
            delta = (self.valid_until - timezone.now().date()).days
            return max(0, delta)
        return 0
    
    @property
    def best_option(self):
        """Retorna la opción con mejor precio"""
        return self.options.filter(is_recommended=True).first() or \
               self.options.order_by('premium_amount').first()
    
    def convert_to_policy(self, option, user):
        """Convierte la cotización en una póliza usando la opción seleccionada"""
        if self.status == 'converted':
            raise ValidationError('Esta cotización ya fue convertida a póliza.')
        
        policy = Poliza.objects.create(
            numero_poliza=f"POL-{self.quote_number}",
            compania_aseguradora=option.insurer,
            corredor_seguros=option.broker,
            tipo_poliza=self.policy_type,
            suma_asegurada=self.sum_insured,
            coberturas=option.coverage_offered or self.coverage_details,
            fecha_inicio=self.desired_start_date,
            fecha_fin=self.desired_end_date,
            creado_por=user,
            observaciones=f"Generada desde cotización {self.quote_number}"
        )
        
        self.resulting_policy = policy
        self.status = 'converted'
        self.save()
        
        return policy


class QuoteOption(models.Model):
    """
    Opciones de cotización de diferentes aseguradoras.
    Permite comparar múltiples ofertas para una misma solicitud.
    """
    # Relación con la cotización
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE,
                              related_name='options', verbose_name="Cotización")
    
    # Aseguradora y corredor
    insurer = models.ForeignKey(CompaniaAseguradora, on_delete=models.PROTECT,
                                related_name='quote_options', verbose_name="Aseguradora")
    broker = models.ForeignKey(CorredorSeguros, on_delete=models.PROTECT,
                               related_name='quote_options', verbose_name="Corredor")
    
    # Valores ofertados
    premium_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                         validators=[MinValueValidator(Decimal('0.01'))],
                                         verbose_name="Prima Anual")
    deductible = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'),
                                     verbose_name="Deducible")
    
    # Cobertura ofrecida
    coverage_offered = models.TextField(verbose_name="Coberturas Ofrecidas")
    exclusions = models.TextField(blank=True, verbose_name="Exclusiones")
    conditions = models.TextField(blank=True, verbose_name="Condiciones Especiales")
    
    # Documento de propuesta
    proposal_document = models.FileField(upload_to='quotes/proposals/%Y/%m/', null=True, blank=True,
                                         verbose_name="Documento de Propuesta")
    
    # Evaluación
    is_recommended = models.BooleanField(default=False, verbose_name="Recomendada")
    rating = models.PositiveSmallIntegerField(null=True, blank=True,
                                              validators=[MinValueValidator(1), MaxValueValidator(5)],
                                              verbose_name="Calificación (1-5)")
    evaluation_notes = models.TextField(blank=True, verbose_name="Notas de Evaluación")
    
    # Fechas
    received_date = models.DateField(verbose_name="Fecha de Recepción")
    valid_until = models.DateField(verbose_name="Válida Hasta")
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Opción de Cotización"
        verbose_name_plural = "Opciones de Cotización"
        ordering = ['premium_amount']

    def __str__(self):
        return f"{self.insurer.nombre} - ${self.premium_amount}"
    
    @property
    def premium_per_thousand(self):
        """Calcula la prima por cada mil de suma asegurada"""
        if self.quote.sum_insured and self.quote.sum_insured > 0:
            return (self.premium_amount / self.quote.sum_insured) * 1000
        return 0


class PolicyRenewal(models.Model):
    """
    Modelo para gestionar renovaciones de pólizas.
    Permite hacer seguimiento del proceso de renovación y comparar condiciones.
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('in_progress', 'En Proceso'),
        ('quoted', 'Cotizada'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ]
    
    DECISION_CHOICES = [
        ('renew_same', 'Renovar con Misma Aseguradora'),
        ('renew_different', 'Renovar con Otra Aseguradora'),
        ('not_renew', 'No Renovar'),
        ('pending', 'Pendiente de Decisión'),
    ]

    # Póliza a renovar
    original_policy = models.ForeignKey(Poliza, on_delete=models.PROTECT,
                                        related_name='renewals', verbose_name="Póliza Original")
    
    # Nueva póliza (si se completa la renovación)
    new_policy = models.ForeignKey(Poliza, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='renewal_source', verbose_name="Nueva Póliza")
    
    # Cotización asociada (opcional)
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='renewals', verbose_name="Cotización Asociada")
    
    # Identificación
    renewal_number = models.CharField(max_length=100, unique=True, verbose_name="Número de Renovación")
    
    # Fechas del proceso
    notification_date = models.DateField(verbose_name="Fecha de Notificación")
    due_date = models.DateField(verbose_name="Fecha Límite de Renovación")
    decision_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Decisión")
    completion_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Completado")
    
    # Valores comparativos
    original_premium = models.DecimalField(max_digits=15, decimal_places=2,
                                           verbose_name="Prima Original")
    proposed_premium = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                           verbose_name="Prima Propuesta")
    final_premium = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                        verbose_name="Prima Final")
    
    # Cambios en cobertura
    coverage_changes = models.TextField(blank=True, verbose_name="Cambios en Coberturas")
    
    # Estado y decisión
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                              verbose_name="Estado")
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='pending',
                                verbose_name="Decisión")
    decision_reason = models.TextField(blank=True, verbose_name="Justificación de Decisión")
    
    # Notificaciones
    reminder_sent = models.BooleanField(default=False, verbose_name="Recordatorio Enviado")
    reminder_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Recordatorio")
    
    # Notas
    notes = models.TextField(blank=True, verbose_name="Notas")
    
    # Auditoría
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='renewals_created', verbose_name="Creado por")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='renewals_approved', verbose_name="Aprobado por")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    # Historial
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    class Meta:
        verbose_name = "Renovación de Póliza"
        verbose_name_plural = "Renovaciones de Pólizas"
        ordering = ['-due_date']
        indexes = [
            models.Index(fields=['renewal_number']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.renewal_number} - {self.original_policy.numero_poliza}"
    
    @property
    def days_until_due(self):
        """Días restantes hasta la fecha límite"""
        if self.due_date:
            delta = (self.due_date - timezone.now().date()).days
            return delta
        return 0
    
    @property
    def is_overdue(self):
        """Verifica si la renovación está vencida"""
        return self.days_until_due < 0 and self.status not in ['completed', 'cancelled']
    
    @property
    def premium_change_percentage(self):
        """Calcula el porcentaje de cambio en la prima"""
        if self.original_premium and self.proposed_premium and self.original_premium > 0:
            return ((self.proposed_premium - self.original_premium) / self.original_premium) * 100
        return 0
    
    def complete_renewal(self, new_policy, user):
        """Completa el proceso de renovación"""
        self.new_policy = new_policy
        self.status = 'completed'
        self.completion_date = timezone.now().date()
        self.final_premium = new_policy.facturas.aggregate(
            total=models.Sum('subtotal')
        )['total'] or self.proposed_premium
        self.save()


class PaymentApproval(models.Model):
    """
    Modelo para el workflow de aprobación de pagos.
    Implementa niveles de aprobación según el monto.
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
    ]
    
    APPROVAL_LEVEL_CHOICES = [
        ('level_1', 'Nivel 1 - Operativo'),
        ('level_2', 'Nivel 2 - Supervisión'),
        ('level_3', 'Nivel 3 - Gerencial'),
        ('level_4', 'Nivel 4 - Directivo'),
    ]

    # Relación con el pago
    payment = models.ForeignKey(Pago, on_delete=models.CASCADE,
                                related_name='approvals', verbose_name="Pago")
    
    # Nivel de aprobación
    approval_level = models.CharField(max_length=20, choices=APPROVAL_LEVEL_CHOICES,
                                      verbose_name="Nivel de Aprobación")
    required_level = models.CharField(max_length=20, choices=APPROVAL_LEVEL_CHOICES,
                                      verbose_name="Nivel Requerido")
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                              verbose_name="Estado")
    
    # Aprobador
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='payment_approvals', verbose_name="Aprobador")
    
    # Fechas
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Decisión")
    
    # Comentarios
    request_notes = models.TextField(blank=True, verbose_name="Notas de Solicitud")
    decision_notes = models.TextField(blank=True, verbose_name="Notas de Decisión")
    
    # Firma digital (checkbox de confirmación)
    digital_signature = models.BooleanField(default=False, 
                                            verbose_name="Firma Digital/Confirmación")

    class Meta:
        verbose_name = "Aprobación de Pago"
        verbose_name_plural = "Aprobaciones de Pagos"
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['approval_level']),
        ]

    def __str__(self):
        return f"Aprobación {self.payment} - {self.get_status_display()}"
    
    @classmethod
    def get_required_level(cls, amount):
        """Determina el nivel de aprobación requerido según el monto"""
        # Umbrales configurables (podrían venir de ConfiguracionSistema)
        if amount >= Decimal('50000'):
            return 'level_4'
        elif amount >= Decimal('20000'):
            return 'level_3'
        elif amount >= Decimal('5000'):
            return 'level_2'
        return 'level_1'
    
    def approve(self, user, notes=''):
        """Aprueba el pago"""
        self.status = 'approved'
        self.approver = user
        self.decided_at = timezone.now()
        self.decision_notes = notes
        self.digital_signature = True
        self.save()
        
        # Aprobar el pago si tiene todas las aprobaciones necesarias
        if self._all_approvals_complete():
            self.payment.estado = 'aprobado'
            self.payment.save()
    
    def reject(self, user, notes=''):
        """Rechaza el pago"""
        self.status = 'rejected'
        self.approver = user
        self.decided_at = timezone.now()
        self.decision_notes = notes
        self.save()
        
        # Rechazar el pago
        self.payment.estado = 'rechazado'
        self.payment.save()
    
    def _all_approvals_complete(self):
        """Verifica si todas las aprobaciones requeridas están completas"""
        pending = PaymentApproval.objects.filter(
            payment=self.payment,
            status='pending'
        ).exists()
        return not pending


# ==================== MODELOS DE CATÁLOGO DE RAMOS (JERARQUÍA) ====================

class TipoRamo(models.Model):
    """
    Nivel más alto de la jerarquía de clasificación de riesgos.
    Ejemplo: Ramos Generales, Ramos de Vida, etc.
    """
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Tipo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    es_predefinido = models.BooleanField(default=False, verbose_name="Es Predefinido",
                                         help_text="Los tipos predefinidos no pueden eliminarse")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Tipo de Ramo"
        verbose_name_plural = "Tipos de Ramo"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def delete(self, *args, **kwargs):
        if self.es_predefinido:
            raise ValidationError("No se puede eliminar un tipo de ramo predefinido.")
        super().delete(*args, **kwargs)


class GrupoRamo(models.Model):
    """
    Segundo nivel de la jerarquía. Representa la categoría de póliza.
    Pertenece a un TipoRamo.
    Ejemplos: Póliza de Vehículos, Póliza de Incendio, Responsabilidad Civil, etc.
    """
    tipo_ramo = models.ForeignKey(TipoRamo, on_delete=models.PROTECT,
                                  related_name='grupos', verbose_name="Tipo de Ramo")
    codigo = models.CharField(max_length=50, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Grupo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    es_predefinido = models.BooleanField(default=False, verbose_name="Es Predefinido",
                                         help_text="Los grupos predefinidos no pueden eliminarse")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden",
                                        help_text="Orden de visualización")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Grupo de Ramo"
        verbose_name_plural = "Grupos de Ramo"
        ordering = ['tipo_ramo', 'orden', 'nombre']
        unique_together = ['tipo_ramo', 'codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def delete(self, *args, **kwargs):
        if self.es_predefinido:
            raise ValidationError("No se puede eliminar un grupo de ramo predefinido.")
        super().delete(*args, **kwargs)


class SubgrupoRamo(models.Model):
    """
    Tercer nivel de la jerarquía. Clasificación específica del objeto asegurado.
    Pertenece a un GrupoRamo.
    Ejemplos: Vehículo Liviano, Equipo Electrónico, Incendio, etc.
    """
    grupo_ramo = models.ForeignKey(GrupoRamo, on_delete=models.PROTECT,
                                   related_name='subgrupos', verbose_name="Grupo de Ramo")
    codigo = models.CharField(max_length=50, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Subgrupo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    es_predefinido = models.BooleanField(default=False, verbose_name="Es Predefinido",
                                         help_text="Los subgrupos predefinidos no pueden eliminarse")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden",
                                        help_text="Orden de visualización")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Subgrupo de Ramo"
        verbose_name_plural = "Subgrupos de Ramo"
        ordering = ['grupo_ramo', 'orden', 'nombre']
        unique_together = ['grupo_ramo', 'codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return f"{self.grupo_ramo.codigo}/{self.codigo} - {self.nombre}"

    def delete(self, *args, **kwargs):
        if self.es_predefinido:
            raise ValidationError("No se puede eliminar un subgrupo de ramo predefinido.")
        super().delete(*args, **kwargs)

    @property
    def nombre_completo(self):
        """Retorna la ruta completa: Tipo > Grupo > Subgrupo"""
        return f"{self.grupo_ramo.tipo_ramo.nombre} > {self.grupo_ramo.nombre} > {self.nombre}"


# Alias para compatibilidad con código existente (deprecado)
Ramo = GrupoRamo
SubtipoRamo = SubgrupoRamo


# ==================== MODELO BIEN ASEGURADO ====================

class BienAsegurado(models.Model):
    """
    Modelo UNIFICADO que representa un bien asegurado específico.
    Actúa como pivote entre la Póliza (contrato) y el SubgrupoRamo (clasificación).
    
    El siniestro se relaciona con el BienAsegurado, no directamente con la Póliza,
    porque el evento de pérdida ocurre sobre un objeto específico.
    
    NOTA: Este modelo unifica BienAsegurado + InsuredAsset (deprecado).
    Todos los bienes deben crearse usando este modelo.
    """
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('dado_de_baja', 'Dado de Baja'),
        ('siniestrado', 'Siniestrado'),
        ('transferido', 'Transferido'),
    ]
    
    CONDICION_CHOICES = [
        ('excelente', 'Excelente'),
        ('bueno', 'Bueno'),
        ('regular', 'Regular'),
        ('malo', 'Malo'),
    ]

    # Relación con Póliza (contrato al que pertenece)
    poliza = models.ForeignKey('Poliza', on_delete=models.PROTECT,
                               related_name='bienes_asegurados',
                               verbose_name="Póliza")
    
    # Relación con SubgrupoRamo (clasificación específica del bien)
    subgrupo_ramo = models.ForeignKey(SubgrupoRamo, on_delete=models.PROTECT,
                                      related_name='bienes_asegurados',
                                      verbose_name="Subgrupo de Ramo")
    
    # Identificación del bien
    codigo_bien = models.CharField(max_length=100, unique=True, verbose_name="Código del Bien",
                                   help_text="Identificador único del bien asegurado")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Bien")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    categoria = models.CharField(max_length=100, blank=True, verbose_name="Categoría",
                                 help_text="Categoría del bien (ej: Equipos de Cómputo, Vehículos)")
    
    # Características del bien
    marca = models.CharField(max_length=100, blank=True, verbose_name="Marca")
    modelo = models.CharField(max_length=100, blank=True, verbose_name="Modelo")
    serie = models.CharField(max_length=100, blank=True, verbose_name="Número de Serie")
    codigo_activo = models.CharField(max_length=100, blank=True, verbose_name="Código de Activo Fijo",
                                     help_text="Código institucional del activo fijo")
    anio_fabricacion = models.PositiveIntegerField(null=True, blank=True, 
                                                    verbose_name="Año de Fabricación")
    
    # Ubicación detallada
    ubicacion = models.CharField(max_length=300, blank=True, verbose_name="Ubicación General")
    edificio = models.CharField(max_length=100, blank=True, verbose_name="Edificio")
    piso = models.CharField(max_length=50, blank=True, verbose_name="Piso")
    departamento = models.CharField(max_length=100, blank=True, verbose_name="Departamento/Área")
    
    # Responsable
    responsable_custodio = models.ForeignKey('ResponsableCustodio', on_delete=models.SET_NULL,
                                             null=True, blank=True,
                                             related_name='bienes_asegurados',
                                             verbose_name="Responsable/Custodio")
    
    # Valores financieros
    valor_compra = models.DecimalField(max_digits=15, decimal_places=2,
                                       null=True, blank=True,
                                       validators=[MinValueValidator(Decimal('0.01'))],
                                       verbose_name="Valor de Compra")
    valor_actual = models.DecimalField(max_digits=15, decimal_places=2,
                                       null=True, blank=True,
                                       validators=[MinValueValidator(Decimal('0.00'))],
                                       verbose_name="Valor Actual (Depreciado)")
    valor_asegurado = models.DecimalField(max_digits=15, decimal_places=2,
                                          validators=[MinValueValidator(Decimal('0.01'))],
                                          verbose_name="Valor Asegurado")
    valor_comercial = models.DecimalField(max_digits=15, decimal_places=2,
                                          null=True, blank=True,
                                          validators=[MinValueValidator(Decimal('0.00'))],
                                          verbose_name="Valor Comercial")
    
    # Estado y condición
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, 
                              default='activo', verbose_name="Estado")
    condicion = models.CharField(max_length=20, choices=CONDICION_CHOICES,
                                 default='bueno', verbose_name="Condición Física")
    
    # Fechas
    fecha_adquisicion = models.DateField(null=True, blank=True, verbose_name="Fecha de Adquisición")
    fecha_garantia = models.DateField(null=True, blank=True, verbose_name="Vencimiento de Garantía")
    
    # Imagen y QR
    imagen = models.ImageField(upload_to='bienes/imagenes/%Y/%m/', null=True, blank=True,
                               verbose_name="Imagen del Bien")
    codigo_qr = models.CharField(max_length=200, blank=True, verbose_name="Código QR",
                                 help_text="Código QR para identificación rápida")
    
    # Observaciones
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Grupo de bienes (opcional, para agrupar bienes relacionados)
    grupo_bienes = models.ForeignKey('GrupoBienes', on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='bienes_asegurados',
                                     verbose_name="Grupo de Bienes")
    
    # Auditoría
    activo = models.BooleanField(default=True, verbose_name="Activo")
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='bienes_creados', verbose_name="Creado por")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    # Historial de cambios
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    # Manager personalizado (centraliza reglas de negocio)
    objects = BienAseguradoManager()

    class Meta:
        verbose_name = "Bien Asegurado"
        verbose_name_plural = "Bienes Asegurados"
        ordering = ['poliza', 'nombre']
        indexes = [
            models.Index(fields=['codigo_bien']),
            models.Index(fields=['poliza', 'estado']),
            models.Index(fields=['subgrupo_ramo']),
            models.Index(fields=['codigo_activo']),
        ]

    def __str__(self):
        return f"{self.codigo_bien} - {self.nombre}"

    @property
    def clasificacion_completa(self):
        """Retorna la clasificación completa del bien: Tipo > Grupo > Subgrupo"""
        return self.subgrupo_ramo.nombre_completo

    @property
    def tiene_siniestros(self):
        """Verifica si el bien tiene siniestros asociados"""
        return self.siniestros.exists()

    @property
    def total_siniestros(self):
        """Retorna el número total de siniestros del bien"""
        return self.siniestros.count()


class DetallePolizaRamo(models.Model):
    """
    Modelo para el desglose financiero por ramo de una póliza.
    Contiene los cálculos detallados de primas, contribuciones, impuestos y retenciones.
    """
    poliza = models.ForeignKey('Poliza', on_delete=models.CASCADE,
                               related_name='detalles_ramo', verbose_name="Póliza")
    grupo_ramo = models.ForeignKey(GrupoRamo, on_delete=models.PROTECT,
                                   related_name='detalles_poliza', verbose_name="Grupo de Ramo")
    subgrupo_ramo = models.ForeignKey(SubgrupoRamo, on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                      related_name='detalles_poliza', verbose_name="Subgrupo de Ramo")

    # Información de facturación
    numero_factura = models.CharField(max_length=100, blank=True, verbose_name="N° Factura")
    documento_contable = models.CharField(max_length=100, blank=True, verbose_name="Doc. Contable")

    # Valores financieros base
    suma_asegurada = models.DecimalField(max_digits=15, decimal_places=2,
                                         validators=[MinValueValidator(Decimal('0.00'))],
                                         default=Decimal('0.00'),
                                         verbose_name="Suma Asegurada")
    total_prima = models.DecimalField(max_digits=15, decimal_places=2,
                                      validators=[MinValueValidator(Decimal('0.00'))],
                                      default=Decimal('0.00'),
                                      verbose_name="Prima Total")

    # Contribuciones (calculadas automáticamente)
    contribucion_superintendencia = models.DecimalField(max_digits=15, decimal_places=2,
                                                        default=Decimal('0.00'),
                                                        verbose_name="Contribución Superintendencia (3.5%)")
    emision = models.DecimalField(max_digits=15, decimal_places=2,
                                  default=Decimal('0.00'),
                                  verbose_name="Emisión")
    seguro_campesino = models.DecimalField(max_digits=15, decimal_places=2,
                                           default=Decimal('0.00'),
                                           verbose_name="Seguro Campesino (0.5%)")

    # Base imponible e IVA
    base_imponible = models.DecimalField(max_digits=15, decimal_places=2,
                                         default=Decimal('0.00'),
                                         verbose_name="Base Imponible")
    iva = models.DecimalField(max_digits=15, decimal_places=2,
                              default=Decimal('0.00'),
                              verbose_name="IVA (15%)")
    total_facturado = models.DecimalField(max_digits=15, decimal_places=2,
                                          default=Decimal('0.00'),
                                          verbose_name="Total Facturado")

    # Retenciones (aplican si es gran contribuyente)
    retencion_prima = models.DecimalField(max_digits=15, decimal_places=2,
                                          default=Decimal('0.00'),
                                          verbose_name="Retención Prima (1%)")
    retencion_iva = models.DecimalField(max_digits=15, decimal_places=2,
                                        default=Decimal('0.00'),
                                        verbose_name="Retención IVA (100%)")

    # Valor final
    valor_por_pagar = models.DecimalField(max_digits=15, decimal_places=2,
                                          default=Decimal('0.00'),
                                          verbose_name="Valor por Pagar")

    # Observaciones
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    # Historial
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    class Meta:
        verbose_name = "Detalle de Póliza por Ramo"
        verbose_name_plural = "Detalles de Póliza por Ramo"
        ordering = ['poliza', 'grupo_ramo__nombre']
        indexes = [
            models.Index(fields=['poliza', 'grupo_ramo']),
        ]

    def __str__(self):
        return f"{self.poliza.numero_poliza} - {self.grupo_ramo.nombre}"

    def save(self, *args, **kwargs):
        """Calcula automáticamente los valores derivados antes de guardar"""
        self.calcular_valores()
        super().save(*args, **kwargs)

    @staticmethod
    def calcular_derechos_emision(valor_prima: Decimal) -> Decimal:
        """
        Calcula los derechos de emisión según tabla escalonada.
        Cálculo puro sin dependencias de servicios.
        
        La tabla se obtiene de ConfiguracionSistema (TABLA_TASAS_EMISION).
        Valores por defecto si no hay configuración:
          0 - 250      -> 0.50
          251 - 500    -> 1.00
          501 - 1000   -> 3.00
          1001 - 2000  -> 5.00
          2001 - 4000  -> 7.00
          > 4001       -> 9.00
        """
        # Intentar obtener tabla de configuración
        tabla_config = ConfiguracionSistema.get_config('TABLA_TASAS_EMISION', None)
        
        if tabla_config and isinstance(tabla_config, list):
            tabla = tabla_config
        else:
            # Valores por defecto
            tabla = [
                {'limite': 250, 'tasa': '0.50'},
                {'limite': 500, 'tasa': '1.00'},
                {'limite': 1000, 'tasa': '3.00'},
                {'limite': 2000, 'tasa': '5.00'},
                {'limite': 4000, 'tasa': '7.00'},
                {'limite': None, 'tasa': '9.00'},
            ]
        
        for rango in tabla:
            limite = rango.get('limite')
            tasa = Decimal(str(rango.get('tasa', '0')))
            
            if limite is None or valor_prima <= Decimal(str(limite)):
                return tasa
        
        # Fallback al último valor
        return Decimal(str(tabla[-1].get('tasa', '9.00')))

    def calcular_valores(self):
        """Calcula todos los valores financieros derivados"""
        # Obtener porcentajes de configuración
        pct_super = ConfiguracionSistema.get_config('PORCENTAJE_SUPERINTENDENCIA', Decimal('0.035'))
        pct_campesino = ConfiguracionSistema.get_config('PORCENTAJE_SEGURO_CAMPESINO', Decimal('0.005'))

        # Calcular contribuciones sobre la prima
        self.contribucion_superintendencia = self.total_prima * pct_super
        self.seguro_campesino = self.total_prima * pct_campesino

        # Calcular derechos de emisión según tabla escalonada
        self.emision = self.calcular_derechos_emision(self.total_prima)

        # Calcular base imponible (Prima + Contribuciones + Emisión)
        self.base_imponible = (
            self.total_prima +
            self.contribucion_superintendencia +
            self.seguro_campesino +
            self.emision
        )

        # Calcular IVA (15%)
        self.iva = self.base_imponible * Decimal('0.15')

        # Calcular total facturado
        self.total_facturado = self.base_imponible + self.iva

        # Calcular retenciones (solo si la póliza es de gran contribuyente)
        if self.poliza_id and self.poliza.es_gran_contribuyente:
            self.retencion_prima = self.total_prima * Decimal('0.01')
            self.retencion_iva = self.iva  # 100% del IVA
        else:
            self.retencion_prima = Decimal('0.00')
            self.retencion_iva = Decimal('0.00')

        # Calcular valor por pagar
        self.valor_por_pagar = self.total_facturado - self.retencion_prima - self.retencion_iva


# ==================== MODELO GRUPO DE BIENES ====================

class GrupoBienes(models.Model):
    """
    Modelo para agrupar bienes asegurados.
    Permite organizar bienes por categoría, ubicación o responsable.
    """
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Grupo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    grupo_ramo = models.ForeignKey(GrupoRamo, on_delete=models.PROTECT,
                                   related_name='grupos_bienes', verbose_name="Grupo de Ramo")
    subgrupo_ramo = models.ForeignKey(SubgrupoRamo, on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                      related_name='grupos_bienes', verbose_name="Subgrupo de Ramo")
    responsable = models.ForeignKey(ResponsableCustodio, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='grupos_bienes', verbose_name="Responsable")
    poliza = models.ForeignKey('Poliza', on_delete=models.SET_NULL,
                               null=True, blank=True,
                               related_name='grupos_bienes', verbose_name="Póliza")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='grupos_bienes_creados', verbose_name="Creado por")

    class Meta:
        verbose_name = "Grupo de Bienes"
        verbose_name_plural = "Grupos de Bienes"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['grupo_ramo']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return self.nombre

    @property
    def total_bienes(self):
        """Retorna el total de bienes en el grupo"""
        return self.bienes.count()

    @property
    def valor_total(self):
        """Retorna el valor total de los bienes del grupo"""
        return self.bienes.aggregate(
            total=models.Sum('current_value')
        )['total'] or Decimal('0.00')


class CalendarEvent(models.Model):
    """
    Modelo para eventos del calendario.
    Centraliza vencimientos y fechas importantes.
    """
    EVENT_TYPE_CHOICES = [
        ('policy_expiry', 'Vencimiento de Póliza'),
        ('invoice_due', 'Vencimiento de Factura'),
        ('renewal_due', 'Fecha Límite de Renovación'),
        ('claim_deadline', 'Plazo de Siniestro'),
        ('quote_expiry', 'Expiración de Cotización'),
        ('meeting', 'Reunión'),
        ('reminder', 'Recordatorio'),
        ('other', 'Otro'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]

    # Información del evento
    title = models.CharField(max_length=200, verbose_name="Título")
    description = models.TextField(blank=True, verbose_name="Descripción")
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES,
                                  verbose_name="Tipo de Evento")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium',
                                verbose_name="Prioridad")
    
    # Fechas
    start_date = models.DateField(verbose_name="Fecha de Inicio")
    end_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Fin")
    all_day = models.BooleanField(default=True, verbose_name="Todo el Día")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Hora de Inicio")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Hora de Fin")
    
    # Relaciones opcionales (para eventos automáticos)
    policy = models.ForeignKey(Poliza, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='calendar_events', verbose_name="Póliza")
    invoice = models.ForeignKey(Factura, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='calendar_events', verbose_name="Factura")
    renewal = models.ForeignKey(PolicyRenewal, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='calendar_events', verbose_name="Renovación")
    claim = models.ForeignKey(Siniestro, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='calendar_events', verbose_name="Siniestro")
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='calendar_events', verbose_name="Cotización")
    
    # Notificaciones
    reminder_days = models.PositiveIntegerField(default=7,
                                                verbose_name="Días de Anticipación para Recordatorio")
    reminder_sent = models.BooleanField(default=False, verbose_name="Recordatorio Enviado")
    
    # Estado
    is_completed = models.BooleanField(default=False, verbose_name="Completado")
    is_auto_generated = models.BooleanField(default=False, verbose_name="Generado Automáticamente")
    
    # Auditoría
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='calendar_events_created', verbose_name="Creado por")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Evento de Calendario"
        verbose_name_plural = "Eventos de Calendario"
        ordering = ['start_date', 'start_time']
        indexes = [
            models.Index(fields=['start_date']),
            models.Index(fields=['event_type']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"{self.title} - {self.start_date}"
    
    @property
    def days_until(self):
        """Días hasta el evento"""
        delta = (self.start_date - timezone.now().date()).days
        return delta
    
    @property
    def is_overdue(self):
        """Verifica si el evento ya pasó"""
        return self.start_date < timezone.now().date() and not self.is_completed
    
    @property
    def color(self):
        """Retorna el color del evento según tipo y prioridad"""
        colors = {
            'policy_expiry': '#ef4444',      # Rojo
            'invoice_due': '#f59e0b',        # Naranja
            'renewal_due': '#8b5cf6',        # Púrpura
            'claim_deadline': '#ec4899',     # Rosa
            'quote_expiry': '#06b6d4',       # Cyan
            'meeting': '#3b82f6',            # Azul
            'reminder': '#10b981',           # Verde
            'other': '#6b7280',              # Gris
        }
        return colors.get(self.event_type, '#6b7280')
    
    @classmethod
    def generate_policy_events(cls, policy):
        """Genera eventos de calendario para una póliza"""
        # Evento de vencimiento
        event, created = cls.objects.get_or_create(
            policy=policy,
            event_type='policy_expiry',
            defaults={
                'title': f'Vencimiento: {policy.numero_poliza}',
                'description': f'Vence la póliza {policy.numero_poliza} de {policy.compania_aseguradora}',
                'start_date': policy.fecha_fin,
                'priority': 'high',
                'is_auto_generated': True,
            }
        )
        return event


# ==================== MODELO SINIESTRO EMAIL ====================

class SiniestroEmail(models.Model):
    """
    Modelo para almacenar los datos de siniestros extraídos de correos electrónicos.
    Permite guardar la información aunque no se pueda crear el siniestro automáticamente.
    """
    ESTADO_PROCESAMIENTO_CHOICES = [
        ('pendiente', 'Pendiente de Revisión'),
        ('procesado', 'Procesado - Siniestro Creado'),
        ('error', 'Error en Procesamiento'),
        ('descartado', 'Descartado'),
    ]

    # Información del correo
    email_id = models.CharField(max_length=100, verbose_name="ID del Correo")
    email_subject = models.CharField(max_length=500, verbose_name="Asunto del Correo")
    email_from = models.CharField(max_length=300, verbose_name="Remitente")
    email_date = models.DateTimeField(null=True, blank=True, verbose_name="Fecha del Correo")
    email_body = models.TextField(blank=True, verbose_name="Cuerpo del Correo")

    # Datos extraídos del reporte
    responsable_nombre = models.CharField(max_length=300, verbose_name="Nombre del Responsable")
    fecha_reporte = models.CharField(max_length=50, verbose_name="Fecha de Reporte (texto)")
    problema = models.TextField(verbose_name="Descripción del Problema")
    causa = models.TextField(verbose_name="Causa del Daño")

    # Datos del equipo
    periferico = models.CharField(max_length=200, verbose_name="Tipo de Periférico")
    marca = models.CharField(max_length=200, verbose_name="Marca")
    modelo = models.CharField(max_length=200, verbose_name="Modelo")
    serie = models.CharField(max_length=200, verbose_name="Número de Serie")
    codigo_activo = models.CharField(max_length=200, blank=True, verbose_name="Código de Activo")

    # Estado del procesamiento
    estado_procesamiento = models.CharField(
        max_length=20, 
        choices=ESTADO_PROCESAMIENTO_CHOICES, 
        default='pendiente',
        verbose_name="Estado de Procesamiento"
    )
    mensaje_procesamiento = models.TextField(blank=True, verbose_name="Mensaje de Procesamiento")

    # Relaciones (se llenan si se puede procesar automáticamente)
    activo_encontrado = models.ForeignKey(
        'BienAsegurado', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='siniestros_email',
        verbose_name="Activo Encontrado"
    )
    siniestro_creado = models.ForeignKey(
        'Siniestro', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='origen_email',
        verbose_name="Siniestro Creado"
    )
    responsable_encontrado = models.ForeignKey(
        'ResponsableCustodio', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='siniestros_email',
        verbose_name="Responsable Encontrado"
    )

    # Auditoría
    fecha_recepcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Recepción")
    fecha_procesamiento = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Procesamiento")
    procesado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='siniestros_email_procesados',
        verbose_name="Procesado por"
    )

    class Meta:
        verbose_name = "Siniestro por Email"
        verbose_name_plural = "Siniestros por Email"
        ordering = ['-fecha_recepcion']
        indexes = [
            models.Index(fields=['serie']),
            models.Index(fields=['estado_procesamiento']),
            models.Index(fields=['email_id']),
        ]

    def __str__(self):
        return f"Email: {self.email_subject[:50]} - {self.get_estado_procesamiento_display()}"

    def buscar_activo_por_serie(self):
        """Busca un activo en el sistema por número de serie."""
        if not self.serie:
            return None
        
        try:
            activo = BienAsegurado.objects.filter(
                serie__iexact=self.serie.strip()
            ).first()
            return activo
        except Exception:
            return None

    def buscar_responsable(self):
        """Busca un responsable por nombre (búsqueda parcial)."""
        if not self.responsable_nombre:
            return None
        
        try:
            # Buscar coincidencia exacta primero
            responsable = ResponsableCustodio.objects.filter(
                nombre__iexact=self.responsable_nombre.strip()
            ).first()
            
            if not responsable:
                # Buscar coincidencia parcial
                responsable = ResponsableCustodio.objects.filter(
                    nombre__icontains=self.responsable_nombre.strip().split()[0]
                ).first()
            
            return responsable
        except Exception:
            return None

    def crear_siniestro_automatico(self):
        """
        Intenta crear un siniestro automáticamente si se encuentra el activo.
        
        Returns:
            tuple: (siniestro_creado, mensaje)
        """
        from django.utils import timezone
        from datetime import datetime
        
        # Buscar activo
        activo = self.buscar_activo_por_serie()
        self.activo_encontrado = activo
        
        if not activo:
            self.estado_procesamiento = 'pendiente'
            self.mensaje_procesamiento = (
                f"No se encontró activo con número de serie '{self.serie}'. "
                "Requiere revisión manual para asignar póliza."
            )
            self.save()
            return None, self.mensaje_procesamiento
        
        # Verificar que el activo tenga póliza
        if not activo.poliza:
            self.estado_procesamiento = 'pendiente'
            self.mensaje_procesamiento = (
                f"Activo encontrado ({activo.codigo_activo}) pero no tiene póliza asignada. "
                "Requiere revisión manual."
            )
            self.save()
            return None, self.mensaje_procesamiento
        
        # Buscar o usar el custodio del activo
        responsable = self.buscar_responsable() or activo.responsable_custodio
        self.responsable_encontrado = responsable
        
        # Buscar tipo de siniestro "daño" por defecto
        tipo_siniestro = TipoSiniestro.objects.filter(nombre='daño').first()
        if not tipo_siniestro:
            tipo_siniestro = TipoSiniestro.objects.first()
        
        if not tipo_siniestro:
            self.estado_procesamiento = 'error'
            self.mensaje_procesamiento = "No existe ningún tipo de siniestro en el sistema."
            self.save()
            return None, self.mensaje_procesamiento
        
        # Parsear fecha del reporte
        fecha_siniestro = timezone.now()
        if self.fecha_reporte:
            try:
                fecha_siniestro = timezone.make_aware(
                    datetime.strptime(self.fecha_reporte.strip(), '%d/%m/%Y')
                )
            except ValueError:
                pass  # Usar fecha actual si no se puede parsear
        
        # Generar número de siniestro
        from django.db.models import Max
        ultimo = Siniestro.objects.aggregate(Max('id'))['id__max'] or 0
        numero_siniestro = f"SIN-EMAIL-{timezone.now().year}-{str(ultimo + 1).zfill(5)}"
        
        try:
            # Crear el siniestro
            siniestro = Siniestro.objects.create(
                poliza=activo.poliza,
                bien_asegurado=activo,
                numero_siniestro=numero_siniestro,
                tipo_siniestro=tipo_siniestro,
                fecha_siniestro=fecha_siniestro,
                bien_nombre=f"{self.periferico} {self.marca}".strip(),
                bien_modelo=self.modelo,
                bien_serie=self.serie,
                bien_marca=self.marca,
                bien_codigo_activo=activo.codigo_activo or '',
                responsable_custodio=responsable,
                ubicacion=activo.ubicacion or "Ver correo original",
                causa=self.causa,
                descripcion_detallada=self.problema,
                monto_estimado=activo.valor_actual or activo.valor_asegurado,
                estado='registrado',
            )
            
            self.siniestro_creado = siniestro
            self.estado_procesamiento = 'procesado'
            self.fecha_procesamiento = timezone.now()
            self.mensaje_procesamiento = (
                f"Siniestro {numero_siniestro} creado exitosamente. "
                f"Póliza: {activo.poliza.numero_poliza}"
            )
            self.save()
            
            # Generar checklist de documentos automáticamente
            self._generar_checklist(siniestro)
            
            return siniestro, self.mensaje_procesamiento
            
        except Exception as e:
            self.estado_procesamiento = 'error'
            self.mensaje_procesamiento = f"Error al crear siniestro: {str(e)}"
            self.save()
            return None, self.mensaje_procesamiento
    
    def _generar_checklist(self, siniestro):
        """
        Genera el checklist de documentos requeridos para el siniestro.
        Usa las configuraciones activas del tipo de siniestro o genéricas.
        """
        from app.models import ChecklistSiniestro, ChecklistSiniestroConfig
        
        # Buscar configuraciones para el tipo de siniestro o genéricas
        configs = ChecklistSiniestroConfig.objects.filter(activo=True)
        
        if siniestro.tipo_siniestro:
            # Primero buscar específicas del tipo
            configs_tipo = configs.filter(tipo_siniestro=siniestro.tipo_siniestro)
            if configs_tipo.exists():
                configs = configs_tipo
            else:
                # Buscar genéricas (tipo "General")
                configs = configs.filter(tipo_siniestro__nombre='General')
        
        # Crear items del checklist
        for config in configs.order_by('orden'):
            ChecklistSiniestro.objects.get_or_create(
                siniestro=siniestro,
                config_item=config,
                defaults={'completado': False}
            )


# ==================== SISTEMA DE RESPALDOS ====================

class BackupRegistro(models.Model):
    """
    Modelo para registrar y gestionar los backups del sistema.
    Permite rastrear el historial de respaldos y restauraciones.
    """
    TIPO_CHOICES = [
        ('base_datos', 'Base de Datos'),
        ('completo', 'Completo (BD + Media)'),
        ('media', 'Solo Media'),
        ('restauracion', 'Restauración'),
        ('automatico', 'Automático Programado'),
    ]
    
    ESTADO_CHOICES = [
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
        ('eliminado', 'Eliminado'),
    ]
    
    FRECUENCIA_CHOICES = [
        ('manual', 'Manual'),
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
    ]
    
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Archivo")
    ruta = models.TextField(verbose_name="Ruta del Archivo")
    tamaño = models.BigIntegerField(default=0, verbose_name="Tamaño (bytes)")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='base_datos', verbose_name="Tipo")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='en_progreso', verbose_name="Estado")
    comprimido = models.BooleanField(default=False, verbose_name="Comprimido")
    formato = models.CharField(max_length=10, default='json', verbose_name="Formato")
    frecuencia = models.CharField(max_length=20, choices=FRECUENCIA_CHOICES, default='manual', verbose_name="Frecuencia")
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_expiracion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Expiración")
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='backups_creados', verbose_name="Creado Por"
    )
    
    # Información adicional
    notas = models.TextField(blank=True, verbose_name="Notas")
    error_mensaje = models.TextField(blank=True, verbose_name="Mensaje de Error")
    
    # Estadísticas
    duracion_segundos = models.IntegerField(default=0, verbose_name="Duración (segundos)")
    registros_respaldados = models.IntegerField(default=0, verbose_name="Registros Respaldados")
    
    class Meta:
        verbose_name = "Registro de Backup"
        verbose_name_plural = "Registros de Backups"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['tipo', 'estado']),
            models.Index(fields=['fecha_creacion']),
        ]
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()}) - {self.fecha_creacion.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def tamaño_legible(self):
        """Retorna el tamaño en formato legible."""
        size = self.tamaño
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.2f} {unit}'
            size /= 1024
        return f'{size:.2f} TB'
    
    @property
    def archivo_existe(self):
        """Verifica si el archivo de backup existe."""
        from pathlib import Path
        return Path(self.ruta).exists()
    
    @classmethod
    def limpiar_antiguos(cls, dias_retener=30):
        """
        Elimina backups más antiguos que los días especificados.
        Mantiene al menos los últimos 5 backups.
        """
        from datetime import timedelta
        from pathlib import Path
        
        fecha_limite = timezone.now() - timedelta(days=dias_retener)
        
        # Obtener backups antiguos (excepto los últimos 5)
        backups_antiguos = cls.objects.filter(
            fecha_creacion__lt=fecha_limite,
            estado='completado'
        ).exclude(
            pk__in=cls.objects.filter(estado='completado').order_by('-fecha_creacion')[:5].values_list('pk', flat=True)
        )
        
        eliminados = 0
        for backup in backups_antiguos:
            try:
                # Eliminar archivo físico
                archivo = Path(backup.ruta)
                if archivo.exists():
                    archivo.unlink()
                
                # Marcar como eliminado
                backup.estado = 'eliminado'
                backup.save()
                eliminados += 1
            except Exception:
                pass
        
        return eliminados
    
    @classmethod
    def obtener_estadisticas(cls):
        """Obtiene estadísticas de backups."""
        from django.db.models import Sum, Avg, Count
        
        return {
            'total': cls.objects.count(),
            'completados': cls.objects.filter(estado='completado').count(),
            'fallidos': cls.objects.filter(estado='fallido').count(),
            'tamaño_total': cls.objects.filter(estado='completado').aggregate(
                total=Sum('tamaño')
            )['total'] or 0,
            'ultimo_backup': cls.objects.filter(
                estado='completado', 
                tipo__in=['base_datos', 'completo', 'automatico']
            ).first(),
            'duracion_promedio': cls.objects.filter(
                estado='completado'
            ).aggregate(
                promedio=Avg('duracion_segundos')
            )['promedio'] or 0,
        }


class ConfiguracionBackup(models.Model):
    """
    Configuración para backups automáticos del sistema.
    """
    activo = models.BooleanField(default=True, verbose_name="Backup Automático Activo")
    frecuencia = models.CharField(
        max_length=20,
        choices=BackupRegistro.FRECUENCIA_CHOICES,
        default='diario',
        verbose_name="Frecuencia"
    )
    hora_ejecucion = models.TimeField(
        default='02:00',
        verbose_name="Hora de Ejecución",
        help_text="Hora del día para ejecutar el backup automático"
    )
    dias_retener = models.IntegerField(
        default=30,
        verbose_name="Días de Retención",
        help_text="Número de días para mantener los backups antiguos"
    )
    incluir_media = models.BooleanField(
        default=False,
        verbose_name="Incluir Archivos Media"
    )
    comprimir = models.BooleanField(
        default=True,
        verbose_name="Comprimir Backup"
    )
    notificar_email = models.EmailField(
        blank=True,
        verbose_name="Email de Notificación",
        help_text="Email para notificar sobre el estado de los backups"
    )
    ultimo_backup = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Último Backup Exitoso"
    )
    
    class Meta:
        verbose_name = "Configuración de Backup"
        verbose_name_plural = "Configuraciones de Backup"
    
    def __str__(self):
        return f"Configuración de Backup ({'Activo' if self.activo else 'Inactivo'})"
    
    @classmethod
    def get_config(cls):
        """Obtiene o crea la configuración de backup."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config
