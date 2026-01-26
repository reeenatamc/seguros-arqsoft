@echo off
REM Script para auto-formatear codigo con black e isort
echo.
echo Formateando codigo automaticamente...
echo.
echo [1/2] Formateando con black...
python -m black .
echo.
echo [2/2] Ordenando imports con isort...
python -m isort .
echo.
echo [OK] Codigo formateado!
echo.
echo Ahora ejecuta: check-lint.bat para verificar
echo.
pause
