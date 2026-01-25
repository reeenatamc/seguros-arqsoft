@echo off
REM ============================================
REM Setup Script para Pipeline CI/CD (Windows)
REM Sistema de Gestión de Seguros
REM ============================================

echo.
echo ════════════════════════════════════════════
echo   Pipeline CI/CD - Setup para Windows
echo ════════════════════════════════════════════
echo.

REM ============================================
REM 1. Verificar Python
REM ============================================
echo [1/10] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado
    pause
    exit /b 1
)
python --version
echo [OK] Python instalado
echo.

REM ============================================
REM 2. Crear entorno virtual
REM ============================================
echo [2/10] Configurando entorno virtual...
if exist venv (
    echo [WARN] Entorno virtual ya existe, saltando...
) else (
    python -m venv venv
    echo [OK] Entorno virtual creado
)
echo.

REM ============================================
REM 3. Activar entorno virtual
REM ============================================
echo [3/10] Activando entorno virtual...
call venv\Scripts\activate.bat
echo [OK] Entorno virtual activado
echo.

REM ============================================
REM 4. Actualizar pip
REM ============================================
echo [4/10] Actualizando pip...
python -m pip install --upgrade pip
echo [OK] pip actualizado
echo.

REM ============================================
REM 5. Instalar dependencias
REM ============================================
echo [5/10] Instalando dependencias...
echo Instalando dependencias principales...
pip install -r requirements.txt
echo.
echo Instalando dependencias de desarrollo...
pip install -r requirements-dev.txt
echo [OK] Dependencias instaladas
echo.

REM ============================================
REM 6. Configurar pre-commit
REM ============================================
echo [6/10] Configurando pre-commit hooks...
pre-commit install
echo [OK] Pre-commit hooks instalados
echo.

REM ============================================
REM 7. Verificar archivo .env
REM ============================================
echo [7/10] Verificando configuración...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo [OK] Archivo .env creado desde .env.example
        echo [WARN] Por favor, configura las variables en .env
    ) else (
        echo [WARN] No se encontró .env.example
    )
) else (
    echo [OK] Archivo .env existe
)
echo.

REM ============================================
REM 8. Migraciones
REM ============================================
echo [8/10] Configurando base de datos...
echo Verificando migraciones...
python manage.py makemigrations --check --dry-run
echo.
echo Ejecutando migraciones...
python manage.py migrate
echo [OK] Migraciones aplicadas
echo.

REM ============================================
REM 9. Archivos estáticos
REM ============================================
echo [9/10] Recolectando archivos estáticos...
python manage.py collectstatic --no-input --clear
echo [OK] Archivos estáticos recolectados
echo.

REM ============================================
REM 10. Ejecutar verificaciones
REM ============================================
echo [10/10] Ejecutando verificaciones...
echo.
echo Ejecutando flake8...
flake8 .
echo.
echo Ejecutando black (check)...
black --check .
echo.
echo Ejecutando isort (check)...
isort --check-only .
echo.

REM ============================================
REM Resumen final
REM ============================================
echo.
echo ════════════════════════════════════════════════════════════
echo.
echo   [OK] Pipeline CI/CD configurado exitosamente!
echo.
echo   Próximos pasos:
echo   1. Configura las variables en .env
echo   2. Ejecuta: python manage.py runserver
echo   3. Ejecuta tests: pytest
echo   4. Haz commit de tus cambios
echo.
echo   Comandos útiles:
echo   - Formatear código: black . ^&^& isort .
echo   - Ejecutar tests: pytest --cov
echo   - Verificar seguridad: safety check ^&^& bandit -r app/
echo   - Pre-commit check: pre-commit run --all-files
echo.
echo   Para activar el entorno virtual en el futuro:
echo   venv\Scripts\activate.bat
echo.
echo ════════════════════════════════════════════════════════════
echo.
echo [OK] Listo para desarrollar!
echo.
pause
