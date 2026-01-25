# Pipeline CI/CD - Sistema de Gestión de Seguros 🚀

## 📋 Descripción General

Este documento describe el pipeline de CI/CD configurado para el Sistema de Gestión de Seguros desarrollado en Django. El pipeline está implementado usando **GitHub Actions** y se ejecuta automáticamente en cada push y pull request a las ramas principales.

### 🎯 Objetivos del Pipeline

- ✅ Garantizar la calidad del código
- 🧪 Ejecutar tests automáticamente
- 🔒 Verificar seguridad
- 🏗️ Validar builds
- 🚀 Facilitar despliegues seguros

---

## 🔄 Flujo del Pipeline

```
┌─────────────────────────────────────┐
│         Push / Pull Request          │
│    (main, develop, master)          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  JOB 1: LINT (2-3 min)             │
│  ────────────────────────────       │
│  🔍 flake8   - Análisis estático    │
│  ⚫ black    - Formato de código    │
│  📋 isort    - Orden de imports     │
└──────────────┬──────────────────────┘
               │
               ├──────────────────┐
               │                  │
               ▼                  ▼
┌──────────────────────┐  ┌──────────────────────┐
│ JOB 2: TEST (5-8min) │  │ JOB 3: SECURITY      │
│ ──────────────────── │  │ (3-5 min)            │
│ 🧪 pytest            │  │ ────────────────     │
│ 📊 coverage          │  │ 🛡️ safety            │
│ 🗄️ migrations        │  │ 🔐 bandit            │
│ ✅ collectstatic     │  │                      │
└──────────┬───────────┘  └─────────┬────────────┘
           │                        │
           └──────────┬─────────────┘
                      │
                      ▼
           ┌────────────────────────┐
           │ JOB 4: BUILD (2-3 min) │
           │ ────────────────────── │
           │ 🏗️ Verificar build     │
           │ ✅ Configuración       │
           │ 📁 Static files        │
           └──────────┬─────────────┘
                      │
                      ▼
           ┌────────────────────────┐
           │ JOB 5: DEPLOY (Manual) │
           │ ────────────────────── │
           │ 🚀 Solo main/master    │
           │ ⏸️ Aprobación manual   │
           └────────────────────────┘
```

---

## 📦 Descripción Detallada de los Jobs

### 1️⃣ JOB 1: LINT - Verificación de Calidad de Código

**Duración:** 2-3 minutos  
**Ejecuta en:** Todas las ramas

#### ¿Qué hace?

Verifica que el código cumpla con los estándares de calidad y estilo de Python.

#### Herramientas utilizadas:

##### 🔍 **flake8** - Análisis Estático
- Verifica errores de sintaxis
- Detecta código no utilizado
- Valida estilo PEP 8
- Complejidad ciclomática (máx: 10)
- Longitud de línea (máx: 120 caracteres)

```bash
# Comandos ejecutados
flake8 . --count --statistics --show-source
```

##### ⚫ **black** - Formateador de Código
- Verifica formato consistente
- Asegura estilo uniforme
- Compatible con PEP 8

```bash
black --check --diff .
```

##### 📋 **isort** - Orden de Imports
- Organiza imports alfabéticamente
- Separa imports por categorías
- Compatible con black

```bash
isort --check-only --diff .
```

#### Archivos de configuración:
- `.flake8` - Configuración de flake8
- `pyproject.toml` o argumentos inline para black/isort

---

### 2️⃣ JOB 2: TEST - Pruebas Unitarias y Cobertura

**Duración:** 5-8 minutos  
**Ejecuta en:** Todas las ramas  
**Depende de:** Job 1 (Lint)

#### ¿Qué hace?

Ejecuta todos los tests unitarios e integración, genera reportes de cobertura y verifica migraciones.

#### Servicios auxiliares:

##### 🐘 **PostgreSQL 14**
```yaml
postgres:
  image: postgres:14
  env:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    POSTGRES_DB: test_seguros
  port: 5432
```

##### 🔴 **Redis 7**
```yaml
redis:
  image: redis:7
  port: 6379
```

