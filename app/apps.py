from django.apps import AppConfig


class AppConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "app"

    def ready(self):
        """

        Se ejecuta al iniciar Django; aquí registramos las señales del app.

        """

        # Importar receptores de señales (no eliminar, necesario para que se registren)

        from . import signals  # noqa: F401
