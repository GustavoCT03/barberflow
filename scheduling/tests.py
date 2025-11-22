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
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from core.models import User, Nosotros, Barberia, Sucursal, Servicio, Barbero
from .models import Cita, Valoracion, WaitlistEntry

class CitaTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.cliente = User.objects.create_user(
            email='cliente@test.com',
            password='test123',
            nombre='Cliente Test',
            rol=User.Roles.CLIENTE
        )
        self.nosotros = Nosotros.objects.create(nombre='Test Barber', activo=True)
        self.barberia = Barberia.objects.create(nosotros=self.nosotros, nombre='Test', activa=True)
        self.sucursal = Sucursal.objects.create(barberia=self.barberia, nombre='Suc1', activo=True)
        self.servicio = Servicio.objects.create(
            barberia=self.barberia, nombre='Corte', precio=10000, duracion_minutos=30
        )
        user_barbero = User.objects.create_user(
            email='barbero@test.com', password='test123', nombre='Barbero', rol=User.Roles.BARBERO
        )
        self.barbero = Barbero.objects.create(
            nosotros=self.nosotros, user=user_barbero, nombre='Barbero', activo=True, sucursal_principal=self.sucursal
        )
    
    def test_crear_cita(self):
        """HU09: Cliente puede crear cita"""
        self.client.login(email='cliente@test.com', password='test123')
        fecha = timezone.now() + timedelta(days=1)
        response = self.client.post(reverse('scheduling:confirmar_reserva', args=[
            self.sucursal.id, self.servicio.id, self.barbero.id
        ]), {
            'fecha_hora': fecha.strftime('%Y-%m-%dT%H:%M:%S')
        })
        self.assertEqual(Cita.objects.count(), 1)
        cita = Cita.objects.first()
        self.assertEqual(cita.cliente, self.cliente)
        self.assertEqual(cita.estado, Cita.Estado.PENDIENTE)
    
    def test_cancelar_cita_2h(self):
        """HU12: Cliente puede cancelar con >2h de anticipación"""
        self.client.login(email='cliente@test.com', password='test123')
        fecha = timezone.now() + timedelta(hours=3)
        cita = Cita.objects.create(
            cliente=self.cliente,
            barbero=self.barbero,
            sucursal=self.sucursal,
            servicio=self.servicio,
            fecha_hora=fecha,
            precio=self.servicio.precio
        )
        response = self.client.post(reverse('scheduling:cancelar_cita', args=[cita.id]))
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.Estado.CANCELADA_CLIENTE)
    
    def test_valorar_cita(self):
        """HU17: Cliente puede valorar cita completada"""
        self.client.login(email='cliente@test.com', password='test123')
        cita = Cita.objects.create(
            cliente=self.cliente,
            barbero=self.barbero,
            sucursal=self.sucursal,
            servicio=self.servicio,
            fecha_hora=timezone.now() - timedelta(hours=1),
            precio=self.servicio.precio,
            estado=Cita.Estado.COMPLETADA
        )
        response = self.client.post(reverse('scheduling:valorar_cita', args=[cita.id]), {
            'puntuacion': 5,
            'comentario': 'Excelente servicio'
        })
        self.assertEqual(Valoracion.objects.count(), 1)
        val = Valoracion.objects.first()
        self.assertEqual(val.puntuacion, 5)
    
    def test_unirse_waitlist(self):
        """HU09: Cliente puede unirse a lista de espera"""
        self.client.login(email='cliente@test.com', password='test123')
        fecha_dia = (timezone.now() + timedelta(days=1)).date()
        response = self.client.post(reverse('scheduling:unirse_waitlist', args=[
            self.barbero.id, self.servicio.id
        ]), {
            'fecha_dia': fecha_dia
        })
        self.assertEqual(WaitlistEntry.objects.count(), 1)
        entry = WaitlistEntry.objects.first()
        self.assertTrue(entry.activo)
        self.assertFalse(entry.utilizado)