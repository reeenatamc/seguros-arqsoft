@echo off
REM ============================================
REM Script de inicio rápido con Docker
REM ============================================

echo.
echo ============================================
echo   Sistema de Seguros UTPL - Docker
echo ============================================
echo.

REM Verificar que Docker está corriendo
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no esta corriendo
    echo Por favor inicia Docker Desktop
    pause
    exit /b 1
)

echo [OK] Docker esta corriendo
echo.

echo Selecciona el modo de deployment:
echo.
echo [1] PRODUCCION - Con PostgreSQL, Redis, Celery (Recomendado)
echo [2] DESARROLLO - Con live reload
echo.
set /p choice="Opcion (1 o 2): "

if "%choice%"=="1" (
    echo.
    echo ============================================
    echo   Iniciando en modo PRODUCCION
    echo ============================================
    echo.
    
    REM Verificar si existe .env.production
    if not exist .env.production (
        echo [WARNING] No existe .env.production
        echo Creando desde plantilla...
        copy .env.docker .env.production
        echo.
        echo [IMPORTANTE] Edita .env.production y configura:
        echo   - SECRET_KEY
        echo   - POSTGRES_PASSWORD
        echo   - ALLOWED_HOSTS
        echo.
        echo Presiona cualquier tecla para continuar o Ctrl+C para cancelar
        pause >nul
    )
    
    echo [INFO] Construyendo imagenes...
    docker compose build
    
    echo.
    echo [INFO] Levantando servicios...
    docker compose --env-file .env.production up -d
    
) else if "%choice%"=="2" (
    echo.
    echo ============================================
    echo   Iniciando en modo DESARROLLO
    echo ============================================
    echo.
    
    docker compose -f docker-compose.dev.yml up -d
    
) else (
    echo [ERROR] Opcion invalida
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Servicios iniciados correctamente
echo ============================================
echo.
echo Verificando estado...
docker compose ps
echo.
echo URLs disponibles:
echo   - Aplicacion: http://localhost:8000
echo   - Admin:      http://localhost:8000/admin
echo.
echo Comandos utiles:
echo   - Ver logs:     docker compose logs -f web
echo   - Detener:      docker compose down
echo   - Reiniciar:    docker compose restart web
echo.
pause
