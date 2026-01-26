# Dockerfile para Sistema de Gestión de Seguros - UTPL
FROM python:3.12-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn psycopg2-binary

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chmod -R 755 /app/staticfiles /app/media /app/logs

# Recolectar archivos estáticos
RUN python manage.py collectstatic --noinput || true

# Exponer puerto
EXPOSE 8000

# Script de inicio
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["web"]
