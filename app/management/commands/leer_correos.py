"""
Comando Django para leer correos de siniestros desde la bandeja IMAP.

Uso:
    python manage.py leer_correos
    python manage.py leer_correos --limit 5
    python manage.py leer_correos --unseen-only
    python manage.py leer_correos --mark-read
    python manage.py leer_correos --dry-run
    python manage.py leer_correos --no-auto-create

Opciones:
    --limit N       : Procesar máximo N correos (default: 10)
    --unseen-only   : Solo procesar correos no leídos
    --mark-read     : Marcar correos procesados como leídos
    --dry-run       : Solo mostrar qué haría, sin guardar en BD
    --folder FOLDER : Carpeta a procesar (default: INBOX)
    --no-auto-create: No intentar crear siniestros automáticamente
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from app.services.email_reader import (
    EmailReaderService,
    IMAPConnectionError,
    IMAPAuthenticationError,
    ReporteSiniestro,
    guardar_reporte_en_bd,
)


class Command(BaseCommand):
    help = 'Lee correos de siniestros desde la bandeja de entrada IMAP y los guarda en la BD'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Máximo de correos a procesar (default: 10)',
        )
        parser.add_argument(
            '--unseen-only',
            action='store_true',
            help='Solo procesar correos no leídos',
        )
        parser.add_argument(
            '--mark-read',
            action='store_true',
            help='Marcar correos procesados como leídos',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué haría, sin guardar en BD',
        )
        parser.add_argument(
            '--folder',
            type=str,
            default='INBOX',
            help='Carpeta a procesar (default: INBOX)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada de cada correo',
        )
        parser.add_argument(
            '--no-auto-create',
            action='store_true',
            help='No intentar crear siniestros automáticamente',
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        unseen_only = options['unseen_only']
        mark_read = options['mark_read'] and not options['dry_run']
        dry_run = options['dry_run']
        folder = options['folder']
        verbose = options['verbose']
        auto_create = not options['no_auto_create']
        
        # Verificar configuración
        if not self._check_configuration():
            return
        
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write(self.style.HTTP_INFO('  LECTOR DE CORREOS DE SINIESTROS'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠ MODO DRY-RUN: No se guardarán datos en la BD'))
            self.stdout.write('')
        
        # Mostrar configuración
        self.stdout.write(f'📧 Email: {settings.IMAP_EMAIL}')
        self.stdout.write(f'📁 Carpeta: {folder}')
        self.stdout.write(f'🔢 Límite: {limit} correos')
        self.stdout.write(f'👁 Solo no leídos: {"Sí" if unseen_only else "No"}')
        self.stdout.write(f'✓ Marcar como leídos: {"Sí" if mark_read else "No"}')
        self.stdout.write(f'🤖 Crear siniestros auto: {"Sí" if auto_create else "No"}')
        self.stdout.write('')
        
        try:
            self.stdout.write(f'Conectando a {settings.IMAP_HOST}:{settings.IMAP_PORT}...')
            
            with EmailReaderService() as service:
                self.stdout.write(self.style.SUCCESS('✓ Conexión exitosa'))
                self.stdout.write('')
                
                self.stdout.write(f'Buscando correos con [{settings.SINIESTRO_EMAIL_SUBJECT_TAG}]...')
                
                reportes = service.process_siniestro_emails(
                    folder=folder,
                    limit=limit,
                    unseen_only=unseen_only,
                    mark_as_read=mark_read,
                )
                
                self.stdout.write('')
                self.stdout.write(self.style.HTTP_INFO('-' * 60))
                self.stdout.write('')
                
                if not reportes:
                    self.stdout.write(self.style.WARNING(
                        'No se encontraron correos de siniestros que procesar.'
                    ))
                    return
                
                # Estadísticas
                guardados = 0
                siniestros_creados = 0
                pendientes = 0
                ya_existentes = 0
                errores = 0
                
                # Mostrar y procesar resultados
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Se encontraron {len(reportes)} correo(s) de siniestros:'
                ))
                self.stdout.write('')
                
                for i, reporte in enumerate(reportes, 1):
                    self._print_reporte(i, reporte, verbose)
                    
                    # Guardar en BD si no es dry-run
                    if not dry_run:
                        try:
                            siniestro_email, siniestro, mensaje = guardar_reporte_en_bd(
                                reporte,
                                intentar_crear_siniestro=auto_create
                            )
                            
                            guardados += 1
                            
                            if siniestro:
                                siniestros_creados += 1
                                self.stdout.write(self.style.SUCCESS(
                                    f'    💾 GUARDADO: Siniestro {siniestro.numero_siniestro} creado'
                                ))
                            elif 'ya procesado' in mensaje.lower():
                                ya_existentes += 1
                                self.stdout.write(self.style.WARNING(
                                    f'    ⚠️  Ya existía en el sistema'
                                ))
                            else:
                                pendientes += 1
                                self.stdout.write(self.style.WARNING(
                                    f'    📋 PENDIENTE: {mensaje[:60]}...'
                                ))
                            
                            self.stdout.write('')
                            
                        except Exception as e:
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f'    ❌ ERROR al guardar: {str(e)[:60]}'
                            ))
                            self.stdout.write('')
                
                # Resumen final
                self.stdout.write('')
                self.stdout.write(self.style.HTTP_INFO('=' * 60))
                self.stdout.write(self.style.HTTP_INFO('  RESUMEN'))
                self.stdout.write(self.style.HTTP_INFO('=' * 60))
                self.stdout.write('')
                self.stdout.write(f'📬 Correos procesados: {len(reportes)}')
                
                if not dry_run:
                    self.stdout.write(f'💾 Guardados en BD: {guardados}')
                    self.stdout.write(self.style.SUCCESS(f'✅ Siniestros creados: {siniestros_creados}'))
                    self.stdout.write(self.style.WARNING(f'📋 Pendientes revisión: {pendientes}'))
                    if ya_existentes:
                        self.stdout.write(f'⚠️  Ya existentes: {ya_existentes}')
                    if errores:
                        self.stdout.write(self.style.ERROR(f'❌ Errores: {errores}'))
                else:
                    self.stdout.write('')
                    self.stdout.write(self.style.WARNING(
                        '⚠ MODO DRY-RUN: Los datos NO fueron guardados.'
                    ))
                    self.stdout.write(self.style.WARNING(
                        '  Ejecute sin --dry-run para guardar en la BD.'
                    ))
                
                self.stdout.write('')
                
        except IMAPConnectionError as e:
            raise CommandError(f'Error de conexión: {e}')
        
        except IMAPAuthenticationError as e:
            raise CommandError(
                f'Error de autenticación: {e}\n\n'
                'Para Gmail, necesitas:\n'
                '1. Habilitar "Verificación en 2 pasos"\n'
                '2. Generar una "Contraseña de aplicación"\n'
                '3. Configurar IMAP_PASSWORD con esa contraseña en .env'
            )
        
        except Exception as e:
            raise CommandError(f'Error inesperado: {e}')
    
    def _check_configuration(self) -> bool:
        """Verifica que la configuración IMAP esté presente."""
        errors = []
        
        if not getattr(settings, 'IMAP_EMAIL', ''):
            errors.append('IMAP_EMAIL no está configurado')
        
        if not getattr(settings, 'IMAP_PASSWORD', ''):
            errors.append('IMAP_PASSWORD no está configurado')
        
        if errors:
            self.stdout.write(self.style.ERROR('Error de configuración:'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
            self.stdout.write('')
            self.stdout.write('Configura las variables en tu archivo .env:')
            self.stdout.write('  IMAP_EMAIL=tu_correo@gmail.com')
            self.stdout.write('  IMAP_PASSWORD=tu_app_password')
            self.stdout.write('')
            self.stdout.write('Para Gmail, genera una App Password en:')
            self.stdout.write('  https://myaccount.google.com/apppasswords')
            return False
        
        return True
    
    def _print_reporte(self, index: int, reporte: ReporteSiniestro, verbose: bool):
        """Imprime los detalles de un reporte."""
        self.stdout.write(f'┌─ [{index}] {reporte.subject[:50]}{"..." if len(reporte.subject) > 50 else ""}')
        self.stdout.write(f'│')
        self.stdout.write(f'│  📋 Responsable: {reporte.responsable}')
        self.stdout.write(f'│  📅 Fecha reporte: {reporte.fecha_reporte}')
        self.stdout.write(f'│  ⚠️  Problema: {reporte.problema[:60]}{"..." if len(reporte.problema) > 60 else ""}')
        self.stdout.write(f'│  🔍 Causa: {reporte.causa}')
        self.stdout.write(f'│')
        self.stdout.write(f'│  📦 EQUIPO:')
        self.stdout.write(f'│     Tipo: {reporte.equipo.periferico}')
        self.stdout.write(f'│     Marca: {reporte.equipo.marca}')
        self.stdout.write(f'│     Modelo: {reporte.equipo.modelo}')
        self.stdout.write(f'│     Serie: {self.style.WARNING(reporte.equipo.serie)}')
        if reporte.equipo.activo:
            self.stdout.write(f'│     Activo: {reporte.equipo.activo}')
        self.stdout.write(f'│')
        
        if reporte.attachments:
            self.stdout.write(f'│  📎 Adjuntos: {len(reporte.attachments)}')
            for att in reporte.attachments:
                self.stdout.write(f'│     - {att.get("filename", "sin nombre")}')
        
        if verbose:
            self.stdout.write(f'│')
            self.stdout.write(f'│  🔑 Email ID: {reporte.email_id}')
            self.stdout.write(f'│  📨 De: {reporte.from_address}')
            if reporte.date:
                self.stdout.write(f'│  🕐 Fecha email: {reporte.date}')
        
        self.stdout.write(f'└{"─" * 58}')
