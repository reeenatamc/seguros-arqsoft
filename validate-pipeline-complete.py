#!/usr/bin/env python
"""
Validación COMPLETA del pipeline CI/CD localmente.
Simula EXACTAMENTE el mismo proceso que GitHub Actions.
"""
import os
import subprocess
import sys


def run_command(cmd, env=None, description=""):
    """Ejecuta un comando y retorna True si pasa."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")

    result = subprocess.run(
        cmd, env=env or os.environ.copy(), capture_output=True, text=True, shell=True if isinstance(cmd, str) else False
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode != 0:
        print(f"\n[X] FALLO: {description}")
        return False
    else:
        print(f"\n[OK] PASO: {description}")
        return True


def main():
    """Ejecuta el pipeline completo."""
    print("\n" + "=" * 60)
    print("  VALIDACIÓN COMPLETA DEL PIPELINE CI/CD")
    print("=" * 60)

    # Configurar env vars como en GitHub Actions
    env = os.environ.copy()
    env["SECRET_KEY"] = "test-very-long-secret-key-with-many-unique-characters-1234567890-abcdefghijklmnopqrstuvwxyz"
    env["DEBUG"] = "False"
    env["ALLOWED_HOSTS"] = "localhost,127.0.0.1"

    results = []

    # 1. LINT: flake8
    results.append(
        run_command(
            [sys.executable, "-m", "flake8", ".", "--count", "--statistics"],
            description="1/6: Flake8 - Verificación de calidad",
        )
    )

    # 2. LINT: black
    results.append(
        run_command(
            [sys.executable, "-m", "black", "--check", ".", "--exclude=app/management/commands/poblar_datos_prueba.py"],
            description="2/6: Black - Verificación de formato",
        )
    )

    # 3. LINT: isort
    results.append(
        run_command(
            [sys.executable, "-m", "isort", "--check-only", "."], description="3/6: isort - Verificación de imports"
        )
    )

    # 4. TEST: check migraciones
    results.append(
        run_command(
            [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run", "--no-input"],
            env=env,
            description="4/6: Django - Verificar migraciones",
        )
    )

    # 5. TEST: check deploy
    results.append(
        run_command(
            [sys.executable, "manage.py", "check", "--deploy"],
            env=env,
            description="5/6: Django - Check de deploy (seguridad)",
        )
    )

    # 6. TEST: pytest (con coverage como en CI/CD)
    results.append(
        run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "app/tests.py",
                "--verbose",
                "--tb=short",
                "--cov=app",
                "--cov=seguros",
                "--cov-report=term-missing",
                "--cov-report=html",
                "--cov-report=xml",
            ],
            env=env,
            description="6/6: Pytest - Tests unitarios (con coverage)",
        )
    )

    # Resumen
    print("\n" + "=" * 60)
    print("  RESUMEN DEL PIPELINE")
    print("=" * 60)

    checks = ["flake8", "black", "isort", "migraciones", "check deploy", "pytest"]

    for i, (check, result) in enumerate(zip(checks, results)):
        status = "[OK] PASO" if result else "[X] FALLO"
        print(f"{i+1}. {check:20s} {status}")

    print("=" * 60)

    if all(results):
        print("\n[SUCCESS] TODOS LOS CHECKS PASARON! Pipeline listo para push.")
        return 0
    else:
        print("\n[ERROR] ALGUNOS CHECKS FALLARON. Revisa los errores arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
