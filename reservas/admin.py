from django.contrib import admin

from .models import CalificacionEquipo, Notificacion, Reserva

admin.site.register(Reserva)
admin.site.register(Notificacion)
admin.site.register(CalificacionEquipo)
