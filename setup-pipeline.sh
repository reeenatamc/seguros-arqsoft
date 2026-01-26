#!/bin/bash

# ============================================
# Setup Script para Pipeline CI/CD
# Sistema de Gestión de Seguros
# ============================================

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ============================================
# 1. Verificar Python
# ============================================
print_header "1. Verificando Python"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 no está instalado"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
print_success "Python $PYTHON_VERSION instalado"

# ============================================
# 2. Crear entorno virtual
# ============================================
print_header "2. Configurando entorno virtual"

if [ -d "venv" ]; then
    print_warning "Entorno virtual ya existe, saltando..."
else
    python3 -m venv venv
    print_success "Entorno virtual creado"
fi

# Activar entorno virtual
source venv/bin/activate || source venv/Scripts/activate
print_success "Entorno virtual activado"

# ============================================
# 3. Actualizar pip
# ============================================
print_header "3. Actualizando pip"

python -m pip install --upgrade pip
print_success "pip actualizado"

# ============================================
# 4. Instalar dependencias
# ============================================
print_header "4. Instalando dependencias"

print_info "Instalando dependencias principales..."
pip install -r requirements.txt

print_info "Instalando dependencias de desarrollo..."
pip install -r requirements-dev.txt

print_success "Todas las dependencias instaladas"

# ============================================
# 5. Configurar pre-commit
# ============================================
print_header "5. Configurando pre-commit hooks"

pre-commit install
print_success "Pre-commit hooks instalados"

# ============================================
# 6. Verificar configuración
# ============================================
print_header "6. Verificando configuración"

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    print_warning "Archivo .env no encontrado"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Archivo .env creado desde .env.example"
        print_warning "Por favor, configura las variables en .env"
    else
        print_error "No se encontró .env.example"
    fi
fi

# ============================================
# 7. Ejecutar verificaciones
# ============================================
print_header "7. Ejecutando verificaciones de código"

print_info "Ejecutando flake8..."
if flake8 .; then
    print_success "flake8 pasó correctamente"
else
    print_warning "flake8 encontró algunos problemas"
fi

print_info "Ejecutando black (check)..."
if black --check .; then
    print_success "black check pasó correctamente"
else
    print_warning "Algunos archivos necesitan formateo. Ejecuta: black ."
fi

print_info "Ejecutando isort (check)..."
if isort --check-only .; then
    print_success "isort check pasó correctamente"
else
    print_warning "Algunos imports necesitan ordenamiento. Ejecuta: isort ."
fi

# ============================================
# 8. Migraciones de base de datos
# ============================================
print_header "8. Configurando base de datos"

print_info "Verificando migraciones..."
if python manage.py makemigrations --check --dry-run; then
    print_success "No hay migraciones pendientes"
else
    print_warning "Hay migraciones pendientes"
fi

print_info "Ejecutando migraciones..."
python manage.py migrate
print_success "Migraciones aplicadas"

# ============================================
# 9. Recolectar archivos estáticos
# ============================================
print_header "9. Recolectando archivos estáticos"

python manage.py collectstatic --no-input --clear
print_success "Archivos estáticos recolectados"

# ============================================
# 10. Ejecutar tests
# ============================================
print_header "10. Ejecutando tests"

print_info "Ejecutando pytest..."
if pytest --verbose --tb=short; then
    print_success "Todos los tests pasaron"
else
    print_error "Algunos tests fallaron"
fi

# ============================================
# 11. Análisis de seguridad
# ============================================
print_header "11. Análisis de seguridad"

print_info "Verificando vulnerabilidades con safety..."
if safety check --file requirements.txt; then
    print_success "No se encontraron vulnerabilidades"
else
    print_warning "Se encontraron algunas vulnerabilidades"
fi

print_info "Analizando código con bandit..."
if bandit -r app/ seguros/ -ll; then
    print_success "No se encontraron problemas de seguridad"
else
    print_warning "Se encontraron algunos problemas de seguridad"
fi

# ============================================
# Resumen final
# ============================================
print_header "✅ Setup completado"

echo -e "${GREEN}
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║  🎉 Pipeline CI/CD configurado exitosamente                ║
║                                                            ║
║  Próximos pasos:                                          ║
║  1. Configura las variables en .env                       ║
║  2. Ejecuta: python manage.py runserver                   ║
║  3. Ejecuta tests: pytest                                 ║
║  4. Haz commit de tus cambios                             ║
║                                                            ║
║  Comandos útiles:                                         ║
║  - Formatear código: black . && isort .                   ║
║  - Ejecutar tests: pytest --cov                           ║
║  - Verificar seguridad: safety check && bandit -r app/    ║
║  - Pre-commit check: pre-commit run --all-files           ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
${NC}"

print_info "Para activar el entorno virtual en el futuro:"
echo "  source venv/bin/activate  # Linux/macOS"
echo "  venv\\Scripts\\activate     # Windows"

print_success "¡Listo para desarrollar! 🚀"
