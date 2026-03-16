import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class TipoUsuario(models.TextChoices):
        CLIENTE = 'cliente', 'Cliente'
        ADMINISTRADOR = 'administrador', 'Administrador'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_usuario = models.CharField(max_length=20, choices=TipoUsuario.choices, default=TipoUsuario.CLIENTE)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)
    email_verificado = models.BooleanField(default=False)
    telefono_verificado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        full_name = self.get_full_name() or self.username
        return f'{full_name} ({self.get_tipo_usuario_display()})'

    @property
    def es_administrador(self):
        return self.tipo_usuario == self.TipoUsuario.ADMINISTRADOR

    @property
    def es_cliente(self):
        return self.tipo_usuario == self.TipoUsuario.CLIENTE

    def puede_gestionar_equipos(self):
        return self.es_administrador

    def puede_realizar_reservas(self):
        return self.es_cliente or self.es_administrador
