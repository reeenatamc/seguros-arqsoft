from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from datetime import timedelta
import re

from simple_history.models import HistoricalRecords

from .validators import validate_document


# ==================== CONSTANTES Y VALIDADORES ====================

validador_ruc = RegexValidator(
    regex=r'^\d{13}$',
    message='El RUC debe contener exactamente 13 dígitos numéricos.',
    code='invalid_ruc'
)


# ==================== MODELOS ====================

class ConfiguracionSistema(models.Model):
    clave = models.CharField(max_length=100, unique=True, verbose_name="Clave")
    valor = models.CharField(max_length=255, verbose_name="Valor")
    tipo = models.CharField(max_length=20, choices=[
        ('decimal', 'Decimal'),
        ('entero', 'Entero'),
        ('texto', 'Texto'),
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
        Validaciones de negocio para configuraciones sensibles.
        En particular, se validan los porcentajes financieros críticos.
        """
        super().clean()

        # Validar porcentajes de contribuciones financieras
        claves_porcentaje = {
            'PORCENTAJE_SUPERINTENDENCIA',
            'PORCENTAJE_SEGURO_CAMPESINO',
        }

        if self.clave in claves_porcentaje:
            # Debe ser de tipo decimal
            if self.tipo != 'decimal':
                raise ValidationError({
                    'tipo': 'Este parámetro debe ser de tipo "decimal".',
                })

            try:
                valor_decimal = Decimal(self.valor)
            except (ArithmeticError, ValueError, TypeError):
                raise ValidationError({
                    'valor': 'El valor debe ser un número decimal válido.',
                })

            # Rango seguro: entre 0.0 y 0.1 (0% a 10%)
            if not (Decimal('0.0') <= valor_decimal <= Decimal('0.1')):
                raise ValidationError({
                    'valor': (
                        'El porcentaje debe estar entre 0.0 y 0.1 '
                        '(por ejemplo, 0.035 para 3.5%).'
                    )
                })

    def get_valor_tipado(self):
        if self.tipo == 'decimal':
            return Decimal(self.valor)
        elif self.tipo == 'entero':
            return int(self.valor)
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
                'valor': 'Cargo del Firmante',
                'tipo': 'texto',
                'descripcion': 'Cargo que aparecerá como firmante en cartas y recibos',
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
    # Relación opcional con brokers autorizados
    brokers = models.ManyToManyField(
        'CorredorSeguros',
        related_name='companias_aseguradas',
        verbose_name="Brokers autorizados",
        blank=True,
        help_text="Listado de brokers con convenio para esta aseguradora.",
    )

    class Meta:
        verbose_name = "Compañía Aseguradora"
        verbose_name_plural = "Compañías Aseguradoras"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class CorredorSeguros(models.Model):
    """Modelo para los corredores de seguros"""
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre del Corredor")
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
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


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
    
    # Coberturas y sumas
    suma_asegurada = models.DecimalField(max_digits=15, decimal_places=2, 
                                        validators=[MinValueValidator(Decimal('0.01'))],
                                        verbose_name="Suma Asegurada")
    coberturas = models.TextField(verbose_name="Coberturas Detalladas")
    
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

    def clean(self):
        """
        Validación personalizada de negocio:
          - Evitar duplicidad de pólizas con fechas superpuestas.
          - Validar coherencia entre compañía aseguradora y corredor, si hay brokers configurados.
        """
        super().clean()

        if not self.fecha_inicio or not self.fecha_fin:
            return

        # Validar que fecha_inicio sea anterior a fecha_fin
        if self.fecha_inicio >= self.fecha_fin:
            raise ValidationError({
                'fecha_fin': 'La fecha de fin debe ser posterior a la fecha de inicio.'
            })

        # Buscar pólizas con el mismo número y fechas superpuestas
        query = Q(numero_poliza=self.numero_poliza) & (
            Q(fecha_inicio__lte=self.fecha_fin) &
            Q(fecha_fin__gte=self.fecha_inicio)
        )

        if self.pk:
            query &= ~Q(pk=self.pk)

        polizas_superpuestas = Poliza.objects.filter(query)

        if polizas_superpuestas.exists():
            primera_superpuesta = polizas_superpuestas.first()
            raise ValidationError({
                'numero_poliza': (
                    f'Ya existe una póliza con el número \"{self.numero_poliza}\" '
                    f'con fechas superpuestas: {primera_superpuesta.fecha_inicio} - '
                    f'{primera_superpuesta.fecha_fin}. '
                    f'No pueden existir dos pólizas con el mismo número vigentes al mismo tiempo.'
                )
            })

        # Validar coherencia aseguradora-broker si la compañía tiene brokers configurados
        if (
            self.compania_aseguradora_id
            and self.corredor_seguros_id
            and self.compania_aseguradora.brokers.exists()
        ):
            if self.corredor_seguros not in self.compania_aseguradora.brokers.all():
                raise ValidationError({
                    'corredor_seguros': (
                        'El corredor seleccionado no está configurado como broker autorizado '
                        'para esta compañía aseguradora.'
                    )
                })

    def save(self, *args, **kwargs):
        if self.fecha_inicio and self.fecha_fin:
            self.clean()
            self.actualizar_estado()
        super().save(*args, **kwargs)

    def actualizar_estado(self):
        try:
            if not self.fecha_inicio or not self.fecha_fin:
                return
            
            hoy = timezone.now().date()
            dias_alerta = ConfiguracionSistema.get_config('DIAS_ALERTA_VENCIMIENTO_POLIZA', 30)
            
            if self.fecha_fin < hoy:
                self.estado = 'vencida'
            elif self.fecha_inicio <= hoy and self.fecha_fin <= hoy + timedelta(days=dias_alerta):
                self.estado = 'por_vencer'
            elif self.fecha_inicio <= hoy <= self.fecha_fin:
                self.estado = 'vigente'
            elif hoy < self.fecha_inicio and self.estado != 'cancelada':
                self.estado = 'vigente'
        except (TypeError, AttributeError):
            pass

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
        """Retorna la prima total de todos los ramos"""
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

    def save(self, *args, **kwargs):
        """
        Sobrescribe save para calcular montos automáticamente.
        El estado se actualiza después del save inicial para evitar errores con relaciones.
        """
        # Calcular montos antes de guardar
        self.calcular_contribuciones()
        self.calcular_descuento_pronto_pago()
        self.calcular_monto_total()
        
        # Guardar primero para obtener PK si es nuevo
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        # Actualizar estado solo si ya existe (tiene pagos)
        if not es_nuevo:
            self._actualizar_estado_con_pagos()

    def calcular_contribuciones(self):
        porcentaje_super = ConfiguracionSistema.get_config('PORCENTAJE_SUPERINTENDENCIA', Decimal('0.035'))
        porcentaje_campesino = ConfiguracionSistema.get_config('PORCENTAJE_SEGURO_CAMPESINO', Decimal('0.005'))
        
        self.contribucion_superintendencia = self.subtotal * porcentaje_super
        self.contribucion_seguro_campesino = self.subtotal * porcentaje_campesino

    def calcular_descuento_pronto_pago(self):
        try:
            if not self.fecha_emision:
                self.descuento_pronto_pago = Decimal('0.00')
                return

            # Si no tiene PK aún, no puede acceder a relaciones inversas
            if not self.pk:
                self.descuento_pronto_pago = Decimal('0.00')
                return

            dias_limite = ConfiguracionSistema.get_config('DIAS_LIMITE_DESCUENTO_PRONTO_PAGO', 20)
            porcentaje_descuento = ConfiguracionSistema.get_config('PORCENTAJE_DESCUENTO_PRONTO_PAGO', Decimal('0.05'))

            # Buscar el primer pago aprobado asociado a la factura
            pago = self.pagos.filter(estado='aprobado').order_by('fecha_pago').first()

            if not pago or not pago.fecha_pago:
                # Sin pagos aprobados o sin fecha de pago => no aplica descuento
                self.descuento_pronto_pago = Decimal('0.00')
                return

            fecha_limite_descuento = self.fecha_emision + timedelta(days=dias_limite)

            # Regla de negocio: si la fecha de pago es <= fecha_emision + 20 días
            if pago.fecha_pago <= fecha_limite_descuento:
                self.descuento_pronto_pago = self.subtotal * porcentaje_descuento
            else:
                self.descuento_pronto_pago = Decimal('0.00')
        except (TypeError, AttributeError, ValueError):
            self.descuento_pronto_pago = Decimal('0.00')

    def calcular_monto_total(self):
        """
        Calcula el monto total de la factura sumando todos los componentes.
        """
        self.monto_total = (
            self.subtotal + 
            self.iva + 
            self.contribucion_superintendencia + 
            self.contribucion_seguro_campesino - 
            self.retenciones - 
            self.descuento_pronto_pago
        )
        
        # Asegurar que el monto total no sea negativo
        if self.monto_total < Decimal('0.00'):
            self.monto_total = Decimal('0.00')

    def _actualizar_estado_con_pagos(self):
        """
        Método privado para actualizar el estado basándose en pagos.
        Solo se llama después del save inicial para evitar errores.
        """
        # Calcular total pagado
        total_pagado = self._calcular_total_pagado()
        
        # Determinar nuevo estado
        if total_pagado >= self.monto_total:
            nuevo_estado = 'pagada'
        elif total_pagado > Decimal('0.00'):
            nuevo_estado = 'parcial'
        elif timezone.now().date() > self.fecha_vencimiento:
            nuevo_estado = 'vencida'
        else:
            nuevo_estado = 'pendiente'
        
        # Actualizar solo si cambió
        if nuevo_estado != self.estado:
            self.estado = nuevo_estado
            # Usar update para evitar recursión infinita
            Factura.objects.filter(pk=self.pk).update(estado=nuevo_estado)

    def _calcular_total_pagado(self):
        """Calcula el total de pagos aprobados."""
        if not self.pk:
            return Decimal('0.00')
        
        total = self.pagos.filter(estado='aprobado').aggregate(
            total=models.Sum('monto')
        )['total']
        
        return total if total is not None else Decimal('0.00')

    def actualizar_estado(self):
        """
        Método público para actualizar el estado.
        Puede ser llamado manualmente desde comandos de gestión.
        """
        if self.pk:
            self._actualizar_estado_con_pagos()

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

    def save(self, *args, **kwargs):
        """
        Guarda el pago y actualiza la factura (estado y descuento pronto pago)
        solo si es necesario.
        """
        super().save(*args, **kwargs)

        # Solo actualizar la factura si este pago está aprobado
        # Esto evita múltiples actualizaciones innecesarias
        if self.estado == 'aprobado' and self.factura_id:
            factura = self.factura
            # Recalcular descuento por pronto pago y montos totales
            factura.calcular_contribuciones()
            factura.calcular_descuento_pronto_pago()
            factura.calcular_monto_total()
            factura.actualizar_estado()
            factura.save(update_fields=[
                'contribucion_superintendencia',
                'contribucion_seguro_campesino',
                'descuento_pronto_pago',
                'monto_total',
                'estado',
            ])

    def delete(self, *args, **kwargs):
        """
        Al borrar un pago, se deben recalcular el descuento por pronto pago
        y los montos de la factura asociada.
        """
        factura = self.factura if self.factura_id else None
        super().delete(*args, **kwargs)

        if factura:
            factura.calcular_contribuciones()
            factura.calcular_descuento_pronto_pago()
            factura.calcular_monto_total()
            factura.actualizar_estado()
            factura.save(update_fields=[
                'contribucion_superintendencia',
                'contribucion_seguro_campesino',
                'descuento_pronto_pago',
                'monto_total',
                'estado',
            ])
    
    def clean(self):
        """Validaciones del pago."""
        super().clean()
        
        # Validar que el monto no exceda el saldo pendiente (con un pequeño margen)
        if self.factura_id and self.monto:
            saldo = self.factura.saldo_pendiente
            if self.pk:  # Si es una actualización, no contar este pago
                pago_anterior = Pago.objects.filter(pk=self.pk).first()
                if pago_anterior and pago_anterior.estado == 'aprobado':
                    saldo += pago_anterior.monto
            
            if self.monto > saldo + Decimal('0.01'):  # Margen de 1 centavo
                raise ValidationError({
                    'monto': f'El monto del pago (${self.monto}) excede el saldo pendiente (${saldo}).'
                })


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
        ('registrado', 'Registrado'),
        ('documentacion_pendiente', 'Documentación Pendiente'),
        ('enviado_aseguradora', 'Enviado a Aseguradora'),
        ('en_evaluacion', 'En Evaluación'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('liquidado', 'Liquidado'),
        ('cerrado', 'Cerrado'),
    ]

    # Relación con póliza
    poliza = models.ForeignKey(Poliza, on_delete=models.PROTECT, 
                              related_name='siniestros', verbose_name="Póliza")
    
    # Información del siniestro
    numero_siniestro = models.CharField(max_length=100, unique=True, 
                                       verbose_name="Número de Siniestro")
    tipo_siniestro = models.ForeignKey(TipoSiniestro, on_delete=models.PROTECT, 
                                      related_name='siniestros', verbose_name="Tipo de Siniestro")
    fecha_siniestro = models.DateTimeField(verbose_name="Fecha y Hora del Siniestro")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    # Información del bien asegurado
    bien_nombre = models.CharField(max_length=200, verbose_name="Nombre del Bien")
    bien_modelo = models.CharField(max_length=100, blank=True, verbose_name="Modelo")
    bien_serie = models.CharField(max_length=100, blank=True, verbose_name="Número de Serie")
    bien_marca = models.CharField(max_length=100, blank=True, verbose_name="Marca")
    bien_codigo_activo = models.CharField(max_length=100, blank=True, verbose_name="Código de Activo")
    
    # Detalles del siniestro
    responsable_custodio = models.ForeignKey(ResponsableCustodio, on_delete=models.PROTECT,
                                            related_name='siniestros', verbose_name="Responsable/Custodio")
    ubicacion = models.CharField(max_length=300, verbose_name="Ubicación del Siniestro")
    causa = models.TextField(verbose_name="Causa del Siniestro")
    descripcion_detallada = models.TextField(verbose_name="Descripción Detallada")
    
    # Montos
    monto_estimado = models.DecimalField(max_digits=15, decimal_places=2,
                                        validators=[MinValueValidator(Decimal('0.01'))],
                                        verbose_name="Monto Estimado del Daño")
    monto_indemnizado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                           verbose_name="Monto Indemnizado")

    # Nuevos campos de valoración del siniestro
    valor_reclamo = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                        verbose_name="Valor del Reclamo (según proforma)")
    deducible = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                    verbose_name="Deducible")
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

    class Meta:
        verbose_name = "Siniestro"
        verbose_name_plural = "Siniestros"
        ordering = ['-fecha_siniestro']
        indexes = [
            models.Index(fields=['numero_siniestro']),
            models.Index(fields=['estado', 'fecha_siniestro']),
        ]

    def __str__(self):
        return f"{self.numero_siniestro} - {self.bien_nombre}"

    def clean(self):
        """Validaciones del siniestro."""
        super().clean()
        
        # Validar que la fecha del siniestro no sea futura
        if self.fecha_siniestro:
            ahora = timezone.now()
            if self.fecha_siniestro > ahora:
                raise ValidationError({
                    'fecha_siniestro': 'La fecha del siniestro no puede ser futura.'
                })
        
        # Validar que el siniestro esté dentro del período de vigencia de la póliza
        if self.poliza_id and self.fecha_siniestro:
            fecha_sin = self.fecha_siniestro.date()
            if not (self.poliza.fecha_inicio <= fecha_sin <= self.poliza.fecha_fin):
                raise ValidationError({
                    'fecha_siniestro': (
                        f'El siniestro debe ocurrir dentro del período de vigencia de la póliza '
                        f'({self.poliza.fecha_inicio} - {self.poliza.fecha_fin}).'
                    )
                })
        
        # Validar coherencia de fechas de gestión
        if self.fecha_envio_aseguradora and self.fecha_respuesta_aseguradora:
            if self.fecha_respuesta_aseguradora < self.fecha_envio_aseguradora:
                raise ValidationError({
                    'fecha_respuesta_aseguradora': (
                        'La fecha de respuesta no puede ser anterior a la fecha de envío.'
                    )
                })
        
        # Validar que si está liquidado, tenga monto indemnizado
        if self.estado == 'liquidado' and not self.monto_indemnizado:
            raise ValidationError({
                'monto_indemnizado': 'Un siniestro liquidado debe tener un monto indemnizado.'
            })

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
    
    def clean(self):
        """Validar que el documento esté asociado al menos a una entidad."""
        super().clean()
        
        if not any([self.poliza_id, self.siniestro_id, self.factura_id]):
            raise ValidationError(
                'El documento debe estar asociado al menos a una póliza, siniestro o factura.'
            )
        
        # Validar que el tipo de documento sea coherente con la relación
        if self.tipo_documento == 'poliza' and not self.poliza_id:
            raise ValidationError({
                'tipo_documento': 'Un documento de tipo "Póliza" debe estar asociado a una póliza.'
            })
        
        if self.tipo_documento == 'factura' and not self.factura_id:
            raise ValidationError({
                'tipo_documento': 'Un documento de tipo "Factura" debe estar asociado a una factura.'
            })
    
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

    def clean(self):
        """Validar que el monto no exceda el saldo de la factura"""
        super().clean()
        if self.factura_id and self.monto:
            # Calcular total de notas de crédito existentes (excluyendo esta si es update)
            notas_existentes = NotaCredito.objects.filter(
                factura=self.factura,
                estado__in=['emitida', 'aplicada']
            )
            if self.pk:
                notas_existentes = notas_existentes.exclude(pk=self.pk)

            total_notas = notas_existentes.aggregate(
                total=models.Sum('monto')
            )['total'] or Decimal('0.00')

            if total_notas + self.monto > self.factura.monto_total:
                raise ValidationError({
                    'monto': 'El monto total de notas de crédito no puede exceder el monto de la factura.'
                })


# ==================== NUEVOS MODELOS (Código en inglés, interfaz en español) ====================

class InsuredAsset(models.Model):
    """
    Modelo para el inventario de bienes asegurados.
    Permite un control preciso de qué bienes están cubiertos por cada póliza.
    """
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('disposed', 'Dado de Baja'),
        ('transferred', 'Transferido'),
    ]

    CONDITION_CHOICES = [
        ('excellent', 'Excelente'),
        ('good', 'Bueno'),
        ('fair', 'Regular'),
        ('poor', 'Malo'),
    ]

    # Relaciones
    policy = models.ForeignKey(Poliza, on_delete=models.PROTECT,
                               related_name='insured_assets', verbose_name="Póliza",
                               null=True, blank=True)
    custodian = models.ForeignKey(ResponsableCustodio, on_delete=models.PROTECT,
                                  related_name='assigned_assets', verbose_name="Custodio/Responsable")
    grupo = models.ForeignKey('GrupoBienes', on_delete=models.SET_NULL,
                              null=True, blank=True,
                              related_name='bienes', verbose_name="Grupo de Bienes")
    
    # Identificación del bien
    asset_code = models.CharField(max_length=100, unique=True, verbose_name="Código de Activo")
    name = models.CharField(max_length=200, verbose_name="Nombre del Bien")
    description = models.TextField(blank=True, verbose_name="Descripción")
    category = models.CharField(max_length=100, verbose_name="Categoría")
    
    # Detalles técnicos
    brand = models.CharField(max_length=100, blank=True, verbose_name="Marca")
    model = models.CharField(max_length=100, blank=True, verbose_name="Modelo")
    serial_number = models.CharField(max_length=100, blank=True, verbose_name="Número de Serie")
    
    # Ubicación
    location = models.CharField(max_length=300, verbose_name="Ubicación")
    building = models.CharField(max_length=100, blank=True, verbose_name="Edificio")
    floor = models.CharField(max_length=50, blank=True, verbose_name="Piso")
    department = models.CharField(max_length=100, blank=True, verbose_name="Departamento")
    
    # Valores financieros
    purchase_value = models.DecimalField(max_digits=15, decimal_places=2,
                                         validators=[MinValueValidator(Decimal('0.01'))],
                                         verbose_name="Valor de Compra")
    current_value = models.DecimalField(max_digits=15, decimal_places=2,
                                        validators=[MinValueValidator(Decimal('0.00'))],
                                        verbose_name="Valor Actual")
    insured_value = models.DecimalField(max_digits=15, decimal_places=2,
                                        validators=[MinValueValidator(Decimal('0.00'))],
                                        null=True, blank=True, verbose_name="Valor Asegurado")
    
    # Fechas
    purchase_date = models.DateField(verbose_name="Fecha de Compra")
    warranty_expiry = models.DateField(null=True, blank=True, verbose_name="Vencimiento de Garantía")
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active',
                              verbose_name="Estado")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good',
                                 verbose_name="Condición")
    
    # Imagen/QR
    image = models.ImageField(upload_to='assets/images/%Y/%m/', null=True, blank=True,
                              verbose_name="Imagen")
    qr_code = models.CharField(max_length=200, blank=True, verbose_name="Código QR")
    
    # Auditoría
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   related_name='assets_created', verbose_name="Creado por")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")
    
    # Historial
    history = HistoricalRecords(
        verbose_name="Historial",
        verbose_name_plural="Historial de cambios"
    )

    class Meta:
        verbose_name = "Bien Asegurado"
        verbose_name_plural = "Bienes Asegurados"
        ordering = ['name']
        indexes = [
            models.Index(fields=['asset_code']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.asset_code} - {self.name}"
    
    @property
    def depreciation_percentage(self):
        """Calcula el porcentaje de depreciación"""
        if self.purchase_value and self.purchase_value > 0:
            return ((self.purchase_value - self.current_value) / self.purchase_value) * 100
        return 0
    
    @property
    def is_covered(self):
        """Verifica si el bien está cubierto por una póliza vigente"""
        if self.policy:
            return self.policy.esta_vigente
        return False
    
    @property
    def claims_count(self):
        """Retorna la cantidad de siniestros asociados a este bien"""
        return Siniestro.objects.filter(
            bien_codigo_activo=self.asset_code
        ).count()


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


# ==================== MODELOS DE RAMOS ====================

class Ramo(models.Model):
    """
    Modelo para los ramos de seguros.
    Permite categorizar las pólizas por tipo de cobertura específica.
    """
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Ramo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    es_predefinido = models.BooleanField(default=False, verbose_name="Es Predefinido")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Ramo"
        verbose_name_plural = "Ramos"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @classmethod
    def crear_ramos_predefinidos(cls):
        """Crea los ramos predefinidos del sistema"""
        ramos_predefinidos = [
            ('INC', 'Incendio'),
            ('LCI', 'Lucro cesante incendio'),
            ('LCR', 'Lucro cesante rotura de maquinaria'),
            ('ROB', 'Robo y Asalto'),
            ('RCV', 'Robo contenido y valores'),
            ('EEL', 'Equipo Electrónico'),
            ('MPR', 'Maquinaria de producción'),
            ('MPE', 'Maquinaria pesada'),
            ('TIM', 'Transporte importación'),
            ('TIN', 'Transporte Interno'),
            ('RC1', 'Responsabilidad civil 1era Capa'),
            ('RC2', 'Responsabilidad civil 2da Capa'),
            ('RCP', 'RC profesional'),
            ('RCD', 'RC Directores'),
            ('VLI', 'Vehículos livianos'),
            ('VPE', 'Vehículos pesados'),
            ('ACP', 'Accidentes personales'),
        ]

        for codigo, nombre in ramos_predefinidos:
            cls.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'es_predefinido': True,
                    'activo': True,
                }
            )


class SubtipoRamo(models.Model):
    """
    Modelo para subtipos de ramo.
    Proporciona granularidad adicional dentro de cada ramo.
    """
    ramo = models.ForeignKey(Ramo, on_delete=models.CASCADE,
                             related_name='subtipos', verbose_name="Ramo")
    codigo = models.CharField(max_length=50, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Subtipo")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")

    class Meta:
        verbose_name = "Subtipo de Ramo"
        verbose_name_plural = "Subtipos de Ramo"
        ordering = ['ramo__nombre', 'nombre']
        unique_together = ['ramo', 'codigo']

    def __str__(self):
        return f"{self.ramo.codigo}/{self.codigo} - {self.nombre}"


class DetallePolizaRamo(models.Model):
    """
    Modelo para el desglose financiero por ramo de una póliza.
    Contiene los cálculos detallados de primas, contribuciones, impuestos y retenciones.
    """
    poliza = models.ForeignKey('Poliza', on_delete=models.CASCADE,
                               related_name='detalles_ramo', verbose_name="Póliza")
    ramo = models.ForeignKey(Ramo, on_delete=models.PROTECT,
                             related_name='detalles_poliza', verbose_name="Ramo")
    subtipo_ramo = models.ForeignKey(SubtipoRamo, on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='detalles_poliza', verbose_name="Subtipo de Ramo")

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
        ordering = ['poliza', 'ramo__nombre']
        indexes = [
            models.Index(fields=['poliza', 'ramo']),
        ]

    def __str__(self):
        return f"{self.poliza.numero_poliza} - {self.ramo.nombre}"

    def save(self, *args, **kwargs):
        """Calcula automáticamente los valores derivados antes de guardar"""
        self.calcular_valores()
        super().save(*args, **kwargs)

    @staticmethod
    def calcular_derechos_emision(valor_prima: Decimal) -> Decimal:
        """
        Calcula los derechos de emisión según tabla escalonada:
          0 - 250      -> 0.50
          251 - 500    -> 1.00
          501 - 1000   -> 3.00
          1001 - 2000  -> 5.00
          2001 - 4000  -> 7.00
          > 4001       -> 9.00
        """
        if valor_prima <= Decimal('250'):
            return Decimal('0.50')
        elif valor_prima <= Decimal('500'):
            return Decimal('1.00')
        elif valor_prima <= Decimal('1000'):
            return Decimal('3.00')
        elif valor_prima <= Decimal('2000'):
            return Decimal('5.00')
        elif valor_prima <= Decimal('4000'):
            return Decimal('7.00')
        else:
            return Decimal('9.00')

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
    ramo = models.ForeignKey(Ramo, on_delete=models.PROTECT,
                             related_name='grupos_bienes', verbose_name="Ramo")
    subtipo_ramo = models.ForeignKey(SubtipoRamo, on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='grupos_bienes', verbose_name="Subtipo de Ramo")
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
            models.Index(fields=['ramo']),
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
