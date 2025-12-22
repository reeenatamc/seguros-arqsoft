from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta


class CompaniaAseguradora(models.Model):
    """Modelo para las compañías aseguradoras"""
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre de la Compañía")
    ruc = models.CharField(max_length=13, unique=True, verbose_name="RUC")
    direccion = models.TextField(blank=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    contacto_nombre = models.CharField(max_length=200, blank=True, verbose_name="Nombre del Contacto")
    contacto_telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono del Contacto")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Compañía Aseguradora"
        verbose_name_plural = "Compañías Aseguradoras"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class CorredorSeguros(models.Model):
    """Modelo para los corredores de seguros"""
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre del Corredor")
    ruc = models.CharField(max_length=13, unique=True, verbose_name="RUC")
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
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='polizas_creadas', verbose_name="Creado por")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

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
        """Validación personalizada para evitar duplicidad de pólizas con fechas superpuestas"""
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_inicio >= self.fecha_fin:
                raise ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
            
            # Verificar duplicidad de pólizas con fechas superpuestas
            polizas_superpuestas = Poliza.objects.filter(
                numero_poliza=self.numero_poliza
            ).exclude(pk=self.pk)
            
            for poliza in polizas_superpuestas:
                if (self.fecha_inicio <= poliza.fecha_fin and self.fecha_fin >= poliza.fecha_inicio):
                    raise ValidationError(
                        f"Ya existe una póliza con el número {self.numero_poliza} "
                        f"con fechas de vigencia superpuestas: {poliza.fecha_inicio} - {poliza.fecha_fin}"
                    )

    def save(self, *args, **kwargs):
        self.clean()
        # Actualizar estado automáticamente
        self.actualizar_estado()
        super().save(*args, **kwargs)

    def actualizar_estado(self):
        """Actualiza el estado de la póliza según las fechas"""
        hoy = timezone.now().date()
        if self.fecha_fin < hoy:
            self.estado = 'vencida'
        elif self.fecha_fin <= hoy + timedelta(days=30):
            self.estado = 'por_vencer'
        elif self.fecha_inicio <= hoy <= self.fecha_fin:
            self.estado = 'vigente'

    @property
    def dias_para_vencer(self):
        """Retorna los días que faltan para que venza la póliza"""
        hoy = timezone.now().date()
        if self.fecha_fin > hoy:
            return (self.fecha_fin - hoy).days
        return 0

    @property
    def esta_vigente(self):
        """Verifica si la póliza está vigente"""
        hoy = timezone.now().date()
        return self.fecha_inicio <= hoy <= self.fecha_fin


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
        # Calcular contribuciones automáticamente
        self.calcular_contribuciones()
        # Calcular descuento por pronto pago si aplica
        self.calcular_descuento_pronto_pago()
        # Calcular monto total
        self.calcular_monto_total()
        # Actualizar estado
        self.actualizar_estado()
        super().save(*args, **kwargs)

    def calcular_contribuciones(self):
        """Calcula automáticamente las contribuciones (3.5% y 0.5%)"""
        self.contribucion_superintendencia = self.subtotal * Decimal('0.035')  # 3.5%
        self.contribucion_seguro_campesino = self.subtotal * Decimal('0.005')  # 0.5%

    def calcular_descuento_pronto_pago(self):
        """Calcula el descuento del 5% si se paga dentro de 20 días"""
        hoy = timezone.now().date()
        fecha_limite_descuento = self.fecha_emision + timedelta(days=20)
        
        if hoy <= fecha_limite_descuento and self.estado == 'pendiente':
            self.descuento_pronto_pago = self.subtotal * Decimal('0.05')  # 5%
        else:
            self.descuento_pronto_pago = Decimal('0.00')

    def calcular_monto_total(self):
        """Calcula el monto total de la factura"""
        self.monto_total = (
            self.subtotal + 
            self.iva + 
            self.contribucion_superintendencia + 
            self.contribucion_seguro_campesino - 
            self.retenciones - 
            self.descuento_pronto_pago
        )

    def actualizar_estado(self):
        """Actualiza el estado de la factura según los pagos y fechas"""
        total_pagado = sum(pago.monto for pago in self.pagos.filter(estado='aprobado'))
        
        if total_pagado >= self.monto_total:
            self.estado = 'pagada'
        elif total_pagado > 0:
            self.estado = 'parcial'
        elif timezone.now().date() > self.fecha_vencimiento:
            self.estado = 'vencida'
        else:
            self.estado = 'pendiente'

    @property
    def saldo_pendiente(self):
        """Retorna el saldo pendiente de pago"""
        total_pagado = sum(pago.monto for pago in self.pagos.filter(estado='aprobado'))
        return self.monto_total - total_pagado

    @property
    def puede_aplicar_descuento(self):
        """Verifica si todavía puede aplicarse el descuento por pronto pago"""
        hoy = timezone.now().date()
        fecha_limite = self.fecha_emision + timedelta(days=20)
        return hoy <= fecha_limite and self.estado == 'pendiente'


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

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Pago {self.referencia} - ${self.monto} ({self.fecha_pago})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar el estado de la factura después de guardar el pago
        self.factura.actualizar_estado()
        self.factura.save()


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
    responsable_custodio = models.CharField(max_length=200, verbose_name="Responsable/Custodio")
    ubicacion = models.CharField(max_length=300, verbose_name="Ubicación del Siniestro")
    causa = models.TextField(verbose_name="Causa del Siniestro")
    descripcion_detallada = models.TextField(verbose_name="Descripción Detallada")
    
    # Montos
    monto_estimado = models.DecimalField(max_digits=15, decimal_places=2, 
                                        validators=[MinValueValidator(Decimal('0.01'))],
                                        verbose_name="Monto Estimado del Daño")
    monto_indemnizado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                           verbose_name="Monto Indemnizado")
    
    # Estado y fechas de gestión
    estado = models.CharField(max_length=30, choices=ESTADO_CHOICES, default='registrado', 
                            verbose_name="Estado")
    fecha_envio_aseguradora = models.DateField(null=True, blank=True, 
                                              verbose_name="Fecha de Envío a Aseguradora")
    fecha_respuesta_aseguradora = models.DateField(null=True, blank=True, 
                                                  verbose_name="Fecha de Respuesta de Aseguradora")
    fecha_liquidacion = models.DateField(null=True, blank=True, verbose_name="Fecha de Liquidación")
    
    # Observaciones
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='siniestros_creados', verbose_name="Creado por")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

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

    @property
    def dias_desde_registro(self):
        """Retorna los días transcurridos desde el registro"""
        hoy = timezone.now()
        return (hoy - self.fecha_registro).days

    @property
    def requiere_alerta_documentacion(self):
        """Verifica si requiere alerta por documentación pendiente (más de 30 días)"""
        return self.dias_desde_registro > 30 and self.estado == 'documentacion_pendiente'

    @property
    def dias_espera_respuesta(self):
        """Retorna los días de espera de respuesta de la aseguradora"""
        if self.fecha_envio_aseguradora and not self.fecha_respuesta_aseguradora:
            hoy = timezone.now().date()
            return (hoy - self.fecha_envio_aseguradora).days
        return 0

    @property
    def requiere_alerta_respuesta(self):
        """Verifica si requiere alerta por falta de respuesta (más de 8 días hábiles)"""
        return self.dias_espera_respuesta > 8 and self.estado == 'enviado_aseguradora'


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
    archivo = models.FileField(upload_to='documentos/%Y/%m/', verbose_name="Archivo")
    
    # Auditoría
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='documentos_subidos', verbose_name="Subido por")

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_documento_display()})"


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
