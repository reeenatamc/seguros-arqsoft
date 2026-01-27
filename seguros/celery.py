import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seguros.settings")

app = Celery("seguros")

# Using a string here means the worker doesn't have to serialize

# the configuration object to child processes.

# - namespace='CELERY' means all celery-related configuration keys

#   should have a `CELERY_` prefix.

app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.

app.autodiscover_tasks()

# Configuración de tareas periódicas

app.conf.beat_schedule = {
    # Generar alertas todos los días a las 8:00 AM
    "generar-alertas-diarias": {
        "task": "app.tasks.generar_alertas_automaticas",
        "schedule": crontab(hour=8, minute=0),
    },
    # Enviar alertas por email todos los días a las 8:30 AM y 2:00 PM
    "enviar-alertas-email-manana": {
        "task": "app.tasks.enviar_alertas_email",
        "schedule": crontab(hour=8, minute=30),
    },
    "enviar-alertas-email-tarde": {
        "task": "app.tasks.enviar_alertas_email",
        "schedule": crontab(hour=14, minute=0),
    },
    # Actualizar estados de pólizas todos los días a las 7:00 AM
    "actualizar-estados-polizas": {
        "task": "app.tasks.actualizar_estados_polizas",
        "schedule": crontab(hour=7, minute=0),
    },
    # Actualizar estados de facturas cada 6 horas
    "actualizar-estados-facturas": {
        "task": "app.tasks.actualizar_estados_facturas",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Revisar inbox para respuestas del broker cada 5 minutos
    "revisar-inbox-broker": {
        "task": "app.tasks.revisar_inbox_broker",
        "schedule": crontab(minute="*/5"),
    },
    # Revisar inbox para recibos de indemnización cada 5 minutos
    "revisar-inbox-recibos": {
        "task": "app.tasks.revisar_inbox_recibos",
        "schedule": crontab(minute="*/5"),
    },
    # Verificar plazos de liquidación (72h) cada hora
    "verificar-plazos-liquidacion": {
        "task": "app.tasks.verificar_plazos_liquidacion",
        "schedule": crontab(minute=0),
    },
}

# Configuración de zona horaria

app.conf.timezone = "America/Guayaquil"


@app.task(bind=True, ignore_result=True)
def debug_task(self):

    print(f"Request: {self.request!r}")
