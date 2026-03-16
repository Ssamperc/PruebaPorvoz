from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from equipos.models import Categoria, Equipo
from usuarios.models import Usuario

from .models import Notificacion, Reserva
from .services import ReservaService


class ReservaServiceTest(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username='cliente1', password='1234', tipo_usuario=Usuario.TipoUsuario.CLIENTE
        )
        self.categoria = Categoria.objects.create(nombre='Energía')
        self.equipo = Equipo.objects.create(
            nombre='Generador',
            descripcion='Generador portátil',
            categoria=self.categoria,
            codigo_interno='EQ-003',
            precio_por_dia=Decimal('30.00'),
            deposito_garantia=Decimal('50.00'),
        )
        self.service = ReservaService()

    def test_crear_reserva_calcula_costo(self):
        inicio = timezone.now().date() + timedelta(days=2)
        fin = inicio + timedelta(days=2)

        reserva = self.service.crear_reserva(self.cliente, self.equipo, inicio, fin)

        self.assertEqual(reserva.costo_alquiler, Decimal('60.00'))
        self.assertEqual(reserva.deposito_pagado, Decimal('50.00'))
        self.assertEqual(reserva.estado, Reserva.EstadoReserva.PENDIENTE)

    def test_crear_notificaciones_reserva(self):
        inicio = timezone.now().date() + timedelta(days=3)
        fin = inicio + timedelta(days=2)
        reserva = self.service.crear_reserva(self.cliente, self.equipo, inicio, fin)
        reserva.estado = Reserva.EstadoReserva.CONFIRMADA
        reserva.save(update_fields=['estado'])

        self.service.crear_notificaciones_reserva(reserva)

        self.assertEqual(Notificacion.objects.filter(reserva=reserva).count(), 3)

    def test_registrar_calificacion_reserva_completada(self):
        inicio = timezone.now().date() + timedelta(days=4)
        fin = inicio + timedelta(days=2)
        reserva = self.service.crear_reserva(self.cliente, self.equipo, inicio, fin)
        reserva.estado = Reserva.EstadoReserva.COMPLETADA
        reserva.save(update_fields=['estado'])

        calificacion = self.service.registrar_calificacion(reserva, 5, 'Excelente estado')

        self.assertEqual(calificacion.puntuacion, 5)
        self.assertEqual(calificacion.reserva, reserva)
