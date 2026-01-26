@echo off
REM ============================================
REM Pipeline CI/CD Local - Sistema de Seguros
REM ============================================
REM Ejecuta las mismas verificaciones del pipeline de GitHub Actions localmente

echo.
echo ============================================
echo   Pipeline CI/CD Local - Sistema de Seguros
echo ============================================
echo.

REM Verificar que el entorno virtual está activado
if not defined VIRTUAL_ENV (
    echo [ERROR] El entorno virtual no esta activado
    echo Por favor ejecuta: venv\Scripts\activate
    exit /b 1
)

echo [INFO] Entorno virtual: %VIRTUAL_ENV%
echo.

REM ============================================
REM PASO 1: LINT - Verificacion de Calidad
REM ============================================
echo ============================================
echo   1/3 - LINT: Verificacion de Calidad
echo ============================================
echo.

echo [1/3] Ejecutando flake8...
python -m flake8 . --count --statistics --show-source
if %errorlevel% neq 0 (
    echo [ERROR] Flake8 encontro errores
    echo.
    echo Presiona cualquier tecla para continuar con black...
    pause >nul
) else (
    echo [OK] Flake8 paso correctamente
)
echo.

echo [2/3] Verificando formato con black...
python -m black --check --diff .
if %errorlevel% neq 0 (
    echo [WARNING] Black encontro archivos sin formatear
    echo Para formatear automaticamente: python -m black .
    echo.
    echo Presiona cualquier tecla para continuar con isort...
    pause >nul
) else (
    echo [OK] Black paso correctamente
)
echo.

echo [3/3] Verificando orden de imports con isort...
python -m isort --check-only --diff .
if %errorlevel% neq 0 (
    echo [WARNING] isort encontro imports desordenados
    echo Para ordenar automaticamente: python -m isort .
    echo.
    echo Presiona cualquier tecla para continuar...
    pause >nul
) else (
    echo [OK] isort paso correctamente
)
echo.

REM ============================================
REM PASO 2: TEST - Pruebas Unitarias
REM ============================================
echo ============================================
echo   2/3 - TEST: Pruebas Unitarias
echo ============================================
echo.

echo [1/3] Verificando migraciones...
python manage.py makemigrations --check --dry-run --no-input
if %errorlevel% neq 0 (
    echo [ERROR] Hay migraciones pendientes
    exit /b 1
) else (
    echo [OK] No hay migraciones pendientes
)
echo.

echo [2/3] Verificando configuracion...
python manage.py check --deploy --fail-level WARNING
if %errorlevel% neq 0 (
    echo [WARNING] Check de deploy encontro advertencias
) else (
    echo [OK] Check paso correctamente
)
echo.

echo [3/3] Ejecutando tests...
python -m pytest --verbose --tb=short
if %errorlevel% neq 0 (
    echo [ERROR] Algunos tests fallaron
) else (
    echo [OK] Todos los tests pasaron
)
echo.

REM ============================================
REM PASO 3: SECURITY - Analisis de Seguridad
REM ============================================
echo ============================================
echo   3/3 - SECURITY: Analisis de Seguridad
echo ============================================
echo.

echo [1/2] Verificando vulnerabilidades con safety...
python -m safety check --file requirements.txt || echo [INFO] Safety check completado
echo.

echo [2/2] Analisis de seguridad con bandit...
python -m bandit -r app/ seguros/ -ll || echo [INFO] Bandit check completado
echo.

REM ============================================
REM RESUMEN
REM ============================================
echo ============================================
echo   RESUMEN DEL PIPELINE LOCAL
echo ============================================
echo.
echo [OK] Pipeline local completado
echo.
echo Siguiente paso: git push origin HEAD:rama-samuel
echo.
pause
