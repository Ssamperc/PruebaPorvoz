import random
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Reserva(models.Model):
    class EstadoReserva(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de Confirmación'
        CONFIRMADA = 'confirmada', 'Confirmada'
        EN_CURSO = 'en_curso', 'En Curso'
        COMPLETADA = 'completada', 'Completada'
        CANCELADA = 'cancelada', 'Cancelada'
        VENCIDA = 'vencida', 'Vencida'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_reserva = models.CharField(max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reservas',
        limit_choices_to={'tipo_usuario': 'cliente'},
    )
    equipo = models.ForeignKey('equipos.Equipo', on_delete=models.PROTECT, related_name='reservas')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)
    fecha_devolucion_real = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=EstadoReserva.choices, default=EstadoReserva.PENDIENTE)
    costo_alquiler = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deposito_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    costo_adicional = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    notas_cliente = models.TextField(blank=True)
    notas_admin = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmada_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['equipo', 'fecha_inicio', 'fecha_fin']),
            models.Index(fields=['numero_reserva']),
        ]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio >= self.fecha_fin:
            raise ValidationError('La fecha de inicio debe ser anterior a la fecha de fin')

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.numero_reserva:
            self.numero_reserva = 'RES-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        super().save(*args, **kwargs)

    def calcular_costo(self):
        self.costo_alquiler = self.equipo.calcular_precio(self.fecha_inicio, self.fecha_fin)
        self.save(update_fields=['costo_alquiler'])
        return self.costo_alquiler

    @property
    def costo_total(self):
        return self.costo_alquiler + self.costo_adicional

    @property
    def dias_alquiler(self):
        return (self.fecha_fin - self.fecha_inicio).days

    @property
    def puede_calificarse(self):
        return self.estado == self.EstadoReserva.COMPLETADA and not hasattr(self, 'calificacion')

    def confirmar_reserva(self):
        if self.estado != self.EstadoReserva.PENDIENTE:
            raise ValueError('Solo se pueden confirmar reservas pendientes')
        if not self.equipo.consultar_disponibilidad(self.fecha_inicio, self.fecha_fin):
            raise ValueError('El equipo no está disponible para estas fechas')
        self.estado = self.EstadoReserva.CONFIRMADA
        self.confirmada_at = timezone.now()
        self.save(update_fields=['estado', 'confirmada_at', 'updated_at'])
        if self.fecha_inicio <= timezone.now().date():
            self.equipo.marcar_como_rentado()

    def iniciar_alquiler(self):
        if self.estado != self.EstadoReserva.CONFIRMADA:
            raise ValueError('Solo se pueden iniciar reservas confirmadas')
        self.estado = self.EstadoReserva.EN_CURSO
        self.fecha_entrega_real = timezone.now()
        self.save(update_fields=['estado', 'fecha_entrega_real', 'updated_at'])
        self.equipo.marcar_como_rentado()

    def completar_alquiler(self):
        if self.estado != self.EstadoReserva.EN_CURSO:
            raise ValueError('Solo se pueden completar reservas en curso')
        self.estado = self.EstadoReserva.COMPLETADA
        self.fecha_devolucion_real = timezone.now()
        self.save(update_fields=['estado', 'fecha_devolucion_real', 'updated_at'])
        self.equipo.marcar_como_disponible()

        if self.fecha_devolucion_real.date() > self.fecha_fin:
            dias_retraso = (self.fecha_devolucion_real.date() - self.fecha_fin).days
            self.costo_adicional += self.equipo.precio_por_dia * Decimal('0.5') * dias_retraso
            self.save(update_fields=['costo_adicional', 'updated_at'])

    def cancelar_reserva(self):
        if self.estado in [self.EstadoReserva.COMPLETADA, self.EstadoReserva.CANCELADA]:
            raise ValueError('No se puede cancelar una reserva completada o ya cancelada')
        self.estado = self.EstadoReserva.CANCELADA
        self.save(update_fields=['estado', 'updated_at'])
        if self.equipo.estado == self.equipo.EstadoEquipo.RENTADO:
            self.equipo.marcar_como_disponible()


class Notificacion(models.Model):
    class TipoNotificacion(models.TextChoices):
        RESERVA_CONFIRMADA = 'reserva_confirmada', 'Reserva confirmada'
        RECORDATORIO_ENTREGA = 'recordatorio_entrega', 'Recordatorio de entrega'
        RECORDATORIO_DEVOLUCION = 'recordatorio_devolucion', 'Recordatorio de devolución'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=40, choices=TipoNotificacion.choices)
    mensaje = models.CharField(max_length=255)
    fecha_programada = models.DateTimeField()
    enviado = models.BooleanField(default=False)
    enviado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_programada']
        indexes = [models.Index(fields=['enviado', 'fecha_programada'])]


class CalificacionEquipo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='calificacion')
    equipo = models.ForeignKey('equipos.Equipo', on_delete=models.CASCADE, related_name='calificaciones')
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calificaciones')
    puntuacion = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        if self.puntuacion < 1 or self.puntuacion > 5:
            raise ValidationError('La puntuación debe estar entre 1 y 5')
        if self.reserva.estado != Reserva.EstadoReserva.COMPLETADA:
            raise ValidationError('Solo se puede calificar una reserva completada')
        if self.reserva.cliente_id != self.cliente_id:
            raise ValidationError('El cliente de la calificación debe coincidir con el de la reserva')
        if self.reserva.equipo_id != self.equipo_id:
            raise ValidationError('El equipo de la calificación debe coincidir con el de la reserva')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
