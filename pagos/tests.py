from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from equipos.models import Categoria, Equipo
from reservas.models import Reserva
from usuarios.models import Usuario

from .models import Pago


class PagoModelTest(TestCase):
    def test_procesar_pago_manual(self):
        cliente = Usuario.objects.create_user(username='cliente2', password='1234', tipo_usuario=Usuario.TipoUsuario.CLIENTE)
        categoria = Categoria.objects.create(nombre='Compactación')
        equipo = Equipo.objects.create(
            nombre='Compactadora',
            descripcion='Compactadora liviana',
            categoria=categoria,
            codigo_interno='EQ-004',
            precio_por_dia=Decimal('40.00'),
        )
        inicio = timezone.now().date() + timedelta(days=1)
        reserva = Reserva.objects.create(cliente=cliente, equipo=equipo, fecha_inicio=inicio, fecha_fin=inicio + timedelta(days=2))
        pago = Pago.objects.create(
            reserva=reserva,
            usuario=cliente,
            monto=Decimal('80.00'),
            metodo_pago=Pago.MetodoPago.EFECTIVO,
        )

        resultado = pago.procesar_pago()

        self.assertTrue(resultado)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, Pago.EstadoPago.COMPLETADO)
