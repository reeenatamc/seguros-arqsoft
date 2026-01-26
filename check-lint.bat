@echo off
REM Script rapido para verificar flake8 localmente (igual que el pipeline)
echo.
echo Ejecutando flake8 (mismo que pipeline CI/CD)...
echo.
python -m flake8 . --count --statistics --show-source
echo.
if %errorlevel% equ 0 (
    echo [OK] Sin errores! Puedes hacer push con confianza.
) else (
    echo [ERROR] Hay errores. Revisa la salida anterior.
)
echo.
pause
