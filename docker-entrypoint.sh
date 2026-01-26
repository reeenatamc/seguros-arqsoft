#!/bin/bash
set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  Sistema de Seguros UTPL${NC}"
echo -e "${GREEN}  Starting...${NC}"
echo -e "${GREEN}==================================${NC}"

# Esperar a que PostgreSQL esté listo
if [ "$DATABASE_URL" ]; then
    echo -e "${YELLOW}Esperando a PostgreSQL...${NC}"
    until pg_isready -h ${POSTGRES_HOST:-postgres} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-postgres}; do
        echo -e "${YELLOW}PostgreSQL no está listo - esperando...${NC}"
        sleep 2
    done
    echo -e "${GREEN}✓ PostgreSQL está listo${NC}"
fi

# Esperar a que Redis esté listo (para Celery)
if [ "$CELERY_BROKER_URL" ]; then
    echo -e "${YELLOW}Esperando a Redis...${NC}"
    until redis-cli -h ${REDIS_HOST:-redis} ping > /dev/null 2>&1; do
        echo -e "${YELLOW}Redis no está listo - esperando...${NC}"
        sleep 2
    done
    echo -e "${GREEN}✓ Redis está listo${NC}"
fi

# Ejecutar migraciones
echo -e "${YELLOW}Ejecutando migraciones...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}✓ Migraciones completadas${NC}"

# Crear superusuario si no existe
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo -e "${YELLOW}Verificando superusuario...${NC}"
    python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('✓ Superusuario creado')
else:
    print('✓ Superusuario ya existe')
EOF
fi

# Recolectar archivos estáticos
echo -e "${YELLOW}Recolectando archivos estáticos...${NC}"
python manage.py collectstatic --noinput --clear
echo -e "${GREEN}✓ Archivos estáticos recolectados${NC}"

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  Iniciando servicio: $1${NC}"
echo -e "${GREEN}==================================${NC}"

# Ejecutar comando según argumento
case "$1" in
    web)
        echo -e "${GREEN}Iniciando servidor web con Gunicorn...${NC}"
        exec gunicorn seguros.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers ${GUNICORN_WORKERS:-4} \
            --threads ${GUNICORN_THREADS:-2} \
            --timeout ${GUNICORN_TIMEOUT:-120} \
            --access-logfile - \
            --error-logfile - \
            --log-level ${LOG_LEVEL:-info}
        ;;
    celery-worker)
        echo -e "${GREEN}Iniciando Celery Worker...${NC}"
        exec celery -A seguros worker \
            --loglevel=${CELERY_LOG_LEVEL:-info} \
            --concurrency=${CELERY_WORKERS:-4}
        ;;
    celery-beat)
        echo -e "${GREEN}Iniciando Celery Beat...${NC}"
        exec celery -A seguros beat \
            --loglevel=${CELERY_LOG_LEVEL:-info} \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    dev)
        echo -e "${GREEN}Iniciando servidor de desarrollo...${NC}"
        exec python manage.py runserver 0.0.0.0:8000
        ;;
    *)
        echo -e "${RED}Comando desconocido: $1${NC}"
        echo "Comandos disponibles: web, celery-worker, celery-beat, dev"
        exit 1
        ;;
esac
