# Políticas de Correo Electrónico - Sistema de Seguros UTPL

Este documento describe las políticas de correo electrónico que el sistema procesa automáticamente para la gestión de siniestros.

---

## Resumen del Flujo

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   CUSTODIO      │     │     BROKER       │     │    ASEGURADORA      │
│   (Reporte)     │────▶│   (Respuesta)    │────▶│  (Recibo Indemn.)   │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                        │                         │
        ▼                        ▼                         ▼
   registrado            notificado_broker          enviado_aseguradora
                               │                           │
                               ▼                           ▼
                        documentacion_lista         recibo_recibido
```

---

## 1. Reporte de Siniestro (Custodio → Sistema)

### Política de Asunto
```
[SINIESTRO] Descripción del problema
```

### Campos Requeridos en el Cuerpo
```
--- INICIO REPORTE ---
RESPONSABLE: Nombre Apellido
FECHA_REPORTE: DD/MM/YYYY
PROBLEMA: Descripción del problema
CAUSA: Causa del daño
--- DATOS DEL EQUIPO ---
PERIFERICO: Tipo de equipo
MARCA: Marca
MODELO: Modelo
SERIE: Número de serie
ACTIVO: Código de activo (opcional)
--- FIN REPORTE ---
```

### Ejemplo Completo
```
Asunto: [SINIESTRO] Laptop no enciende

--- INICIO REPORTE ---
RESPONSABLE: María García López
FECHA_REPORTE: 15/01/2026
PROBLEMA: El equipo no enciende, pantalla dañada
CAUSA: Caída accidental desde el escritorio
--- DATOS DEL EQUIPO ---
PERIFERICO: Laptop
MARCA: Dell
MODELO: XPS 15
SERIE: ABC123XYZ
ACTIVO: 02002001648
--- FIN REPORTE ---
```

### Imágenes Adjuntas
- El custodio puede adjuntar **imágenes** (JPG, PNG, etc.) del daño
- Las imágenes se guardan automáticamente como adjuntos del siniestro
- Tipos soportados: `image/jpeg`, `image/png`, `image/gif`, `image/webp`

### Acción del Sistema
- Crea un nuevo `Siniestro` en estado `registrado`
- Vincula al `BienAsegurado` por serie o código de activo
- **Guarda las imágenes adjuntas** como `AdjuntoSiniestro` tipo "foto_dano"
- Genera checklist de documentos según el tipo de ramo

---

## 2. Respuesta del Broker (Broker → Sistema)

### Política de Asunto
```
RESPUESTA SINIESTRO SIN-XXXX-XXXX
```

### Ejemplo
```
RESPUESTA SINIESTRO SIN-2026-0001
```

### Requisitos
- El número de siniestro debe existir en el sistema
- El siniestro debe estar en estado `notificado_broker`

### Acción del Sistema
- Cambia el estado del siniestro a `documentacion_lista`
- Registra la fecha de respuesta del broker
- El siniestro queda listo para enviar documentos a la aseguradora

---

## 3. Recibo de Indemnización (Aseguradora → Sistema)

### Política de Asunto
```
RECIBO DE INDEMNIZACIÓN
```
o
```
RECIBO DE INDEMNIZACION
```

### Requisitos
- Debe incluir un **PDF adjunto** con el recibo de indemnización
- El PDF debe contener información para identificar el bien:

### Campos en el PDF
| Campo | Formato | Descripción |
|-------|---------|-------------|
| Código Activo | `AC: XXXXXXXXXXX` | Código del activo fijo |
| Serie | `SE: XXXXXXXX` | Número de serie del equipo |
| Reclamo | `RECLAMO N° XXXXXX` | Número de reclamo (6 dígitos) |
| Valor | `LA SUMA DE: X,XXX.XX` | Monto de indemnización |

### Ejemplo de Contenido PDF
```
RECIBO DE INDEMNIZACIÓN Y SUBROGACIÓN DE DERECHOS
                                                    651147
