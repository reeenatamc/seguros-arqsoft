# 🚀 Inicio Rápido - 5 Minutos

Esta guía te ayudará a tener el sistema funcionando en menos de 5 minutos.

## ⚡ Instalación Express

### 1. Instalar Dependencias (2 minutos)

```bash
# Opción A: Usando el script automático (RECOMENDADO)
./setup.sh

# Opción B: Manual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Base de Datos (1 minuto)

```bash
# Si usaste setup.sh, esto ya está hecho. Si no:
python manage.py makemigrations
python manage.py migrate
```

### 3. Crear Superusuario (1 minuto)

```bash
python manage.py createsuperuser

# Te pedirá:
# - Username: admin
# - Email: tu@email.com
# - Password: (elige una contraseña segura)
```

### 4. Iniciar Servidor (30 segundos)

```bash
python manage.py runserver
```

### 5. Acceder al Sistema (30 segundos)

Abre tu navegador en: **http://localhost:8000/admin/**

---

## 🎯 Primeros Pasos en el Sistema

### 1. Crear Datos Básicos

En el admin, crea en este orden:

1. **Compañías Aseguradoras**
   - Admin > Compañías Aseguradoras > Agregar
   - Ej: "Seguros del Pichincha", "Equinoccial"

2. **Corredores de Seguros**
   - Admin > Corredores de Seguros > Agregar
   - Ej: "AON Ecuador", "Marsh Ecuador"

3. **Tipos de Póliza**
   - Admin > Tipos de Póliza > Agregar
   - Ej: "Todo Riesgo", "Incendio", "Robo"

4. **Tipos de Siniestro**
   - Admin > Tipos de Siniestro > Agregar
   - Ej: "Daño", "Robo", "Incendio"

### 2. Crear Tu Primera Póliza

1. Ve a **Pólizas > Agregar Póliza**
2. Llena los campos:
   - Número de póliza: P-2024-001
   - Compañía: (selecciona una)
   - Corredor: (selecciona uno)
   - Tipo: (selecciona uno)
   - Suma asegurada: 100000
   - Fechas de vigencia
3. Guarda

### 3. Crear Una Factura

1. Ve a **Facturas > Agregar Factura**
2. Selecciona la póliza
3. Ingresa:
   - Número de factura: F-001
   - Fechas
   - Subtotal: 1000
4. El sistema calculará automáticamente:
   - Contribuciones
   - Descuento (si aplica)
   - Total

### 4. Registrar un Siniestro

1. Ve a **Siniestros > Agregar Siniestro**
2. Llena los datos del bien afectado
3. Describe el siniestro
4. Guarda

---

## 🔔 Activar Alertas Automáticas (Opcional)

### Requisito: Redis

```bash
# Mac
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Verificar
redis-cli ping  # Debe responder: PONG
```

### Iniciar Celery

En terminales separadas:

```bash
# Terminal 1: Worker
celery -A seguros worker -l info

# Terminal 2: Beat (tareas periódicas)
celery -A seguros beat -l info
```

---

## 📊 Generar Reportes

### Reportes de Pólizas

```bash
# Todas las pólizas
python manage.py generar_reporte_polizas

# Solo vigentes
python manage.py generar_reporte_polizas --estado=vigente

# Los reportes se guardan en: media/reportes/polizas/
```

### Reportes de Siniestros

```bash
# Reporte mensual
python manage.py generar_reporte_siniestros --periodo=mensual

# Los reportes se guardan en: media/reportes/siniestros/
```

---

## 🧪 Probar Alertas

### Generar Alertas Manualmente

```bash
python manage.py generar_alertas --tipo=todas
```

### Ver Alertas en el Admin

Ve a: **Admin > Alertas**

---

## 📝 Flujo de Trabajo Típico

```
1. Registrar Póliza
   ↓
2. Registrar Factura de la Póliza
   ↓
3. Registrar Pagos de la Factura
   ↓
4. Si ocurre un siniestro → Registrar Siniestro
   ↓
5. Adjuntar documentos
   ↓
6. Actualizar estado del siniestro
   ↓
7. Generar reportes periódicos
```

---

## 🆘 Solución Rápida de Problemas

### "ModuleNotFoundError"
```bash
# Asegúrate de estar en el entorno virtual
source venv/bin/activate
pip install -r requirements.txt
```

### "django.db.utils.OperationalError"
```bash
# Aplica las migraciones
python manage.py migrate
```

### "No such file or directory: 'logs/django.log'"
```bash
# Crea el directorio
mkdir -p logs
```

### El admin no se ve bien
```bash
# Recolecta archivos estáticos
python manage.py collectstatic --no-input
```

---

## 🎓 Recursos de Aprendizaje

### Para entender el sistema:
1. Lee: `README.md` (guía completa)
2. Explora: Django Admin
3. Prueba: Crear, editar, eliminar registros

### Para personalizar:
1. Lee: `ARCHITECTURE.md` (arquitectura)
2. Revisa: `app/models.py` (estructura de datos)
3. Modifica: `app/admin.py` (interfaz admin)

### Para desplegar:
1. Lee: `DEPLOYMENT.md` (producción)
2. Configura: PostgreSQL, Nginx, Supervisor
3. Asegura: SSL, backups, monitoreo

---

## ✅ Checklist de Inicio

- [ ] Script setup.sh ejecutado exitosamente
- [ ] Superusuario creado
- [ ] Acceso al admin funcionando
- [ ] Compañías aseguradoras creadas
- [ ] Corredores creados
- [ ] Tipos de póliza creados
- [ ] Tipos de siniestro creados
- [ ] Primera póliza creada
- [ ] Primera factura creada
- [ ] Redis instalado (opcional)
- [ ] Celery funcionando (opcional)

---

## 🚀 ¡Listo para Producción!

Cuando estés listo para producción:

1. Cambia `DEBUG=False` en `.env`
2. Configura `ALLOWED_HOSTS` en `.env`
3. Usa PostgreSQL en lugar de SQLite
4. Configura email SMTP real
5. Sigue la guía en `DEPLOYMENT.md`

---

## 💡 Consejos Pro

### Performance:
- Usa PostgreSQL para producción
- Configura índices si tienes muchos datos
- Habilita cache con Redis

### Seguridad:
- Cambia el SECRET_KEY en producción
- Usa contraseñas fuertes
- Habilita HTTPS
- Configura firewall

### Mantenimiento:
- Haz backups regulares
- Revisa logs periódicamente
- Actualiza dependencias
- Monitorea el sistema

---

## 📞 ¿Necesitas Ayuda?

1. **Primero**: Revisa la documentación en `README.md`
2. **Luego**: Busca en `ARCHITECTURE.md` para detalles técnicos
3. **Si vas a producción**: Lee `DEPLOYMENT.md`
4. **Para desarrollo**: Revisa el código (está bien comentado)

---

## 🎉 ¡Éxito!

Si llegaste hasta aquí, tu sistema ya está funcionando. 

**Próximos pasos sugeridos:**
1. Familiarízate con la interfaz
2. Crea datos de prueba
3. Genera algunos reportes
4. Configura las alertas
5. Personaliza según tus necesidades

---

**¡Bienvenido al Sistema de Gestión de Seguros UTPL!**

_Para más información, consulta README.md_
