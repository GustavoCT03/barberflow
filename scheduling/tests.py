from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from core.models import User, Barbero, Sucursal, Servicio, Nosotros, Barberia
from scheduling.models import Cita, Valoracion

class ValoracionTest(TestCase):
    def setUp(self):
        nosotros = Nosotros.objects.create(nombre="Org")
        barberia = Barberia.objects.create(nosotros=nosotros, nombre="Central")
        sucursal = Sucursal.objects.create(barberia=barberia, nombre="Suc 1")
        self.u_cliente = User.objects.create_user(email="c@x.com", password="x", nombre="Cliente")
        u_barbero = User.objects.create_user(email="b@x.com", password="x", nombre="Barbero", rol=User.Roles.BARBERO)
        self.barbero = Barbero.objects.create(nosotros=nosotros, user=u_barbero, nombre="Barbero Uno")
        servicio = Servicio.objects.create(barberia=barberia, nombre="Corte", duracion_minutos=30, precio=10)
        self.cita = Cita.objects.create(
            cliente=self.u_cliente,
            barbero=self.barbero,
            sucursal=sucursal,
            servicio=servicio,
            fecha_hora=timezone.now() + timedelta(hours=1),
            precio=10,
            estado=Cita.Estado.COMPLETADA
        )

    def test_crear_valoracion(self):
        v = Valoracion.objects.create(
            cita=self.cita,
            cliente=self.u_cliente,
            barbero=self.barbero,
            puntuacion=5
        )
        self.assertEqual(v.puntuacion, 5)
        self.assertTrue(hasattr(self.cita, 'valoracion'))

# Create your tests here.
