# 🚀 Pipeline CI/CD - Guía Rápida

## Configuración Inicial (Primera Vez)

### Windows
```bash
setup-pipeline.bat
```

### Linux/macOS
```bash
chmod +x setup-pipeline.sh
./setup-pipeline.sh
```

## Comandos Esenciales

### 🔍 Verificar Código
```bash
# Verificar todo
flake8 .
black --check .
isort --check-only .

# Arreglar automáticamente
black .
isort .
```

### 🧪 Ejecutar Tests
```bash
# Tests básicos
pytest

# Con cobertura
pytest --cov=app --cov=seguros --cov-report=html

# Tests específicos
pytest app/tests.py -v
pytest -m "not slow"
```

### 🔒 Verificar Seguridad
```bash
# Vulnerabilidades
safety check --file requirements.txt

# Análisis de código
bandit -r app/ seguros/ -ll

# Ambos
safety check && bandit -r app/ seguros/
```

### 🏗️ Verificar Build
```bash
# Migraciones
python manage.py makemigrations --check

# Configuración
python manage.py check --deploy

# Archivos estáticos
python manage.py collectstatic --no-input
```

### ✨ Pre-commit Hooks
```bash
# Instalar
pre-commit install

# Ejecutar en todos los archivos
pre-commit run --all-files

# Ejecutar en archivos modificados
git add .
git commit -m "mensaje"  # Los hooks se ejecutan automáticamente
```

## Flujo de Trabajo Recomendado

### 1. Antes de Commit
```bash
# Formatear código
black .
isort .

# Verificar
flake8 .
pytest --cov
```

### 2. Commit
```bash
git add .
git commit -m "feat: descripción del cambio"
# Los pre-commit hooks se ejecutan automáticamente
```

### 3. Push
```bash
git push origin tu-rama
# El pipeline CI/CD se ejecuta automáticamente en GitHub
```

## Estructura del Pipeline

```
Push/PR → Lint (2-3min) → Test (5-8min) → Security (3-5min) → Build (2-3min) → Deploy (Manual)
                   ↓              ↓              ↓               ↓
                 flake8       pytest         safety          migrations
                 black        coverage       bandit          collectstatic
                 isort        migrations                     check --deploy
```

## Solución Rápida de Problemas

### ❌ Falla Lint
```bash
black .
isort .
```

### ❌ Fallan Tests
```bash
pytest -vv --tb=long
python manage.py makemigrations
python manage.py migrate
```

### ❌ Baja Cobertura
```bash
pytest --cov=app --cov-report=html
# Abrir htmlcov/index.html
```

### ❌ Vulnerabilidades
```bash
pip install --upgrade nombre_paquete
pip freeze > requirements.txt
```

## Archivos Importantes

```
.github/workflows/ci.yml     # Pipeline principal
.flake8                      # Config de linting
pytest.ini                   # Config de tests
.pre-commit-config.yaml      # Pre-commit hooks
requirements-dev.txt         # Deps de desarrollo
PIPELINE.md                  # Documentación completa
```

## Métricas de Calidad

| Métrica | Objetivo |
|---------|----------|
| Cobertura | > 70% |
| Complejidad | < 10 |
| Vulnerabilidades | 0 |
| Tests pasando | 100% |

## Enlaces Útiles

- 📚 [Documentación Completa](PIPELINE.md)
- 🐛 [Troubleshooting](PIPELINE.md#troubleshooting)
- 📊 [Métricas y KPIs](PIPELINE.md#métricas-y-kpis)

---

**¿Necesitas ayuda?** Lee la [documentación completa](PIPELINE.md) 📖
