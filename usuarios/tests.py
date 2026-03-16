from django.test import TestCase

from .models import Usuario


class UsuarioModelTest(TestCase):
    def test_roles(self):
        admin = Usuario.objects.create_user(
            username='admin1', password='1234', tipo_usuario=Usuario.TipoUsuario.ADMINISTRADOR
        )
        self.assertTrue(admin.es_administrador)
        self.assertTrue(admin.puede_gestionar_equipos())