#### Pasos ejecutados:

1. **Instalación de dependencias del sistema**
   ```bash
   sudo apt-get install -y libmagic1 libpq-dev
   ```

2. **Configuración de variables de entorno**
   ```bash
   SECRET_KEY=test-secret-key
   DEBUG=False
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_seguros
   CELERY_BROKER_URL=redis://localhost:6379/0
   ```

3. **Verificación de migraciones**
   ```bash
   python manage.py makemigrations --check --dry-run --no-input
   ```

4. **Aplicación de migraciones**
   ```bash
   python manage.py migrate --no-input
   ```

5. **Verificación de configuración**
   ```bash
   python manage.py check --deploy --fail-level WARNING
   ```

6. **Recolección de archivos estáticos**
   ```bash
   python manage.py collectstatic --no-input --clear
   ```

7. **Ejecución de tests**
   ```bash
   pytest --verbose --tb=short \
     --cov=app --cov=seguros \
     --cov-report=term-missing \
     --cov-report=xml \
     --cov-report=html
   ```

#### Reportes generados:

- 📊 **Coverage Report HTML** - Visualización de cobertura
- 📄 **Coverage XML** - Para integración con herramientas
- 📈 **Test Results** - Resultados detallados de tests

#### Umbral de cobertura:
- **Mínimo requerido:** 70%
- **Recomendado:** 80%+

---

### 3️⃣ JOB 3: SECURITY - Análisis de Seguridad

**Duración:** 3-5 minutos  
**Ejecuta en:** Todas las ramas  
**Depende de:** Job 1 (Lint)

#### ¿Qué hace?

Analiza el código y las dependencias en busca de vulnerabilidades de seguridad.

#### Herramientas utilizadas:

##### 🛡️ **safety** - Vulnerabilidades en Dependencias
Verifica todas las dependencias en `requirements.txt` contra una base de datos de vulnerabilidades conocidas.

```bash
safety check --file requirements.txt --output text
```

**Detecta:**
- CVEs conocidos
- Vulnerabilidades de seguridad
- Versiones desactualizadas con problemas

##### 🔐 **bandit** - Análisis de Seguridad del Código
Analiza el código Python en busca de problemas de seguridad comunes.

```bash
bandit -r app/ seguros/ -ll -f json -o bandit-report.json
```

**Detecta:**
- Uso de funciones inseguras
- SQL injection potencial
- Manejo inseguro de archivos
- Uso de `eval()` o `exec()`
- Problemas de criptografía
- Configuraciones inseguras

#### Reportes generados:
- 📊 `bandit-report.json` - Reporte completo de seguridad

---

### 4️⃣ JOB 4: BUILD - Verificación de Construcción

**Duración:** 2-3 minutos  
**Ejecuta en:** Todas las ramas  
**Depende de:** Jobs 2 y 3 (Test y Security)

#### ¿Qué hace?

Verifica que el proyecto se pueda construir correctamente para producción.

#### Pasos ejecutados:

1. **Verificación de migraciones**
   ```bash
   python manage.py makemigrations --check
   ```

2. **Verificación de configuración de producción**
   ```bash
   python manage.py check --deploy --fail-level WARNING
   ```
   
   Verifica:
   - SECRET_KEY configurado
   - DEBUG=False
   - ALLOWED_HOSTS configurado
   - HTTPS configurado
   - Middleware de seguridad
   - Cookies seguras

3. **Recolección de archivos estáticos**
   ```bash
   python manage.py collectstatic --no-input --clear
   ```

4. **Información de versiones**
   - Versión de Python
   - Versión de Django
   - Dependencias instaladas

---

### 5️⃣ JOB 5: DEPLOY - Despliegue a Producción

**Duración:** Variable  
**Ejecuta en:** Solo ramas main/master  
**Depende de:** Job 4 (Build)  
**Tipo:** Manual (requiere aprobación)

#### ¿Qué hace?

Despliega la aplicación a producción después de pasar todos los checks.

#### Configuración requerida:

