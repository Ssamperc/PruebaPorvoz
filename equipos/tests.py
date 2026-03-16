from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import BloqueoDisponibilidad, Categoria, Equipo


class EquipoModelTest(TestCase):
    def test_calcular_precio_por_semana(self):
        categoria = Categoria.objects.create(nombre='Perforación')
        equipo = Equipo.objects.create(
            nombre='Taladro',
            descripcion='Taladro industrial',
            categoria=categoria,
            codigo_interno='EQ-001',
            precio_por_dia=Decimal('20.00'),
            precio_por_semana=Decimal('100.00'),
        )
        inicio = timezone.now().date()
        fin = inicio + timedelta(days=8)

        total = equipo.calcular_precio(inicio, fin)

        self.assertEqual(total, Decimal('120.00'))

    def test_consultar_disponibilidad_con_bloqueo(self):
        categoria = Categoria.objects.create(nombre='Corte')
        equipo = Equipo.objects.create(
            nombre='Cortadora',
            descripcion='Cortadora de concreto',
            categoria=categoria,
            codigo_interno='EQ-002',
            precio_por_dia=Decimal('50.00'),
        )
        inicio = timezone.now().date() + timedelta(days=1)
        fin = inicio + timedelta(days=3)
        BloqueoDisponibilidad.objects.create(
            equipo=equipo,
            fecha_inicio=inicio,
            fecha_fin=fin,
            motivo='Mantenimiento',
            activo=True,
        )

        self.assertFalse(equipo.consultar_disponibilidad(inicio, fin))
