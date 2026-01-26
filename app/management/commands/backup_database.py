"""

Comando para crear respaldos de la base de datos.

Soporta SQLite, PostgreSQL y MySQL.

Uso:

    python manage.py backup_database

    python manage.py backup_database --output /ruta/backup.sql

    python manage.py backup_database --compress

    python manage.py backup_database --include-media

"""

import os

import gzip

import shutil

from datetime import datetime

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from django.conf import settings

from django.core.management import call_command

class Command(BaseCommand):

    help = 'Crea un respaldo completo de la base de datos y opcionalmente archivos media'

    def add_arguments(self, parser):

        parser.add_argument(

            '--output', '-o',

            type=str,

            help='Ruta de salida para el archivo de backup'

        )

        parser.add_argument(

            '--compress', '-c',

            action='store_true',

            help='Comprimir el backup con gzip'

        )

        parser.add_argument(

            '--include-media', '-m',

            action='store_true',

            help='Incluir archivos media en el backup'

        )

        parser.add_argument(

            '--format',

            type=str,

            choices=['json', 'xml', 'yaml'],

            default='json',

            help='Formato del backup (default: json)'

        )

        parser.add_argument(

            '--quiet', '-q',

            action='store_true',

            help='No mostrar mensajes de progreso'

        )

    def handle(self, *args, **options):

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        backup_dir = self._get_backup_dir()

        # Crear directorio de backups si no existe

        backup_dir.mkdir(parents=True, exist_ok=True)

        # Determinar nombre del archivo

        if options['output']:

            backup_path = Path(options['output'])

        else:

            ext = options['format']

            backup_path = backup_dir / f'backup_{timestamp}.{ext}'

        try:

            # Crear backup de la base de datos

            self._backup_database(backup_path, options)

            # Comprimir si se solicita

            if options['compress']:

                backup_path = self._compress_file(backup_path)

            # Incluir media si se solicita

            if options['include_media']:

                media_backup = self._backup_media(backup_dir, timestamp)

                if media_backup and not options['quiet']:

                    self.stdout.write(

                        self.style.SUCCESS(f'Media respaldado en: {media_backup}')

                    )

            # Registrar backup en la base de datos

            self._register_backup(backup_path, options)

            if not options['quiet']:

                size = backup_path.stat().st_size

                size_str = self._format_size(size)

                self.stdout.write(

                    self.style.SUCCESS(

                        f'\nBackup creado exitosamente:\n'

                        f'  Archivo: {backup_path}\n'

                        f'  Tamaño: {size_str}\n'

                        f'  Formato: {options["format"]}\n'

                        f'  Comprimido: {"Sí" if options["compress"] else "No"}'

                    )

                )

            return str(backup_path)

        except Exception as e:

            raise CommandError(f'Error al crear backup: {str(e)}')

    def _get_backup_dir(self):

        """Obtiene el directorio de backups desde configuración o usa default."""

        backup_dir = getattr(settings, 'BACKUP_DIR', None)

        if backup_dir:

            return Path(backup_dir)

        return Path(settings.BASE_DIR) / 'backups'

    def _backup_database(self, backup_path, options):

        """Crea el backup de la base de datos usando dumpdata."""

        if not options['quiet']:

            self.stdout.write('Creando backup de la base de datos...')

        # Usar dumpdata de Django para compatibilidad

        with open(backup_path, 'w', encoding='utf-8') as f:

            call_command(

                'dumpdata',

                '--natural-foreign',

                '--natural-primary',

                '--exclude=contenttypes',

                '--exclude=auth.permission',

                '--exclude=admin.logentry',

                '--exclude=sessions.session',

                '--indent=2',

                format=options['format'],

                stdout=f

            )

    def _compress_file(self, file_path):

        """Comprime un archivo con gzip."""

        compressed_path = Path(str(file_path) + '.gz')

        with open(file_path, 'rb') as f_in:

            with gzip.open(compressed_path, 'wb') as f_out:

                shutil.copyfileobj(f_in, f_out)

        # Eliminar archivo original

        file_path.unlink()

        return compressed_path

    def _backup_media(self, backup_dir, timestamp):

        """Crea un backup de los archivos media."""

        media_root = getattr(settings, 'MEDIA_ROOT', None)

        if not media_root:

            return None

        media_root = Path(media_root)

        if not media_root.exists():

            return None

        media_backup = backup_dir / f'media_{timestamp}'

        # Crear archivo tar.gz

        shutil.make_archive(

            str(media_backup),

            'gztar',

            media_root

        )

        return Path(str(media_backup) + '.tar.gz')

    def _register_backup(self, backup_path, options):

        """Registra el backup en la base de datos."""

        try:

            from app.models import BackupRegistro

            BackupRegistro.objects.create(

                nombre=backup_path.name,

                ruta=str(backup_path),

                tamaño=backup_path.stat().st_size,

                tipo='completo' if options['include_media'] else 'base_datos',

                comprimido=options['compress'],

                formato=options['format'],

                estado='completado',

                notas=f'Backup creado el {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

            )

        except Exception:

            # Si el modelo no existe aún, ignorar

            pass

    def _format_size(self, size):

        """Formatea el tamaño en bytes a formato legible."""

        for unit in ['B', 'KB', 'MB', 'GB']:

            if size < 1024:

                return f'{size:.2f} {unit}'

            size /= 1024

        return f'{size:.2f} TB'
