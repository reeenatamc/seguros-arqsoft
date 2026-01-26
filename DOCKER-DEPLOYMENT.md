# 🐳 Guía de Deployment con Docker

## 📋 Archivos Creados

- `Dockerfile` - Imagen de la aplicación
- `docker-compose.yml` - Configuración de producción
- `docker-compose.dev.yml` - Configuración de desarrollo
- `docker-entrypoint.sh` - Script de inicio
- `.dockerignore` - Archivos excluidos
- `.env.docker` - Ejemplo de configuración

---

## 🚀 OPCIÓN 1: Deployment de Producción

### **Paso 1: Configurar Variables de Entorno**

Crea un archivo `.env.production`:

```bash
cp .env.docker .env.production
```

Edita `.env.production` y configura:
- ✅ `SECRET_KEY` - Genera uno largo y aleatorio
- ✅ `POSTGRES_PASSWORD` - Contraseña segura
- ✅ `ALLOWED_HOSTS` - Tu dominio real
- ✅ `DJANGO_SUPERUSER_PASSWORD` - Contraseña del admin
- ✅ `EMAIL_*` - Configuración de email

### **Paso 2: Construir y Levantar**

```bash
# Construir las imágenes
docker compose build

# Levantar todos los servicios
docker compose --env-file .env.production up -d

# Ver logs
docker compose logs -f web
```

### **Paso 3: Verificar**

```bash
# Ver servicios corriendo
docker compose ps

# Acceder a la aplicación
http://localhost:8000

# Acceder al admin
http://localhost:8000/admin
```

**Servicios levantados:**
- ✅ PostgreSQL (puerto 5432)
- ✅ Redis (puerto 6379)
- ✅ Web Django (puerto 8000)
- ✅ Celery Worker (tareas asíncronas)
- ✅ Celery Beat (tareas programadas)

---

## 💻 OPCIÓN 2: Desarrollo Local con Docker

### **Ventajas:**
- ✅ Live reload (cambios en código se reflejan automáticamente)
- ✅ DEBUG=True
- ✅ Mismo entorno que producción

### **Comandos:**

```bash
# Levantar en modo desarrollo
docker compose -f docker-compose.dev.yml up -d

# Ver logs en tiempo real
docker compose -f docker-compose.dev.yml logs -f web

# Detener
docker compose -f docker-compose.dev.yml down
```

---

## 🔧 Comandos Útiles

### **Gestión de Servicios:**

```bash
# Iniciar
docker compose up -d

# Detener
docker compose down

# Reiniciar un servicio
docker compose restart web

# Ver logs
docker compose logs -f web
docker compose logs -f celery-worker

# Ver estado
docker compose ps
```

### **Ejecutar Comandos Django:**

```bash
# Crear migraciones
docker compose exec web python manage.py makemigrations

# Aplicar migraciones
docker compose exec web python manage.py migrate

# Crear superusuario manualmente
docker compose exec web python manage.py createsuperuser

# Shell de Django
docker compose exec web python manage.py shell

# Poblar datos de prueba
docker compose exec web python poblar_ejemplo.py
```

### **Gestión de Base de Datos:**

```bash
# Backup de base de datos
docker compose exec db pg_dump -U postgres seguros > backup.sql

# Restaurar base de datos
cat backup.sql | docker compose exec -T db psql -U postgres seguros

# Acceder a PostgreSQL
docker compose exec db psql -U postgres -d seguros
```

---

## 🛡️ Configuración de Seguridad

### **Para Producción, asegúrate de:**

1. **Variables de Entorno Seguras:**
   ```bash
   DEBUG=False
   SECRET_KEY=<genera-uno-largo-y-aleatorio>
   ALLOWED_HOSTS=tudominio.com,www.tudominio.com
   ```

2. **Base de Datos:**
   ```bash
   POSTGRES_PASSWORD=<contraseña-fuerte>
   ```

3. **HTTPS (con Nginx reverse proxy):**
   ```bash
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

---

## 📊 Monitoreo

### **Ver uso de recursos:**

```bash
# Estadísticas en tiempo real
docker stats

# Logs de un servicio específico
docker compose logs --tail=100 -f web

# Inspeccionar un contenedor
docker inspect seguros-web
```

---

## 🐛 Troubleshooting

### **Problema: Contenedores no inician**

```bash
# Ver logs de error
docker compose logs

# Reconstruir desde cero
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### **Problema: Error de migraciones**

```bash
# Ejecutar migraciones manualmente
docker compose exec web python manage.py migrate

# Verificar estado de base de datos
docker compose exec db psql -U postgres -d seguros -c "\dt"
```

### **Problema: Archivos estáticos no cargan**

```bash
# Recolectar estáticos manualmente
docker compose exec web python manage.py collectstatic --noinput
```

### **Problema: Celery no funciona**

```bash
# Ver logs de celery worker
docker compose logs -f celery-worker

# Ver logs de celery beat
docker compose logs -f celery-beat

# Reiniciar celery
docker compose restart celery-worker celery-beat
```

---

## 🌐 Deployment en Servidor Real

### **Con Docker Compose (VPS/Cloud):**

1. **Conectar al servidor:**
   ```bash
   ssh user@your-server.com
   ```

2. **Clonar repositorio:**
   ```bash
   git clone https://github.com/reeenatamc/seguros-arqsoft.git
   cd seguros-arqsoft
   ```

3. **Configurar:**
   ```bash
   cp .env.docker .env.production
   nano .env.production  # Editar configuración
   ```

4. **Levantar:**
   ```bash
   docker compose --env-file .env.production up -d
   ```

5. **Configurar Nginx (opcional):**
   - Proxy reverso para HTTPS
   - Servir archivos estáticos
   - SSL con Let's Encrypt

---

## 📦 Estructura de Contenedores

```
seguros-network
├── seguros-db (PostgreSQL)
├── seguros-redis (Redis)
├── seguros-web (Django + Gunicorn)
├── seguros-celery-worker (Tareas async)
└── seguros-celery-beat (Tareas programadas)
```

---

## ✅ Checklist de Deployment

- [ ] Configurar `.env.production` con valores reales
- [ ] Cambiar `DEBUG=False`
- [ ] Generar `SECRET_KEY` seguro
- [ ] Configurar contraseñas de BD
- [ ] Configurar `ALLOWED_HOSTS`
- [ ] Configurar email SMTP
- [ ] Construir imágenes: `docker compose build`
- [ ] Levantar servicios: `docker compose up -d`
- [ ] Verificar health checks: `docker compose ps`
- [ ] Crear superusuario
- [ ] Verificar acceso web
- [ ] Probar Celery tasks

---

## 🔗 URLs Importantes

Una vez desplegado:

- **Aplicación**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **Dashboard**: http://localhost:8000/
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

---

**¡Listo para deployar! Sigue los pasos según tu necesidad (desarrollo o producción).** 🚀