##### Secrets en GitHub:
```yaml
HOST: servidor-produccion.com
USERNAME: usuario_ssh
SSH_KEY: -----BEGIN RSA PRIVATE KEY-----
```

#### Pasos de deploy (ejemplo):

```bash
# 1. Conectar al servidor
ssh $USERNAME@$HOST

# 2. Actualizar código
cd /path/to/app
git pull origin main

# 3. Activar entorno virtual
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Ejecutar migraciones
python manage.py migrate --no-input

# 6. Recolectar archivos estáticos
python manage.py collectstatic --no-input

# 7. Reiniciar servicios
sudo systemctl restart gunicorn
sudo systemctl restart nginx
sudo systemctl restart celery
```

#### ⚠️ Nota importante:
El código de deploy está **comentado** por defecto. Debe configurarse según el entorno de producción específico.

---

## 🚀 Uso Local del Pipeline

### 1. Instalación de dependencias

```bash
# Dependencias principales
pip install -r requirements.txt

# Dependencias de desarrollo
pip install -r requirements-dev.txt
```

### 2. Configurar Pre-commit Hooks

```bash
# Instalar pre-commit
pip install pre-commit

# Instalar hooks
pre-commit install

# Ejecutar manualmente
pre-commit run --all-files
```

### 3. Ejecutar Linting

```bash
# flake8
flake8 .

# black (verificar)
black --check .

# black (formatear)
black .

# isort (verificar)
isort --check-only .

# isort (ordenar)
isort .
```

### 4. Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=app --cov=seguros --cov-report=html

# Tests específicos
pytest app/tests.py -v

# Tests marcados
pytest -m "not slow"
pytest -m "integration"

# Tests en paralelo
pytest -n auto
```

### 5. Verificar Seguridad

```bash
# Verificar dependencias
safety check --file requirements.txt

# Análisis de código
bandit -r app/ seguros/ -ll

# Ambos
safety check && bandit -r app/ seguros/
```

### 6. Comandos de Django

```bash
# Verificar migraciones
python manage.py makemigrations --check

# Verificar configuración
python manage.py check --deploy

# Recolectar estáticos
python manage.py collectstatic --no-input
```

---

## ⚙️ Configuración

### Archivos de configuración creados:

```
seguros-arqsoft-main/
├── .github/
│   └── workflows/
│       └── ci.yml                    # Pipeline principal
├── .flake8                          # Configuración de flake8
├── pytest.ini                       # Configuración de pytest
├── .pre-commit-config.yaml          # Pre-commit hooks
├── requirements.txt                 # Dependencias principales
├── requirements-dev.txt             # Dependencias de desarrollo
└── PIPELINE.md                      # Esta documentación
```

### Variables de entorno para GitHub Actions:

#### Secrets requeridos (para deploy):
```
HOST              # Servidor de producción
USERNAME          # Usuario SSH
SSH_KEY           # Clave privada SSH
```

#### Variables de entorno automáticas:
```
PYTHON_VERSION           # 3.11
DJANGO_SETTINGS_MODULE   # seguros.settings
SECRET_KEY               # Generado automáticamente
DATABASE_URL             # PostgreSQL de test
CELERY_BROKER_URL        # Redis de test
```

---

## 📊 Reportes y Artefactos

### Artefactos generados:

1. **Coverage Report** (htmlcov/)
   - Visualización interactiva de cobertura
   - Líneas cubiertas/no cubiertas
   - Descargable desde GitHub Actions

2. **Coverage XML** (coverage.xml)
   - Para integración con herramientas
   - Formato estándar

3. **Security Report** (bandit-report.json)
   - Vulnerabilidades encontradas
   - Severidad y ubicación
   - Recomendaciones

### Acceso a reportes:

```
GitHub Actions → Workflow Run → Artifacts
├── coverage-report.zip
└── security-reports.zip
```

---

## 🔧 Troubleshooting

### ❌ El pipeline falla en Lint

#### Problema: Errores de flake8
```bash
# Ver errores específicos
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Arreglar formato automáticamente
black .
isort .
```

#### Problema: Líneas muy largas
```python
# Mal ❌
def very_long_function_name_that_exceeds_the_maximum_line_length_of_120_characters():