RECLAMO N°                    Ramo / Póliza:       1 - 429965 - 0
ASEGURADO:                    UNIVERSIDAD TECNICA PARTICULAR DE LOJA

DETALLE DE PÉRDIDA
DAÑO TOTAL DE LAPTOP DELL V330 SE: MP1NVD1C AC: 02002001648

RECIBÍ DE CHUBB SEGUROS ECUADOR S.A. LA SUMA DE: 598.84
```

### Acción del Sistema
- Extrae el código de activo (`AC:`) y número de serie (`SE:`) del PDF
- Busca el `BienAsegurado` correspondiente
- Vincula el recibo al `Siniestro` en estado `enviado_aseguradora`
- Cambia el estado a `recibo_recibido`
- Guarda el PDF como archivo adjunto

### Si No Puede Vincular Automáticamente
- Guarda el email en `SiniestroEmail` con estado `pendiente`
- Queda disponible para revisión manual en el admin

---

## Configuración IMAP

### Variables de Entorno (.env)
```env
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_EMAIL=correo@ejemplo.com
IMAP_PASSWORD=contraseña_de_aplicación
```

### Para Gmail
1. Habilitar "Acceso de aplicaciones menos seguras" o
2. Usar una **Contraseña de aplicación**:
   - Ir a Google Account → Seguridad → Contraseñas de aplicaciones
   - Generar nueva contraseña para "Correo"

---

## Tareas Programadas (Celery Beat)

| Tarea | Frecuencia | Descripción |
|-------|------------|-------------|
| `revisar_inbox_broker` | Cada 5 min | Busca respuestas del broker |
| `revisar_inbox_recibos` | Cada 5 min | Busca recibos de indemnización |
| `verificar_plazos_liquidacion` | Cada hora | Verifica plazos de 72h |

### Iniciar Celery
```bash
# Terminal 1: Worker
celery -A seguros worker -l info

# Terminal 2: Beat (programador)
celery -A seguros beat -l info
```

---

## Estados del Siniestro

| Estado | Descripción | Siguiente Acción |
|--------|-------------|------------------|
| `registrado` | Siniestro creado | Notificar al broker |
| `notificado_broker` | Esperando respuesta | (Automático) Email del broker |
| `documentacion_lista` | Broker respondió | Enviar a aseguradora |
| `enviado_aseguradora` | Documentos enviados | (Automático) Recibo |
| `recibo_recibido` | Recibo llegó | Firmar recibo |
| `recibo_firmado` | Usuario firmó | Enviar a liquidación |
| `pendiente_liquidacion` | Contador 72h activo | Registrar liquidación |
| `vencido` | 72h vencidas | Registrar liquidación |
| `liquidado` | Pago registrado | Cerrar siniestro |
| `cerrado` | Proceso completado | - |
| `rechazado` | Sin pago | - |

---

## Solución de Problemas

### El sistema no detecta emails
1. Verificar configuración IMAP en `.env`
2. Verificar que Celery worker y beat estén corriendo
3. Ejecutar manualmente:
   ```bash
   python manage.py shell -c "from app.tasks import revisar_inbox_broker; print(revisar_inbox_broker())"
   ```

### Email detectado pero no vinculado
1. Verificar que el asunto coincida exactamente con la política
2. Para recibos: verificar que el PDF contenga `AC:` o `SE:`
3. Verificar que el siniestro esté en el estado correcto

### Ver emails pendientes de revisión
```bash
python manage.py shell -c "from app.models import SiniestroEmail; print(SiniestroEmail.objects.filter(estado_procesamiento='pendiente').count())"
```

---

## Contacto

Para modificar las políticas de email, editar los archivos:
- `app/services/email/broker_reader.py` - Respuestas del broker
- `app/services/email/recibos_reader.py` - Recibos de indemnización
- `app/services/email/reader.py` - Reportes de siniestros
