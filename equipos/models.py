import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Categoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='categorias/', null=True, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


class Equipo(models.Model):
    class EstadoEquipo(models.TextChoices):
        DISPONIBLE = 'disponible', 'Disponible'
        RENTADO = 'rentado', 'Rentado'
        MANTENIMIENTO = 'mantenimiento', 'En Mantenimiento'
        FUERA_SERVICIO = 'fuera_servicio', 'Fuera de Servicio'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    descripcion = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='equipos')
    codigo_interno = models.CharField(max_length=50, unique=True)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True, unique=True, null=True)
    precio_por_dia = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    precio_por_semana = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_por_mes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deposito_garantia = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    estado = models.CharField(max_length=20, choices=EstadoEquipo.choices, default=EstadoEquipo.DISPONIBLE)
    disponible = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)
    especificaciones = models.JSONField(default=dict, blank=True)
    imagen_principal = models.ImageField(upload_to='equipos/%Y/%m/', null=True, blank=True)
    ultima_fecha_mantenimiento = models.DateField(null=True, blank=True)
    proxima_fecha_mantenimiento = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.codigo_interno})'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.nombre}-{self.codigo_interno}')
        super().save(*args, **kwargs)

    def consultar_disponibilidad(self, fecha_inicio, fecha_fin):
        if not self.disponible or not self.activo or self.estado != self.EstadoEquipo.DISPONIBLE:
            return False

        from reservas.models import Reserva

        reserva_solapada = self.reservas.filter(
            estado__in=[Reserva.EstadoReserva.CONFIRMADA, Reserva.EstadoReserva.EN_CURSO],
            fecha_inicio__lt=fecha_fin,
            fecha_fin__gt=fecha_inicio,
        ).exists()

        bloqueo_solapado = self.bloqueos_disponibilidad.filter(
            activo=True,
            fecha_inicio__lt=fecha_fin,
            fecha_fin__gt=fecha_inicio,
        ).exists()

        return not (reserva_solapada or bloqueo_solapado)

    def calcular_precio(self, fecha_inicio, fecha_fin):
        dias = (fecha_fin - fecha_inicio).days
        if dias <= 0:
            return Decimal('0.00')
        if dias >= 30 and self.precio_por_mes:
            meses, dias_restantes = divmod(dias, 30)
            return (self.precio_por_mes * meses) + (self.precio_por_dia * dias_restantes)
        if dias >= 7 and self.precio_por_semana:
            semanas, dias_restantes = divmod(dias, 7)
            return (self.precio_por_semana * semanas) + (self.precio_por_dia * dias_restantes)
        return self.precio_por_dia * dias

    def marcar_como_rentado(self):
        self.estado = self.EstadoEquipo.RENTADO
        self.disponible = False
        self.save(update_fields=['estado', 'disponible', 'updated_at'])

    def marcar_como_disponible(self):
        self.estado = self.EstadoEquipo.DISPONIBLE
        self.disponible = True
        self.save(update_fields=['estado', 'disponible', 'updated_at'])

    def requiere_mantenimiento(self):
        return bool(self.proxima_fecha_mantenimiento and timezone.now().date() >= self.proxima_fecha_mantenimiento)


class ImagenEquipo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='equipos/%Y/%m/')
    descripcion = models.CharField(max_length=200, blank=True)
    orden = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'created_at']


class BloqueoDisponibilidad(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='bloqueos_disponibilidad')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    motivo = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f'Bloqueo {self.equipo.nombre}: {self.motivo}'
