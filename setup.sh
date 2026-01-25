#!/bin/bash

# Script de configuración inicial para el Sistema de Gestión de Seguros - UTPL
# Este script automatiza la instalación y configuración inicial

set -e  # Salir si hay algún error

echo "========================================="
echo "Sistema de Gestión de Seguros - UTPL"
echo "Script de Configuración Inicial"
echo "========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Verificar Python
echo "Verificando requisitos..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 no está instalado. Por favor, instálalo primero."
    exit 1
fi
print_success "Python 3 encontrado"

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 no está instalado. Por favor, instálalo primero."
    exit 1
fi
print_success "pip3 encontrado"

# Crear entorno virtual
echo ""
print_info "Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Entorno virtual creado"
else
    print_info "El entorno virtual ya existe"
fi

# Activar entorno virtual
print_info "Activando entorno virtual..."
source venv/bin/activate
print_success "Entorno virtual activado"

# Actualizar pip
print_info "Actualizando pip..."
pip install --upgrade pip > /dev/null
print_success "pip actualizado"

# Instalar dependencias
echo ""
print_info "Instalando dependencias... (esto puede tomar varios minutos)"
pip install -r requirements.txt > /dev/null
print_success "Dependencias instaladas"

# Crear archivo .env si no existe
echo ""
if [ ! -f ".env" ]; then
    print_info "Creando archivo .env desde .env.example..."
    cp .env.example .env
    
    # Generar SECRET_KEY
    print_info "Generando SECRET_KEY..."
    SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    
    # Reemplazar SECRET_KEY en .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
    fi
    
    print_success "Archivo .env creado con SECRET_KEY generada"
    print_info "Por favor, revisa y ajusta las configuraciones en .env según sea necesario"
else
    print_info "El archivo .env ya existe"
fi

# Crear directorios necesarios
echo ""
print_info "Creando directorios necesarios..."
mkdir -p logs
mkdir -p media/documentos
mkdir -p media/reportes/polizas
mkdir -p media/reportes/siniestros
mkdir -p static
print_success "Directorios creados"

# Crear migraciones
echo ""
print_info "Creando migraciones de base de datos..."
python manage.py makemigrations
print_success "Migraciones creadas"

# Aplicar migraciones
print_info "Aplicando migraciones..."
python manage.py migrate
print_success "Migraciones aplicadas"

# Crear datos iniciales
echo ""
read -p "¿Deseas crear tipos de póliza y siniestro iniciales? (s/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    print_info "Creando datos iniciales..."
    python manage.py shell << EOF
from app.models import TipoPoliza, TipoSiniestro

# Crear tipos de póliza
tipos_poliza = [
    ('Todo Riesgo', 'Cobertura completa contra todo tipo de riesgos'),
    ('Incendio y Líneas Aliadas', 'Protección contra incendios y eventos relacionados'),
    ('Robo y Asalto', 'Protección contra robo y asalto'),
    ('Responsabilidad Civil', 'Cobertura de responsabilidad civil'),
    ('Equipos Electrónicos', 'Cobertura para equipos electrónicos'),
    ('Fidelidad', 'Cobertura de fidelidad de empleados'),
]

for nombre, descripcion in tipos_poliza:
    TipoPoliza.objects.get_or_create(
        nombre=nombre,
        defaults={'descripcion': descripcion}
    )

# Crear tipos de siniestro
tipos_siniestro = [
    ('daño', 'Daño a la propiedad'),
    ('robo', 'Robo de bienes'),
    ('hurto', 'Hurto de bienes'),
    ('incendio', 'Daño por incendio'),
    ('inundacion', 'Daño por inundación'),
    ('terremoto', 'Daño por terremoto'),
    ('vandalismo', 'Daño por vandalismo'),
]

for nombre, descripcion in tipos_siniestro:
    TipoSiniestro.objects.get_or_create(
        nombre=nombre,
        defaults={'descripcion': descripcion}
    )

print("✓ Datos iniciales creados")
EOF
    print_success "Datos iniciales creados"
fi

# Crear superusuario
echo ""
read -p "¿Deseas crear un superusuario ahora? (s/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    print_info "Creando superusuario..."
    python manage.py createsuperuser
    print_success "Superusuario creado"
else
    print_info "Puedes crear un superusuario más tarde con: python manage.py createsuperuser"
fi

# Recolectar archivos estáticos
echo ""
print_info "Recolectando archivos estáticos..."
python manage.py collectstatic --no-input > /dev/null
print_success "Archivos estáticos recolectados"

# Verificar Redis (opcional)
echo ""
print_info "Verificando Redis (necesario para Celery)..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        print_success "Redis está instalado y funcionando"
    else
        print_error "Redis está instalado pero no está corriendo"
        print_info "Inicia Redis con: redis-server (Linux) o brew services start redis (Mac)"
    fi
else
    print_error "Redis no está instalado"
    print_info "Redis es necesario para el sistema de alertas con Celery"
    print_info "Instala Redis:"
    print_info "  - Mac: brew install redis"
    print_info "  - Ubuntu: sudo apt-get install redis-server"
fi

# Resumen final
echo ""
echo "========================================="
echo "✓ Configuración completada exitosamente"
echo "========================================="
echo ""
print_info "Próximos pasos:"
echo "  1. Revisa y ajusta el archivo .env si es necesario"
echo "  2. Inicia el servidor de desarrollo: python manage.py runserver"
echo "  3. Accede al admin en: http://localhost:8000/admin/"
echo ""
print_info "Para usar el sistema de alertas automáticas:"
echo "  1. Asegúrate de que Redis esté corriendo"
echo "  2. En otra terminal: celery -A seguros worker -l info"
echo "  3. En otra terminal: celery -A seguros beat -l info"
echo ""
print_info "Para generar reportes:"
echo "  - Pólizas: python manage.py generar_reporte_polizas"
echo "  - Siniestros: python manage.py generar_reporte_siniestros"
echo ""
print_success "¡Sistema listo para usar!"
echo ""
