# Guía de Despliegue en Producción

Esta guía describe cómo desplegar el Sistema de Gestión de Seguros en un entorno de producción.

## 📋 Requisitos de Servidor

### Hardware Mínimo Recomendado
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Almacenamiento**: 50 GB SSD
- **Ancho de banda**: 100 Mbps

### Software Requerido
- **Sistema Operativo**: Ubuntu 22.04 LTS (o similar)
- **Python**: 3.10+
- **PostgreSQL**: 14+
- **Redis**: 6.2+
- **Nginx**: 1.18+
- **Supervisor**: 4.2+ (para gestión de procesos)

## 🔧 Instalación en Producción

### 1. Preparar el Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias del sistema
sudo apt install -y python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib nginx redis-server \
    supervisor git libpq-dev build-essential
```

### 2. Configurar PostgreSQL

```bash
# Acceder a PostgreSQL
sudo -u postgres psql

# Crear base de datos y usuario
CREATE DATABASE seguros_db;
CREATE USER seguros_user WITH PASSWORD 'password_seguro_aqui';
ALTER ROLE seguros_user SET client_encoding TO 'utf8';
ALTER ROLE seguros_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE seguros_user SET timezone TO 'America/Guayaquil';
GRANT ALL PRIVILEGES ON DATABASE seguros_db TO seguros_user;
\q
```

### 3. Clonar y Configurar Aplicación

```bash
# Crear usuario de sistema para la aplicación
sudo useradd -m -s /bin/bash seguros
sudo su - seguros

# Clonar repositorio
cd /home/seguros
git clone https://github.com/UTPL/seguros-arqsoft.git
cd seguros-arqsoft

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 4. Configurar Variables de Entorno

```bash
# Crear archivo .env
nano .env
```

Contenido del archivo `.env`:

```env
# Django Configuration
SECRET_KEY=generar-clave-secreta-compleja-aqui
DEBUG=False
ALLOWED_HOSTS=seguros.utpl.edu.ec,www.seguros.utpl.edu.ec,IP_DEL_SERVIDOR

# Database
DATABASE_URL=postgresql://seguros_user:password_seguro_aqui@localhost:5432/seguros_db

# Email Configuration (AWS SES Recomendado)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-usuario-smtp
EMAIL_HOST_PASSWORD=tu-password-smtp
DEFAULT_FROM_EMAIL=seguros@utpl.edu.ec
SERVER_EMAIL=seguros@utpl.edu.ec

# Site Configuration
SITE_URL=https://seguros.utpl.edu.ec

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0

# Logging
DJANGO_LOG_LEVEL=WARNING
```

### 5. Configurar Base de Datos PostgreSQL en settings.py

Agregar al `settings.py`:

```python
import dj_database_url

# Si existe DATABASE_URL, úsala; si no, usa SQLite
if os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

Instalar dj-database-url:
```bash
pip install dj-database-url
```

### 6. Preparar Django

```bash
# Migrar base de datos
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar archivos estáticos
python manage.py collectstatic --no-input

# Crear datos iniciales (opcional)
python manage.py shell < scripts/crear_datos_iniciales.py
```

### 7. Configurar Gunicorn

```bash
# Crear archivo de configuración
mkdir -p /home/seguros/seguros-arqsoft/config
nano /home/seguros/seguros-arqsoft/config/gunicorn_config.py
```

Contenido:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2

# Logging
accesslog = "/home/seguros/seguros-arqsoft/logs/gunicorn_access.log"
errorlog = "/home/seguros/seguros-arqsoft/logs/gunicorn_error.log"
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

### 8. Configurar Supervisor

```bash
# Salir del usuario seguros
exit

# Crear archivos de configuración de Supervisor
sudo nano /etc/supervisor/conf.d/seguros_gunicorn.conf
```

Contenido de `seguros_gunicorn.conf`:

```ini
[program:seguros_gunicorn]
command=/home/seguros/seguros-arqsoft/venv/bin/gunicorn seguros.wsgi:application -c /home/seguros/seguros-arqsoft/config/gunicorn_config.py
directory=/home/seguros/seguros-arqsoft
user=seguros
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/seguros/seguros-arqsoft/logs/gunicorn_supervisor.log
```

```bash
sudo nano /etc/supervisor/conf.d/seguros_celery_worker.conf
```

Contenido de `seguros_celery_worker.conf`:

```ini
[program:seguros_celery_worker]
command=/home/seguros/seguros-arqsoft/venv/bin/celery -A seguros worker -l info
directory=/home/seguros/seguros-arqsoft
user=seguros
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/seguros/seguros-arqsoft/logs/celery_worker.log
```

```bash
sudo nano /etc/supervisor/conf.d/seguros_celery_beat.conf
```

Contenido de `seguros_celery_beat.conf`:

```ini
[program:seguros_celery_beat]
command=/home/seguros/seguros-arqsoft/venv/bin/celery -A seguros beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
directory=/home/seguros/seguros-arqsoft
user=seguros
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/seguros/seguros-arqsoft/logs/celery_beat.log
```

```bash
# Recargar Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### 9. Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/seguros
```

Contenido:

```nginx
upstream seguros_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name seguros.utpl.edu.ec www.seguros.utpl.edu.ec;

    client_max_body_size 100M;

    access_log /var/log/nginx/seguros_access.log;
    error_log /var/log/nginx/seguros_error.log;

    location /static/ {
        alias /home/seguros/seguros-arqsoft/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /home/seguros/seguros-arqsoft/media/;
        expires 7d;
    }

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_pass http://seguros_app;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/seguros /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 10. Configurar SSL con Let's Encrypt

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado SSL
sudo certbot --nginx -d seguros.utpl.edu.ec -d www.seguros.utpl.edu.ec

