# Pipeline CI/CD - Sistema de Gestión de Seguros

Este documento describe el pipeline de CI/CD configurado para el proyecto.

## 📋 Descripción General

El pipeline está configurado usando **GitHub Actions** y se ejecuta automáticamente en cada push y pull request a las ramas principales (`main`, `develop`, `master`).

## 🔄 Flujo del Pipeline

```
┌─────────────┐
│   Push/PR   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  1. LINT                            │
│  - flake8                           │
│  - black (check)                    │
│  - isort (check)                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  2. TEST                            │
│  - pytest                           │
│  - coverage                         │
│  - migraciones                      │
│  - collectstatic                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  3. SECURITY                        │
│  - safety (vulnerabilidades)        │
│  - bandit (análisis código)         │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  4. BUILD                           │
│  - Verificar migraciones            │
│  - Verificar configuración          │
│  - collectstatic                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  5. DEPLOY (Manual)                 │
│  - Solo en main/master              │
│  - Requiere aprobación manual       │
└─────────────────────────────────────┘
```

## 📦 Jobs del Pipeline

### 1. Lint
**Duración estimada:** 2-3 minutos

Verifica la calidad del código:
- **flake8**: Análisis estático de código Python
- **black**: Verificación de formato de código
- **isort**: Verificación de orden de imports

**Configuración:**
- Máximo 120 caracteres por línea
- Complejidad máxima: 10
- Ignora migraciones y archivos estáticos

### 2. Test
**Duración estimada:** 5-8 minutos

Ejecuta los tests y verificaciones:
- **pytest**: Ejecuta tests unitarios e integración
- **coverage**: Genera reporte de cobertura
- **makemigrations --check**: Verifica que no haya migraciones pendientes
- **migrate**: Aplica migraciones en base de datos de test
- **check --deploy**: Verifica configuración de producción
- **collectstatic**: Verifica que los archivos estáticos se pueden recolectar

**Servicios:**
- PostgreSQL 14 (base de datos de test)
- Redis 7 (para Celery)

### 3. Security
**Duración estimada:** 3-5 minutos

Análisis de seguridad:
- **safety**: Verifica vulnerabilidades en dependencias
- **bandit**: Análisis estático de seguridad del código

### 4. Build
**Duración estimada:** 2-3 minutos

Verificación de build:
- Verifica que no haya migraciones pendientes
- Verifica configuración de producción
- Recolecta archivos estáticos

**Nota:** Este job solo se ejecuta si todos los jobs anteriores pasan.

### 5. Deploy (Manual)
**Duración estimada:** Variable

Deploy a producción:
- Solo se ejecuta en ramas `main` o `master`
- Requiere aprobación manual
- Actualmente está comentado (configurar según entorno)

## 🚀 Uso Local

### Ejecutar Linting

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecutar flake8
flake8 .

# Formatear código con black
black .

# Ordenar imports con isort
isort .
```

### Ejecutar Tests

```bash
# Ejecutar todos los tests
pytest

# Ejecutar con coverage
pytest --cov=app --cov-report=html

# Ejecutar tests específicos
pytest app/tests.py -v
```

### Verificar Seguridad

```bash
# Verificar vulnerabilidades
safety check --file requirements.txt

# Análisis de seguridad del código
bandit -r app/ seguros/
```

### Pre-commit Hooks (Opcional)

```bash
# Instalar hooks
pre-commit install

# Ejecutar manualmente
pre-commit run --all-files
```

## 📊 Reportes

Los reportes se generan automáticamente en GitHub Actions:

- **Coverage**: Disponible en el artefacto del job de test
- **Bandit**: Disponible en `bandit-report.json`
- **Test Results**: Mostrados en la interfaz de GitHub Actions

## ⚙️ Configuración

### Variables de Entorno en GitHub

Para el deploy, configurar los siguientes secrets en GitHub:

- `HOST`: Dirección del servidor de producción
- `USERNAME`: Usuario SSH
- `SSH_KEY`: Clave privada SSH

### Personalizar el Pipeline

El archivo principal del pipeline está en:
```
.github/workflows/ci.yml
```

### Configuración de Herramientas

- **flake8**: `.flake8`
- **pytest**: `pytest.ini`
- **pre-commit**: `.pre-commit-config.yaml`

## 🔧 Troubleshooting

### El pipeline falla en linting

```bash
# Verificar errores localmente
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Formatear código automáticamente
black .
isort .
```

### El pipeline falla en tests

```bash
# Ejecutar tests localmente
pytest -v

# Verificar migraciones
python manage.py makemigrations --check

# Verificar configuración
python manage.py check --deploy
```

### El pipeline falla en seguridad

```bash
# Actualizar dependencias vulnerables
safety check --file requirements.txt

# Revisar y corregir problemas de seguridad
bandit -r app/ seguros/ -ll
```

## 📝 Mejoras Futuras

- [ ] Agregar tests de integración con Docker
- [ ] Configurar deploy automático a staging
- [ ] Agregar notificaciones (Slack, Email)
- [ ] Agregar análisis de performance
- [ ] Agregar tests de carga
- [ ] Configurar cache de dependencias
- [ ] Agregar matrix testing (múltiples versiones de Python/Django)

## 📚 Referencias

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)

---

**Universidad Técnica Particular de Loja**  
Pipeline CI/CD - Sistema de Gestión de Seguros