# Bien ✅
def very_long_function_name_that_exceeds_maximum_length():
```

### ❌ El pipeline falla en Tests

#### Problema: Tests fallan
```bash
# Ejecutar tests con más detalles
pytest -vv --tb=long

# Ver errores específicos
pytest app/tests.py::test_function_name -vv
```

#### Problema: Migraciones pendientes
```bash
# Crear migraciones
python manage.py makemigrations

# Verificar
python manage.py makemigrations --check
```

#### Problema: Baja cobertura
```bash
# Ver reporte detallado
pytest --cov=app --cov-report=html
# Abrir htmlcov/index.html

# Ver archivos con baja cobertura
coverage report --show-missing
```

### ❌ El pipeline falla en Security

#### Problema: Vulnerabilidades en dependencias
```bash
# Ver vulnerabilidades
safety check --file requirements.txt

# Actualizar paquete específico
pip install --upgrade nombre_paquete

# Actualizar requirements.txt
pip freeze > requirements.txt
```

#### Problema: Código inseguro
```bash
# Ver detalles
bandit -r app/ seguros/ -ll -v

# Ignorar falsos positivos
# En el código:
# nosec comment
```

### ❌ El pipeline falla en Build

#### Problema: collectstatic falla
```bash
# Verificar STATIC_ROOT
python manage.py findstatic archivo.css

# Limpiar y volver a recolectar
python manage.py collectstatic --clear --no-input
```

---

## 📈 Métricas y KPIs

### Tiempos esperados:

| Job | Duración | Tolerancia |
|-----|----------|-----------|
| Lint | 2-3 min | ±30 seg |
| Test | 5-8 min | ±1 min |
| Security | 3-5 min | ±1 min |
| Build | 2-3 min | ±30 seg |
| **Total** | **12-19 min** | **±2 min** |

### Objetivos de calidad:

| Métrica | Objetivo | Mínimo |
|---------|----------|--------|
| Cobertura de tests | 80% | 70% |
| Complejidad ciclomática | < 8 | < 10 |
| Vulnerabilidades | 0 | 0 críticas |
| Tests pasando | 100% | 100% |

---

## 🎯 Mejoras Futuras

### Alta Prioridad:
- [ ] Configurar cache de dependencias (pip cache)
- [ ] Agregar notificaciones (Slack/Email)
- [ ] Configurar deploy automático a staging

### Media Prioridad:
- [ ] Matrix testing (Python 3.10, 3.11, 3.12)
- [ ] Tests de integración con Docker
- [ ] Análisis de performance con locust

### Baja Prioridad:
- [ ] Tests de carga automatizados
- [ ] Documentación automática con Sphinx
- [ ] Análisis de calidad de código con SonarQube

---

## 📚 Referencias y Documentación

### GitHub Actions:
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

### Testing:
- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/4.2/topics/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

### Code Quality:
- [flake8 Documentation](https://flake8.pycqa.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)

### Security:
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://pyup.io/safety/)

### Django:
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Django Best Practices](https://docs.djangoproject.com/en/4.2/misc/design-philosophies/)

---

## 👥 Equipo y Soporte

### Universidad Técnica Particular de Loja
**Sistema de Gestión de Seguros**

**Materia:** Arquitectura de Software  
**Ciclo:** 7mo

### Contacto:
- Para issues: [GitHub Issues](https://github.com/tu-repo/issues)
- Para dudas: Crear discusión en GitHub

---

## 📝 Changelog

### Versión 1.0.0 (Enero 2026)
- ✅ Pipeline CI/CD inicial
- ✅ Jobs de Lint, Test, Security, Build
- ✅ Configuración de pre-commit hooks
- ✅ Tests básicos implementados
- ✅ Documentación completa

---

**Última actualización:** Enero 23, 2026  
**Versión del Pipeline:** 1.0.0  
**Estado:** ✅ Producción
