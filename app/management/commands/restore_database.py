"""

Comando para restaurar la base de datos desde un backup.



Uso:

    python manage.py restore_database backup_20240115_120000.json

    python manage.py restore_database backup.json.gz --compressed

    python manage.py restore_database --list (lista backups disponibles)

    python manage.py restore_database --latest (restaura el más reciente)

"""



import os

import gzip

import shutil

from datetime import datetime

from pathlib import Path



from django.core.management.base import BaseCommand, CommandError

from django.conf import settings

from django.core.management import call_command

from django.db import connection





class Command(BaseCommand):

    help = 'Restaura la base de datos desde un archivo de backup'



    def add_arguments(self, parser):

        parser.add_argument(

            'backup_file',

            nargs='?',

            type=str,

            help='Archivo de backup a restaurar'

        )

        parser.add_argument(

            '--list', '-l',

            action='store_true',

            help='Listar backups disponibles'

        )

        parser.add_argument(

            '--latest',

            action='store_true',

            help='Restaurar el backup más reciente'

        )

        parser.add_argument(

            '--compressed', '-c',

            action='store_true',

            help='El archivo está comprimido con gzip'

        )

        parser.add_argument(

            '--no-confirm',

            action='store_true',

            help='No pedir confirmación antes de restaurar'

        )

        parser.add_argument(

            '--backup-first',

            action='store_true',

            default=True,

            help='Crear backup antes de restaurar (default: True)'

        )

        parser.add_argument(

            '--skip-backup',

            action='store_true',

            help='No crear backup antes de restaurar'

        )



    def handle(self, *args, **options):

        backup_dir = self._get_backup_dir()

        

        # Listar backups disponibles

        if options['list']:

            return self._list_backups(backup_dir)

        

        # Obtener archivo de backup

        if options['latest']:

            backup_file = self._get_latest_backup(backup_dir)

            if not backup_file:

                raise CommandError('No se encontraron backups disponibles')

        elif options['backup_file']:

            backup_file = self._resolve_backup_path(options['backup_file'], backup_dir)

        else:

            raise CommandError(

                'Debe especificar un archivo de backup o usar --latest\n'

                'Use --list para ver backups disponibles'

            )

        

        # Verificar que el archivo existe

        if not backup_file.exists():

            raise CommandError(f'Archivo de backup no encontrado: {backup_file}')

        

        # Confirmar restauración

        if not options['no_confirm']:

            self.stdout.write(

                self.style.WARNING(

                    f'\n¡ADVERTENCIA! Esta acción sobrescribirá TODOS los datos actuales.\n'

                    f'Archivo a restaurar: {backup_file}\n'

                    f'Tamaño: {self._format_size(backup_file.stat().st_size)}\n'

                )

            )

            confirm = input('¿Está seguro que desea continuar? (escriba "SI" para confirmar): ')

            if confirm.upper() != 'SI':

                self.stdout.write(self.style.NOTICE('Restauración cancelada.'))

                return

        

        try:

            # Crear backup de seguridad antes de restaurar

            if options['backup_first'] and not options['skip_backup']:

                self.stdout.write('Creando backup de seguridad...')

                call_command('backup_database', '--quiet', compress=True)

                self.stdout.write(self.style.SUCCESS('Backup de seguridad creado'))

            

            # Descomprimir si es necesario

            is_compressed = options['compressed'] or str(backup_file).endswith('.gz')

            if is_compressed:

                backup_file = self._decompress_file(backup_file)

            

            # Detectar formato

            backup_format = self._detect_format(backup_file)

            

            # Limpiar base de datos

            self.stdout.write('Limpiando base de datos...')

            self._flush_database()

            

            # Restaurar datos

            self.stdout.write('Restaurando datos...')

            self._restore_data(backup_file, backup_format)

            

            # Limpiar archivo temporal si se descomprimió

            if is_compressed:

                backup_file.unlink()

            

            # Registrar restauración

            self._register_restore(backup_file)

            

            self.stdout.write(

                self.style.SUCCESS(

                    f'\nRestauración completada exitosamente.\n'

                    f'Archivo: {backup_file}\n'

                    f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

                )

            )

            

        except Exception as e:

            raise CommandError(f'Error durante la restauración: {str(e)}')



    def _get_backup_dir(self):

        """Obtiene el directorio de backups."""

        backup_dir = getattr(settings, 'BACKUP_DIR', None)

        if backup_dir:

            return Path(backup_dir)

        return Path(settings.BASE_DIR) / 'backups'



    def _list_backups(self, backup_dir):

        """Lista todos los backups disponibles."""

        if not backup_dir.exists():

            self.stdout.write(self.style.WARNING('No hay backups disponibles'))

            return

        

        backups = sorted(

            backup_dir.glob('backup_*'),

            key=lambda x: x.stat().st_mtime,

            reverse=True

        )

        

        if not backups:

            self.stdout.write(self.style.WARNING('No hay backups disponibles'))

            return

        

        self.stdout.write(self.style.SUCCESS(f'\nBackups disponibles en: {backup_dir}\n'))

        self.stdout.write('-' * 80)

        self.stdout.write(f'{"Archivo":<45} {"Tamaño":<12} {"Fecha":<20}')

        self.stdout.write('-' * 80)

        

        for backup in backups:

            size = self._format_size(backup.stat().st_size)

            date = datetime.fromtimestamp(backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')

            self.stdout.write(f'{backup.name:<45} {size:<12} {date:<20}')

        

        self.stdout.write('-' * 80)

        self.stdout.write(f'Total: {len(backups)} backups\n')



    def _get_latest_backup(self, backup_dir):

        """Obtiene el backup más reciente."""

        if not backup_dir.exists():

            return None

        

        backups = sorted(

            backup_dir.glob('backup_*'),

            key=lambda x: x.stat().st_mtime,

            reverse=True

        )

        

        return backups[0] if backups else None



    def _resolve_backup_path(self, backup_file, backup_dir):

        """Resuelve la ruta del archivo de backup."""

        backup_path = Path(backup_file)

        

        # Si es ruta absoluta

        if backup_path.is_absolute():

            return backup_path

        

        # Buscar en directorio de backups

        if (backup_dir / backup_file).exists():

            return backup_dir / backup_file

        

        # Buscar en directorio actual

        return backup_path



    def _decompress_file(self, file_path):

        """Descomprime un archivo gzip."""

        self.stdout.write('Descomprimiendo archivo...')

        

        decompressed_path = Path(str(file_path).replace('.gz', ''))

        

        with gzip.open(file_path, 'rb') as f_in:

            with open(decompressed_path, 'wb') as f_out:

                shutil.copyfileobj(f_in, f_out)

        

        return decompressed_path



    def _detect_format(self, file_path):

        """Detecta el formato del archivo de backup."""

        suffix = file_path.suffix.lower()

        

        if suffix == '.json':

            return 'json'

        elif suffix == '.xml':

            return 'xml'

        elif suffix == '.yaml' or suffix == '.yml':

            return 'yaml'

        

        # Intentar detectar por contenido

        with open(file_path, 'r', encoding='utf-8') as f:

            first_char = f.read(1)

            if first_char == '[' or first_char == '{':

                return 'json'

            elif first_char == '<':

                return 'xml'

        

        return 'json'



    def _flush_database(self):

        """Limpia la base de datos manteniendo la estructura."""

        # Usar flush de Django

        call_command('flush', '--no-input', verbosity=0)



    def _restore_data(self, backup_file, backup_format):

        """Restaura los datos desde el archivo de backup."""

        call_command(

            'loaddata',

            str(backup_file),

            format=backup_format,

            verbosity=1

        )



    def _register_restore(self, backup_file):

        """Registra la restauración en la base de datos."""

        try:

            from app.models import BackupRegistro

            

            BackupRegistro.objects.create(

                nombre=f'restore_{backup_file.name}',

                ruta=str(backup_file),

                tamaño=0,

                tipo='restauracion',

                estado='completado',

                notas=f'Restauración desde {backup_file.name} el {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

            )

        except Exception:

            pass



    def _format_size(self, size):

        """Formatea el tamaño en bytes."""

        for unit in ['B', 'KB', 'MB', 'GB']:

            if size < 1024:

                return f'{size:.2f} {unit}'

            size /= 1024

        return f'{size:.2f} TB'

