# 🚀 Pipeline CI/CD Local

Este directorio contiene scripts para ejecutar las mismas verificaciones del pipeline de GitHub Actions **localmente**, antes de hacer push.

## ⚡ Scripts Disponibles

### 1️⃣ `check-lint.bat` - Verificación Rápida
**Uso:** Doble clic o ejecutar desde terminal

```bash
check-lint.bat
```

**Qué hace:**
- ✅ Ejecuta flake8 (misma configuración que GitHub Actions)
- ✅ Muestra exactamente los mismos errores que verías en el pipeline
- ✅ Cuenta total de errores
- ✅ Muestra estadísticas

**Cuándo usarlo:** Antes de cada commit

---

### 2️⃣ `auto-fix.bat` - Auto-Formateo
**Uso:** Doble clic o ejecutar desde terminal

```bash
auto-fix.bat
```

**Qué hace:**
- 🔧 Formatea todo el código con **black**
- 🔧 Ordena imports con **isort**
- ✅ Corrige automáticamente muchos errores de formato

**Cuándo usarlo:** Cuando tengas errores de formato

---

### 3️⃣ `run-pipeline-local.bat` - Pipeline Completo
**Uso:** Ejecutar desde terminal

```bash
run-pipeline-local.bat
```

**Qué hace:**
1. ✅ **Lint**: flake8, black, isort
2. ✅ **Tests**: pytest, migraciones, check
3. ✅ **Security**: safety, bandit

**Cuándo usarlo:** Antes de hacer push de cambios importantes

---

## 📋 Flujo de Trabajo Recomendado

### Opción A: Verificación Rápida (Recomendada)
```bash
# 1. Haces cambios en el código
# 2. Verificas errores
check-lint.bat

# 3. Si hay errores de formato
auto-fix.bat

# 4. Verificas de nuevo
check-lint.bat

# 5. Commit y push
git add -A
git commit -m "tu mensaje"
git push origin HEAD:rama-samuel
```

### Opción B: Verificación Completa
```bash
# 1. Haces cambios en el código
# 2. Ejecutas pipeline completo
run-pipeline-local.bat

# 3. Si todo pasa, haces push
git push origin HEAD:rama-samuel
```

---

## 🎯 Ventajas

- ⚡ **Más rápido**: No esperas a GitHub Actions
- 💰 **Ahorra tiempo**: Detectas errores antes de push
- 🔍 **Mismo resultado**: Usa las mismas herramientas que CI/CD
- ✅ **Confianza**: Sabes que el pipeline pasará

---

## 📊 Estado Actual

Ejecuta `check-lint.bat` para ver el estado actual del código.

**Progreso desde inicio:**
- Inicial: 7,007 errores
- Actual: ~473 errores
- **Reducción: 93%** ✅

---

## 🛠️ Herramientas Instaladas

- ✅ **flake8** 7.0.0 - Linter principal
- ✅ **black** 24.1.1 - Formateador automático
- ✅ **isort** 5.13.2 - Ordenador de imports
- ✅ **pytest** 8.0.0 - Framework de testing
- ✅ **bandit** 1.7.6 - Análisis de seguridad
- ✅ **safety** 3.0.1 - Verificador de vulnerabilidades

---

## 💡 Tips

1. **Ejecuta `check-lint.bat` antes de cada commit**
2. Usa `auto-fix.bat` para corregir formato automáticamente
3. Los errores SIM*, B0*, C9* son sugerencias, no críticos
4. Enfócate en E*, F* y W* (errores de sintaxis y estilo)

---

**Universidad Técnica Particular de Loja**
Sistema de Gestión de Seguros - Pipeline Local
