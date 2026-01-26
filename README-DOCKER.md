# 🐳 Inicio Rápido con Docker

## ⚡ Comandos Rápidos

### **Opción 1: Script Automático (Recomendado)**

```bash
# Windows
docker-start.bat

# Linux/Mac
chmod +x docker-entrypoint.sh
docker compose up -d
```

### **Opción 2: Comandos Manuales**

#### **Producción:**
```bash
# 1. Configurar
cp .env.docker .env.production
# Editar .env.production con tus valores

# 2. Construir
docker compose build

# 3. Levantar
docker compose --env-file .env.production up -d

# 4. Ver logs
docker compose logs -f web
```

#### **Desarrollo:**
```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml logs -f
```

---

## 📦 Servicios Incluidos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **web** | 8000 | Django con Gunicorn |
| **db** | 5432 | PostgreSQL 15 |
| **redis** | 6379 | Redis para Celery |
| **celery-worker** | - | Tareas asíncronas |
| **celery-beat** | - | Tareas programadas |

---

## 🔧 Comandos Django en Docker

```bash
# Migraciones
docker compose exec web python manage.py migrate

# Crear superusuario
docker compose exec web python manage.py createsuperuser

# Shell de Django
docker compose exec web python manage.py shell

# Poblar datos
docker compose exec web python poblar_ejemplo.py

# Collectstatic
docker compose exec web python manage.py collectstatic --noinput
```

---

## 🛠️ Gestión

```bash
# Ver estado
docker compose ps

# Ver logs
docker compose logs -f web

# Reiniciar servicio
docker compose restart web

# Detener todo
docker compose down

# Detener y eliminar volúmenes (⚠️ BORRA LA BD)
docker compose down -v
```

---

## 📊 Monitoreo

```bash
# Recursos en tiempo real
docker stats

# Logs de Celery
docker compose logs -f celery-worker
docker compose logs -f celery-beat

# Health check
curl http://localhost:8000/admin/login/
```

---

## 🌐 Acceso

Una vez iniciado:
- **App**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **Credenciales**: admin / (configurado en .env.production)

---

## ⚠️ Notas Importantes

1. **Primera vez**: El build puede tomar 5-10 minutos
2. **Producción**: Edita `.env.production` antes de iniciar
3. **Base de datos**: Los datos se guardan en volumen Docker `postgres_data`
4. **Logs**: Se guardan en `./logs/`

---

Para más detalles, consulta `DOCKER-DEPLOYMENT.md`