# Renovación automática (ya configurada)
sudo certbot renew --dry-run
```

### 11. Configurar Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 🔒 Seguridad Adicional

### 1. Configurar Fail2Ban

```bash
sudo apt install fail2ban -y

# Crear configuración personalizada
sudo nano /etc/fail2ban/jail.local
```

Contenido:

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-noscript]
enabled = true

[nginx-badbots]
enabled = true
```

```bash
sudo systemctl restart fail2ban
```

### 2. Configurar Backups Automáticos

```bash
# Crear script de backup
sudo nano /home/seguros/backup.sh
```

Contenido:

```bash
#!/bin/bash
BACKUP_DIR="/home/seguros/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Crear directorio de backups
mkdir -p $BACKUP_DIR

# Backup de base de datos
PGPASSWORD="password_seguro_aqui" pg_dump -U seguros_user -h localhost seguros_db > $BACKUP_DIR/db_backup_$DATE.sql

# Backup de archivos media
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz /home/seguros/seguros-arqsoft/media/

# Eliminar backups antiguos (más de 30 días)
find $BACKUP_DIR -type f -mtime +30 -delete

# Comprimir
gzip $BACKUP_DIR/db_backup_$DATE.sql
```

```bash
# Hacer ejecutable
chmod +x /home/seguros/backup.sh

# Agregar a crontab (diario a las 2 AM)
crontab -e
```

Agregar:
```
0 2 * * * /home/seguros/backup.sh >> /home/seguros/backup.log 2>&1
```

### 3. Monitoreo de Logs

```bash
# Ver logs en tiempo real
sudo tail -f /home/seguros/seguros-arqsoft/logs/django.log
sudo tail -f /var/log/nginx/seguros_error.log
sudo supervisorctl tail -f seguros_gunicorn
```

## 🔄 Actualización de la Aplicación

```bash
# Conectarse como usuario seguros
sudo su - seguros
cd /home/seguros/seguros-arqsoft

# Activar entorno virtual
source venv/bin/activate

# Obtener últimos cambios
git pull origin main

# Instalar nuevas dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Recolectar archivos estáticos
python manage.py collectstatic --no-input

# Salir
exit

# Reiniciar servicios
sudo supervisorctl restart all
sudo systemctl restart nginx
```

## 📊 Monitoreo y Mantenimiento

### Verificar Estado de Servicios

```bash
# Supervisor
sudo supervisorctl status

# Nginx
sudo systemctl status nginx

# Redis
sudo systemctl status redis

# PostgreSQL
sudo systemctl status postgresql
```

### Limpieza de Logs

```bash
# Rotar logs manualmente
sudo logrotate -f /etc/logrotate.d/nginx

# Limpiar logs antiguos de Django (más de 90 días)
find /home/seguros/seguros-arqsoft/logs -name "*.log" -mtime +90 -delete
```

### Monitoreo de Recursos

```bash
# Uso de CPU y RAM
htop

# Espacio en disco
df -h

# Procesos de Python
ps aux | grep python

# Conexiones a base de datos
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

## 🚨 Troubleshooting

### Problema: Gunicorn no inicia

```bash
# Ver logs
sudo supervisorctl tail seguros_gunicorn stderr

# Verificar sintaxis de Python
cd /home/seguros/seguros-arqsoft
source venv/bin/activate
python manage.py check
```

### Problema: Celery no ejecuta tareas

```bash
# Ver logs
sudo supervisorctl tail seguros_celery_worker stderr

# Verificar conexión a Redis
redis-cli ping

# Reiniciar Redis
sudo systemctl restart redis
```

### Problema: Error 502 Bad Gateway

```bash
# Verificar que Gunicorn está corriendo
sudo supervisorctl status seguros_gunicorn

# Verificar logs de Nginx
sudo tail -f /var/log/nginx/seguros_error.log

# Reiniciar Gunicorn
sudo supervisorctl restart seguros_gunicorn
```

## 📈 Optimización de Performance

### 1. Configurar Cache con Redis

Agregar a `settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### 2. Configurar PostgreSQL para Performance

```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```

Ajustar:
```
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
```

```bash
sudo systemctl restart postgresql
```

### 3. Configurar Nginx para Performance

```nginx
# Agregar al bloque server en /etc/nginx/sites-available/seguros

# Gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;

# Cache de archivos estáticos
location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## ✅ Checklist de Despliegue

- [ ] Servidor preparado con software requerido
- [ ] Base de datos PostgreSQL configurada
- [ ] Variables de entorno configuradas
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] Archivos estáticos recolectados
- [ ] Gunicorn funcionando
- [ ] Celery worker funcionando
- [ ] Celery beat funcionando
- [ ] Nginx configurado
- [ ] SSL configurado con Let's Encrypt
- [ ] Firewall configurado
- [ ] Backups automáticos configurados
- [ ] Fail2Ban configurado
- [ ] Monitoreo configurado
- [ ] Pruebas de funcionalidad realizadas

---

**Universidad Técnica Particular de Loja**  
Guía de Despliegue - Sistema de Gestión de Seguros
