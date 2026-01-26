from django.core.management.base import BaseCommand

from app.models import ConfiguracionSistema





class Command(BaseCommand):

    help = 'Inicializa las configuraciones por defecto del sistema'



    def handle(self, *args, **options):

        self.stdout.write('Inicializando configuraciones...')

        ConfiguracionSistema.inicializar_valores_default()

        

        total = ConfiguracionSistema.objects.count()

        self.stdout.write(self.style.SUCCESS(f'✓ {total} configuraciones inicializadas'))

        

        for config in ConfiguracionSistema.objects.all():

            self.stdout.write(f'  {config.clave} = {config.valor}')

