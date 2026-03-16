from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'tipo_usuario', 'is_active', 'date_joined')
    list_filter = ('tipo_usuario', 'is_active', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        (
            'Información adicional',
            {
                'fields': (
                    'tipo_usuario',
                    'telefono',
                    'direccion',
                    'ciudad',
                    'codigo_postal',
                    'email_verificado',
                    'telefono_verificado',
                )
            },
        ),
    )
