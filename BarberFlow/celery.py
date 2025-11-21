import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BarberFlow.settings")
app = Celery("BarberFlow")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(['scheduling'])  # fuerza descubrimiento de tareas

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    from scheduling.tasks import enviar_recordatorios, marcar_no_show_citas
    # Cada 5 minutos: recordatorios 2h antes
    sender.add_periodic_task(300.0, enviar_recordatorios.s(), name="recordatorios_2h")
    # Cada 10 minutos: marcar no show (gracia 15 min)
    sender.add_periodic_task(600.0, marcar_no_show_citas.s(), name="marcar_no_show")