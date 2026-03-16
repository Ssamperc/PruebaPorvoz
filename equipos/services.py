from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from reservas.models import Reserva

from .models import Equipo


class EquipoService:
    def buscar_equipos_disponibles(self, fecha_inicio, fecha_fin, categoria=None, precio_max=None):
        equipos = Equipo.objects.filter(activo=True, disponible=True, estado=Equipo.EstadoEquipo.DISPONIBLE)
        if categoria:
            equipos = equipos.filter(categoria=categoria)
        if precio_max:
            equipos = equipos.filter(precio_por_dia__lte=precio_max)
        ids_disponibles = [equipo.id for equipo in equipos if equipo.consultar_disponibilidad(fecha_inicio, fecha_fin)]
        return equipos.filter(id__in=ids_disponibles)

    def obtener_equipos_populares(self, limit=10):
        return Equipo.objects.annotate(total_reservas=Count('reservas')).order_by('-total_reservas')[:limit]

    def calcular_tasa_ocupacion(self, equipo, dias=30):
        fecha_inicio = timezone.now().date() - timedelta(days=dias)
        fecha_fin = timezone.now().date()
        reservas = Reserva.objects.filter(
            equipo=equipo,
            estado__in=[Reserva.EstadoReserva.CONFIRMADA, Reserva.EstadoReserva.COMPLETADA],
            fecha_inicio__gte=fecha_inicio,
            fecha_fin__lte=fecha_fin,
        )
        dias_rentados = sum(reserva.dias_alquiler for reserva in reservas)
        return min((dias_rentados / dias) * 100, 100.0)

    def generar_reporte_mantenimiento(self):
        return Equipo.objects.filter(
            Q(proxima_fecha_mantenimiento__lte=timezone.now().date())
            | Q(estado=Equipo.EstadoEquipo.MANTENIMIENTO)
        ).select_related('categoria')
