"""

Validadores personalizados para el sistema de seguros.

"""

import os

from django.core.exceptions import ValidationError

from django.utils.deconstruct import deconstructible

from django.template.defaultfilters import filesizeformat


# Importar magic opcionalmente (solo si está disponible)

try:

    import magic

    MAGIC_AVAILABLE = True

except ImportError:

    MAGIC_AVAILABLE = False


# Tipos MIME permitidos para documentos

ALLOWED_MIME_TYPES = {

    # PDFs

    'application/pdf': ['.pdf'],

    # Imágenes

    'image/jpeg': ['.jpg', '.jpeg'],

    'image/png': ['.png'],

    'image/gif': ['.gif'],

    'image/webp': ['.webp'],

    'image/tiff': ['.tiff', '.tif'],

    # Microsoft Office

    'application/msword': ['.doc'],

    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],

    'application/vnd.ms-excel': ['.xls'],

    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],

    'application/vnd.ms-powerpoint': ['.ppt'],

    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],

    # Texto

    'text/plain': ['.txt'],

    'text/csv': ['.csv'],

    # Comprimidos (para documentación múltiple)

    'application/zip': ['.zip'],

    'application/x-rar-compressed': ['.rar'],

}


# Extensiones permitidas

ALLOWED_EXTENSIONS = [ext for exts in ALLOWED_MIME_TYPES.values() for ext in exts]


# Extensiones peligrosas que nunca se deben permitir

DANGEROUS_EXTENSIONS = [

    '.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.pif',

    '.js', '.jse', '.vbs', '.vbe', '.wsf', '.wsh',

    '.ps1', '.psm1', '.psd1',

    '.sh', '.bash', '.zsh',

    '.php', '.php3', '.php4', '.php5', '.phtml',

    '.py', '.pyc', '.pyo',

    '.pl', '.pm', '.cgi',

    '.asp', '.aspx',

    '.jar', '.class',

    '.dll', '.so', '.dylib',

]


# Tamaño máximo por defecto: 10MB

DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB en bytes


@deconstructible
class FileValidator:

    """

    Validador de archivos que verifica:

    - Extensión del archivo

    - Tipo MIME real (no solo la extensión)

    - Tamaño máximo

    - Extensiones peligrosas

    """

    def __init__(self,

                 max_size=DEFAULT_MAX_FILE_SIZE,

                 allowed_extensions=None,

                 allowed_mime_types=None):

        self.max_size = max_size

        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS

        self.allowed_mime_types = allowed_mime_types or list(ALLOWED_MIME_TYPES.keys())

    def __call__(self, file):

        # Validar tamaño

        self._validate_size(file)

        # Validar extensión

        self._validate_extension(file)

        # Validar tipo MIME real

        self._validate_mime_type(file)

    def _validate_size(self, file):

        """Valida que el archivo no exceda el tamaño máximo."""

        if file.size > self.max_size:

            raise ValidationError(

                f'El archivo es demasiado grande. '

                f'Tamaño máximo permitido: {filesizeformat(self.max_size)}. '

                f'Tamaño del archivo: {filesizeformat(file.size)}.'

            )

    def _validate_extension(self, file):

        """Valida la extensión del archivo."""

        ext = os.path.splitext(file.name)[1].lower()

        # Verificar que no sea una extensión peligrosa

        if ext in DANGEROUS_EXTENSIONS:

            raise ValidationError(

                f'El tipo de archivo "{ext}" no está permitido por razones de seguridad.'

            )

        # Verificar que esté en la lista de permitidos

        if ext not in self.allowed_extensions:

            raise ValidationError(

                f'Extensión de archivo no permitida: "{ext}". '

                f'Extensiones permitidas: {", ".join(self.allowed_extensions)}'

            )

    def _validate_mime_type(self, file):

        """

        Valida el tipo MIME real del archivo usando python-magic.

        Esto previene que alguien renombre un .exe a .pdf

        """

        # Si magic no está disponible, solo validar por extensión

        if not MAGIC_AVAILABLE:

            import logging

            logger = logging.getLogger(__name__)

            logger.debug('python-magic no disponible, validación de MIME omitida')

            return

        try:

            # Leer los primeros bytes para detectar el tipo real

            file.seek(0)

            file_header = file.read(2048)

            file.seek(0)

            # Detectar el tipo MIME real

            mime = magic.from_buffer(file_header, mime=True)

            if mime not in self.allowed_mime_types:

                raise ValidationError(

                    f'El contenido del archivo no corresponde a un tipo permitido. '

                    f'Tipo detectado: {mime}. '

                    f'Asegúrese de subir un archivo válido (PDF, imagen, documento Office, etc.).'

                )

            # Verificar que la extensión coincida con el tipo MIME

            ext = os.path.splitext(file.name)[1].lower()

            expected_extensions = ALLOWED_MIME_TYPES.get(mime, [])

            if expected_extensions and ext not in expected_extensions:

                raise ValidationError(

                    f'La extensión del archivo ({ext}) no coincide con su contenido real ({mime}). '

                    f'Esto puede indicar que el archivo ha sido renombrado. '

                    f'Por favor, suba un archivo con la extensión correcta.'

                )

        except Exception as e:

            # Log del error pero no bloquear la subida por errores de detección

            import logging

            logger = logging.getLogger(__name__)

            logger.warning(f'Error validando tipo MIME: {e}')

    def __eq__(self, other):

        return (

            isinstance(other, FileValidator) and

            self.max_size == other.max_size and

            self.allowed_extensions == other.allowed_extensions

        )

@deconstructible
class ImageValidator(FileValidator):

    """

    Validador específico para imágenes.

    """

    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff', '.tif']

    ALLOWED_IMAGE_MIME_TYPES = [

        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/tiff'

    ]

    def __init__(self, max_size=5 * 1024 * 1024):  # 5MB por defecto para imágenes

        super().__init__(

            max_size=max_size,

            allowed_extensions=self.ALLOWED_IMAGE_EXTENSIONS,

            allowed_mime_types=self.ALLOWED_IMAGE_MIME_TYPES

        )

@deconstructible
class PDFValidator(FileValidator):

    """

    Validador específico para archivos PDF.

    """

    def __init__(self, max_size=20 * 1024 * 1024):  # 20MB por defecto para PDFs

        super().__init__(

            max_size=max_size,

            allowed_extensions=['.pdf'],

            allowed_mime_types=['application/pdf']

        )

# Instancias pre-configuradas para uso común

validate_document = FileValidator()

validate_image = ImageValidator()

validate_pdf = PDFValidator()


def validate_file_extension(value):

    """

    Validador simple que solo verifica la extensión.

    Útil para campos donde no se necesita validación completa.

    """

    ext = os.path.splitext(value.name)[1].lower()


    if ext in DANGEROUS_EXTENSIONS:

        raise ValidationError(

            f'El tipo de archivo "{ext}" no está permitido.'

        )


    if ext not in ALLOWED_EXTENSIONS:

        raise ValidationError(

            f'Extensión no permitida: "{ext}". '

            f'Use: PDF, imágenes (JPG, PNG), o documentos Office.'

        )
