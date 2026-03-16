import random
import string
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Pago(models.Model):
    class MetodoPago(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        TARJETA_CREDITO = 'tarjeta_credito', 'Tarjeta de Crédito'
        TARJETA_DEBITO = 'tarjeta_debito', 'Tarjeta de Débito'
        TRANSFERENCIA = 'transferencia', 'Transferencia Bancaria'
        PAYPAL = 'paypal', 'PayPal'
        STRIPE = 'stripe', 'Stripe'

    class EstadoPago(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        PROCESANDO = 'procesando', 'Procesando'
        COMPLETADO = 'completado', 'Completado'
        FALLIDO = 'fallido', 'Fallido'
        REEMBOLSADO = 'reembolsado', 'Reembolsado'

    class TipoPago(models.TextChoices):
        ALQUILER = 'alquiler', 'Pago de Alquiler'
        DEPOSITO = 'deposito', 'Depósito de Garantía'
        ADICIONAL = 'adicional', 'Cargo Adicional'
        REEMBOLSO = 'reembolso', 'Reembolso'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_transaccion = models.CharField(max_length=50, unique=True, editable=False)
    reserva = models.ForeignKey('reservas.Reserva', on_delete=models.PROTECT, related_name='pagos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tipo_pago = models.CharField(max_length=20, choices=TipoPago.choices, default=TipoPago.ALQUILER)
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
    estado = models.CharField(max_length=20, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    fecha_procesado = models.DateTimeField(null=True, blank=True)
    referencia_externa = models.CharField(max_length=200, blank=True)
    notas = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_pago']

    def save(self, *args, **kwargs):
        if not self.numero_transaccion:
            self.numero_transaccion = 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        super().save(*args, **kwargs)

    def procesar_pago(self):
        if self.estado != self.EstadoPago.PENDIENTE:
            raise ValueError('Solo se pueden procesar pagos pendientes')

        self.estado = self.EstadoPago.PROCESANDO
        self.save(update_fields=['estado', 'updated_at'])

        try:
            if self.metodo_pago == self.MetodoPago.STRIPE:
                resultado = self._procesar_con_stripe()
            elif self.metodo_pago == self.MetodoPago.PAYPAL:
                resultado = self._procesar_con_paypal()
            else:
                resultado = True

            if resultado:
                self.estado = self.EstadoPago.COMPLETADO
                self.fecha_procesado = timezone.now()
                self.save(update_fields=['estado', 'fecha_procesado', 'updated_at'])
                return True

            self.estado = self.EstadoPago.FALLIDO
            self.save(update_fields=['estado', 'updated_at'])
            return False
        except Exception as exc:
            self.estado = self.EstadoPago.FALLIDO
            self.notas = f'Error: {exc}'
            self.save(update_fields=['estado', 'notas', 'updated_at'])
            return False

    def _procesar_con_stripe(self):
        return True

    def _procesar_con_paypal(self):
        return True

    def reembolsar(self):
        if self.estado != self.EstadoPago.COMPLETADO:
            raise ValueError('Solo se pueden reembolsar pagos completados')
        pago_reembolso = Pago.objects.create(
            reserva=self.reserva,
            usuario=self.usuario,
            monto=abs(self.monto),
            tipo_pago=self.TipoPago.REEMBOLSO,
            metodo_pago=self.metodo_pago,
            estado=self.EstadoPago.COMPLETADO,
            notas=f'Reembolso de pago {self.numero_transaccion}',
        )
        self.estado = self.EstadoPago.REEMBOLSADO
        self.save(update_fields=['estado', 'updated_at'])
        return pago_reembolso
