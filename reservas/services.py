from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from pagos.models import Pago

from .models import CalificacionEquipo, Notificacion, Reserva


class ReservaService:
    @transaction.atomic
    def crear_reserva(self, cliente, equipo, fecha_inicio, fecha_fin, notas_cliente=''):
        if fecha_inicio >= fecha_fin:
            raise ValueError('La fecha de inicio debe ser anterior a la fecha de fin')
        if fecha_inicio < timezone.now().date():
            raise ValueError('No se pueden hacer reservas para fechas pasadas')
        if not equipo.consultar_disponibilidad(fecha_inicio, fecha_fin):
            raise ValueError(f'El equipo {equipo.nombre} no está disponible para estas fechas')

        reserva = Reserva.objects.create(
            cliente=cliente,
            equipo=equipo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            notas_cliente=notas_cliente,
            deposito_pagado=equipo.deposito_garantia,
        )
        reserva.calcular_costo()
        return reserva

    @transaction.atomic
    def confirmar_reserva_con_pago(self, reserva, metodo_pago):
        pago_alquiler = Pago.objects.create(
            reserva=reserva,
            usuario=reserva.cliente,
            monto=reserva.costo_alquiler,
            tipo_pago=Pago.TipoPago.ALQUILER,
            metodo_pago=metodo_pago,
        )

        pago_deposito = None
        if reserva.equipo.deposito_garantia > 0:
            pago_deposito = Pago.objects.create(
                reserva=reserva,
                usuario=reserva.cliente,
                monto=reserva.equipo.deposito_garantia,
                tipo_pago=Pago.TipoPago.DEPOSITO,
                metodo_pago=metodo_pago,
            )

        if not pago_alquiler.procesar_pago() or (pago_deposito and not pago_deposito.procesar_pago()):
            raise ValueError('Error al procesar los pagos de la reserva')

        reserva.confirmar_reserva()
        self.crear_notificaciones_reserva(reserva)
        return reserva, pago_alquiler

    def obtener_reservas_proximas(self, dias=7):
        limite = timezone.now().date() + timedelta(days=dias)
        return Reserva.objects.filter(
            estado=Reserva.EstadoReserva.CONFIRMADA,
            fecha_inicio__gte=timezone.now().date(),
            fecha_inicio__lte=limite,
        ).select_related('cliente', 'equipo')

    def obtener_reservas_vencidas(self):
        return Reserva.objects.filter(
            estado=Reserva.EstadoReserva.EN_CURSO,
            fecha_fin__lt=timezone.now().date(),
        ).select_related('cliente', 'equipo')

    @transaction.atomic
    def crear_notificaciones_reserva(self, reserva):
        ahora = timezone.now()
        notificaciones = [
            Notificacion(
                usuario=reserva.cliente,
                reserva=reserva,
                tipo=Notificacion.TipoNotificacion.RESERVA_CONFIRMADA,
                mensaje=f'Tu reserva {reserva.numero_reserva} fue confirmada.',
                fecha_programada=ahora,
            )
        ]

        inicio_dt = timezone.make_aware(datetime.combine(reserva.fecha_inicio, time.min))
        fin_dt = timezone.make_aware(datetime.combine(reserva.fecha_fin, time.min))

        notificaciones.append(
            Notificacion(
                usuario=reserva.cliente,
                reserva=reserva,
                tipo=Notificacion.TipoNotificacion.RECORDATORIO_ENTREGA,
                mensaje=f'Recordatorio: tu alquiler de {reserva.equipo.nombre} inicia pronto.',
                fecha_programada=inicio_dt - timedelta(hours=24),
            )
        )
        notificaciones.append(
            Notificacion(
                usuario=reserva.cliente,
                reserva=reserva,
                tipo=Notificacion.TipoNotificacion.RECORDATORIO_DEVOLUCION,
                mensaje=f'Recordatorio: devuelve {reserva.equipo.nombre} en la fecha acordada.',
                fecha_programada=fin_dt - timedelta(hours=24),
            )
        )

        return Notificacion.objects.bulk_create(notificaciones)

    def obtener_notificaciones_pendientes(self):
        return Notificacion.objects.filter(enviado=False, fecha_programada__lte=timezone.now())

    @transaction.atomic
    def registrar_calificacion(self, reserva, puntuacion, comentario=''):
        if not reserva.puede_calificarse:
            raise ValueError('La reserva no se puede calificar')
        return CalificacionEquipo.objects.create(
            reserva=reserva,
            equipo=reserva.equipo,
            cliente=reserva.cliente,
            puntuacion=puntuacion,
            comentario=comentario,
        )
