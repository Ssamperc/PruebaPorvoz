from django.contrib import admin

from .models import BloqueoDisponibilidad, Categoria, Equipo, ImagenEquipo

admin.site.register(Categoria)
admin.site.register(Equipo)
admin.site.register(ImagenEquipo)
admin.site.register(BloqueoDisponibilidad)
