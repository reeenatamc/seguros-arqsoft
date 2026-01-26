/**
 * Cálculos en Vivo para Formularios
 * Sistema de Seguros - Arquitectura de Software
 */

document.addEventListener('DOMContentLoaded', function() {
    initFacturaCalculations();
    initDetalleRamoCalculations();
    initPagoCalculations();
    initNotaCreditoCalculations();
});

// =============================================================================
// CONFIGURACIÓN (puede venir del servidor)
// =============================================================================

const CONFIG = {
    PORCENTAJE_SUPERINTENDENCIA: 0.035,  // 3.5%
    PORCENTAJE_SEGURO_CAMPESINO: 0.005,  // 0.5%
    PORCENTAJE_IVA: 0.15,                // 15%
    DIAS_DESCUENTO_PRONTO_PAGO: 20,
    PORCENTAJE_DESCUENTO_PRONTO_PAGO: 0.10, // 10%
    
    // Tabla de derechos de emisión
    TABLA_EMISION: [
        { limite: 250, tasa: 0.50 },
        { limite: 500, tasa: 1.00 },
        { limite: 1000, tasa: 3.00 },
        { limite: 2000, tasa: 5.00 },
        { limite: 4000, tasa: 7.00 },
        { limite: Infinity, tasa: 9.00 },
    ]
};

// =============================================================================
// UTILIDADES
// =============================================================================

function getNumericValue(input) {
    if (!input) return 0;
    const value = parseFloat(input.value);
    return isNaN(value) ? 0 : value;
}

function setNumericValue(input, value, decimals = 2) {
    if (!input) return;
    input.value = value.toFixed(decimals);
    // Disparar evento para que otros listeners se enteren
    input.dispatchEvent(new Event('change', { bubbles: true }));
}

function formatCurrencyDisplay(value) {
    return new Intl.NumberFormat('es-EC', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

function calcularDerechosEmision(prima) {
    for (const rango of CONFIG.TABLA_EMISION) {
        if (prima <= rango.limite) {
            return rango.tasa;
        }
    }
    return CONFIG.TABLA_EMISION[CONFIG.TABLA_EMISION.length - 1].tasa;
}

// =============================================================================
// CÁLCULOS DE FACTURA
// =============================================================================

function initFacturaCalculations() {
    const form = document.querySelector('[data-calc-form="factura"]');
    if (!form) return;

    const fields = {
        subtotal: form.querySelector('[data-calc="subtotal"]'),
        iva: form.querySelector('[data-calc="iva"]'),
        contribSuper: form.querySelector('[data-calc="contribucion_superintendencia"]'),
        contribCampesino: form.querySelector('[data-calc="contribucion_seguro_campesino"]'),
        retenciones: form.querySelector('[data-calc="retenciones"]'),
        descuento: form.querySelector('[data-calc="descuento_pronto_pago"]'),
        montoTotal: form.querySelector('[data-calc="monto_total"]'),
    };

    // Verificar que existan los campos necesarios
    if (!fields.subtotal || !fields.montoTotal) return;

    function calcularFactura() {
        const subtotal = getNumericValue(fields.subtotal);
        
        // Calcular contribuciones
        const contribSuper = subtotal * CONFIG.PORCENTAJE_SUPERINTENDENCIA;
        const contribCampesino = subtotal * CONFIG.PORCENTAJE_SEGURO_CAMPESINO;
        
        // Calcular IVA sobre el subtotal
        const iva = subtotal * CONFIG.PORCENTAJE_IVA;
        
        // Obtener valores de retenciones y descuento (pueden ser editados manualmente)
        const retenciones = getNumericValue(fields.retenciones);
        const descuento = getNumericValue(fields.descuento);
        
        // Calcular total
        const montoTotal = subtotal + iva + contribSuper + contribCampesino - retenciones - descuento;
        
        // Actualizar campos calculados (solo si no están siendo editados)
        if (fields.contribSuper && !fields.contribSuper.matches(':focus')) {
            setNumericValue(fields.contribSuper, contribSuper);
        }
        if (fields.contribCampesino && !fields.contribCampesino.matches(':focus')) {
            setNumericValue(fields.contribCampesino, contribCampesino);
        }
        if (fields.iva && !fields.iva.matches(':focus')) {
            setNumericValue(fields.iva, iva);
        }
        if (fields.montoTotal) {
            setNumericValue(fields.montoTotal, montoTotal);
        }
        
        // Actualizar display si existe
        updateCalculationDisplay(form, {
            subtotal,
            contribSuper,
            contribCampesino,
            iva,
            retenciones,
            descuento,
            montoTotal
        });
    }

    // Escuchar cambios en campos de entrada
    ['subtotal', 'retenciones', 'descuento'].forEach(fieldName => {
        if (fields[fieldName]) {
            fields[fieldName].addEventListener('input', debounce(calcularFactura, 150));
        }
    });
    
    // Calcular al cargar
    calcularFactura();
}

// =============================================================================
// CÁLCULOS DE DETALLE RAMO (DESGLOSE)
// =============================================================================

function initDetalleRamoCalculations() {
    // Para formsets dinámicos
    const container = document.querySelector('[data-calc-formset="detalle-ramo"]');
    if (container) {
        initDetalleRamoFormset(container);
    }
    
    // Para formularios individuales
    document.querySelectorAll('[data-calc-form="detalle-ramo"]').forEach(form => {
        setupDetalleRamoForm(form);
    });
}

function initDetalleRamoFormset(container) {
    // Observer para detectar nuevos formularios añadidos dinámicamente
    const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1 && node.matches('[data-calc-row="detalle-ramo"]')) {
                    setupDetalleRamoRow(node);
                }
            });
        });
    });
    
    observer.observe(container, { childList: true, subtree: true });
    
    // Configurar filas existentes
    container.querySelectorAll('[data-calc-row="detalle-ramo"]').forEach(row => {
        setupDetalleRamoRow(row);
    });
    
    // Calcular totales globales
    setupFormsetTotals(container);
}

function setupDetalleRamoForm(form) {
    const fields = {
        sumaAsegurada: form.querySelector('[data-calc="suma_asegurada"]'),
        tasa: form.querySelector('[data-calc="tasa"]'),
        totalPrima: form.querySelector('[data-calc="total_prima"]'),
        contribSuper: form.querySelector('[data-calc="contribucion_superintendencia"]'),
        seguroCampesino: form.querySelector('[data-calc="seguro_campesino"]'),
        emision: form.querySelector('[data-calc="emision"]'),
        baseImponible: form.querySelector('[data-calc="base_imponible"]'),
        iva: form.querySelector('[data-calc="iva"]'),
        totalFacturado: form.querySelector('[data-calc="total_facturado"]'),
    };

    function calcular() {
        const sumaAsegurada = getNumericValue(fields.sumaAsegurada);
        const tasa = getNumericValue(fields.tasa);
        
        // Prima = Suma Asegurada × Tasa / 100
        const totalPrima = sumaAsegurada * (tasa / 100);
        
        // Contribuciones
        const contribSuper = totalPrima * CONFIG.PORCENTAJE_SUPERINTENDENCIA;
        const seguroCampesino = totalPrima * CONFIG.PORCENTAJE_SEGURO_CAMPESINO;
        
        // Derechos de emisión
        const emision = calcularDerechosEmision(totalPrima);
        
        // Base imponible
        const baseImponible = totalPrima + contribSuper + seguroCampesino + emision;
        
        // IVA
        const iva = baseImponible * CONFIG.PORCENTAJE_IVA;
        
        // Total facturado
        const totalFacturado = baseImponible + iva;
        
        // Actualizar campos
        if (fields.totalPrima) setNumericValue(fields.totalPrima, totalPrima);
        if (fields.contribSuper) setNumericValue(fields.contribSuper, contribSuper);
        if (fields.seguroCampesino) setNumericValue(fields.seguroCampesino, seguroCampesino);
        if (fields.emision) setNumericValue(fields.emision, emision);
        if (fields.baseImponible) setNumericValue(fields.baseImponible, baseImponible);
        if (fields.iva) setNumericValue(fields.iva, iva);
        if (fields.totalFacturado) setNumericValue(fields.totalFacturado, totalFacturado);
    }

    ['sumaAsegurada', 'tasa'].forEach(fieldName => {
        if (fields[fieldName]) {
            fields[fieldName].addEventListener('input', debounce(calcular, 150));
        }
    });
    
    calcular();
}

function setupDetalleRamoRow(row) {
    const fields = {
        sumaAsegurada: row.querySelector('[data-calc="suma_asegurada"]'),
        totalPrima: row.querySelector('[data-calc="total_prima"]'),
        emision: row.querySelector('[data-calc="emision"]'),
    };

    function calcular() {
        const totalPrima = getNumericValue(fields.totalPrima);
        
        // Calcular derechos de emisión automáticamente
        if (fields.emision && !fields.emision.matches(':focus')) {
            const emision = calcularDerechosEmision(totalPrima);
            setNumericValue(fields.emision, emision);
        }
        
        // Actualizar totales del formset
        const container = row.closest('[data-calc-formset="detalle-ramo"]');
        if (container) {
            updateFormsetTotals(container);
        }
    }

    if (fields.totalPrima) {
        fields.totalPrima.addEventListener('input', debounce(calcular, 150));
    }
    
    calcular();
}

function setupFormsetTotals(container) {
    updateFormsetTotals(container);
}

function updateFormsetTotals(container) {
    let totalSuma = 0;
    let totalPrima = 0;
    let totalEmision = 0;
    
    container.querySelectorAll('[data-calc-row="detalle-ramo"]').forEach(row => {
        // Ignorar filas marcadas para eliminar
        const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (deleteCheckbox && deleteCheckbox.checked) return;
        
        totalSuma += getNumericValue(row.querySelector('[data-calc="suma_asegurada"]'));
        totalPrima += getNumericValue(row.querySelector('[data-calc="total_prima"]'));
        totalEmision += getNumericValue(row.querySelector('[data-calc="emision"]'));
    });
    
    // Actualizar displays de totales
    const totalsDisplay = container.querySelector('[data-calc-totals]');
    if (totalsDisplay) {
        const totalSumaEl = totalsDisplay.querySelector('[data-total="suma_asegurada"]');
        const totalPrimaEl = totalsDisplay.querySelector('[data-total="total_prima"]');
        const totalEmisionEl = totalsDisplay.querySelector('[data-total="emision"]');
        
        if (totalSumaEl) totalSumaEl.textContent = formatCurrencyDisplay(totalSuma);
        if (totalPrimaEl) totalPrimaEl.textContent = formatCurrencyDisplay(totalPrima);
        if (totalEmisionEl) totalEmisionEl.textContent = formatCurrencyDisplay(totalEmision);
    }
}

// =============================================================================
// CÁLCULOS DE PAGO
// =============================================================================

function initPagoCalculations() {
    const form = document.querySelector('[data-calc-form="pago"]');
    if (!form) return;

    const fields = {
        factura: form.querySelector('[data-calc="factura"]'),
        monto: form.querySelector('[data-calc="monto"]'),
    };
    
    const saldoDisplay = form.querySelector('[data-calc-display="saldo_pendiente"]');
    
    // Obtener mapa de saldos desde data attribute
    let saldosMap = {};
    if (fields.factura && fields.factura.dataset.saldos) {
        try {
            saldosMap = JSON.parse(fields.factura.dataset.saldos);
        } catch (e) {
            console.warn('Error parsing saldos:', e);
        }
    }

    function getSaldoFactura() {
        if (!fields.factura) return 0;
        const facturaId = fields.factura.value;
        return parseFloat(saldosMap[facturaId] || 0);
    }

    function actualizarInfo() {
        const saldo = getSaldoFactura();
        
        if (saldoDisplay) {
            if (saldo > 0) {
                saldoDisplay.textContent = formatCurrencyDisplay(saldo);
                saldoDisplay.classList.remove('text-slate-400');
                saldoDisplay.classList.add('text-emerald-600');
            } else {
                saldoDisplay.textContent = '-- seleccione factura --';
                saldoDisplay.classList.remove('text-emerald-600');
                saldoDisplay.classList.add('text-slate-400');
            }
        }
        
        // Establecer el máximo en el campo de monto
        if (fields.monto && saldo > 0) {
            fields.monto.max = saldo;
            fields.monto.placeholder = `Máx: $${saldo.toFixed(2)}`;
        }
        
        validarMonto();
    }

    function validarMonto() {
        if (!fields.monto || !fields.factura) return;
        
        const saldo = getSaldoFactura();
        const monto = getNumericValue(fields.monto);
        
        if (saldo > 0 && monto > saldo) {
            fields.monto.setCustomValidity(`El monto no puede exceder el saldo pendiente ($${saldo.toFixed(2)})`);
            fields.monto.classList.add('border-red-500', 'bg-red-50');
            fields.monto.classList.remove('border-slate-300');
        } else {
            fields.monto.setCustomValidity('');
            fields.monto.classList.remove('border-red-500', 'bg-red-50');
            fields.monto.classList.add('border-slate-300');
        }
    }

    if (fields.factura) {
        fields.factura.addEventListener('change', actualizarInfo);
    }
    
    if (fields.monto) {
        fields.monto.addEventListener('input', debounce(validarMonto, 150));
    }
    
    actualizarInfo();
}

// =============================================================================
// CÁLCULOS DE NOTA DE CRÉDITO
// =============================================================================

function initNotaCreditoCalculations() {
    const form = document.querySelector('[data-calc-form="nota_credito"]');
    if (!form) return;

    const fields = {
        factura: form.querySelector('[data-calc="factura"]'),
        monto: form.querySelector('[data-calc="monto"]'),
    };
    
    const saldoDisplay = form.querySelector('[data-calc-display="saldo_factura"]');
    
    // Obtener mapa de saldos desde data attribute
    let saldosMap = {};
    if (fields.factura && fields.factura.dataset.saldos) {
        try {
            saldosMap = JSON.parse(fields.factura.dataset.saldos);
        } catch (e) {
            console.warn('Error parsing saldos:', e);
        }
    }

    function getSaldoFactura() {
        if (!fields.factura) return 0;
        const facturaId = fields.factura.value;
        return parseFloat(saldosMap[facturaId] || 0);
    }

    function actualizarInfo() {
        const saldo = getSaldoFactura();
        
        if (saldoDisplay) {
            if (saldo > 0) {
                saldoDisplay.textContent = formatCurrencyDisplay(saldo);
            } else {
                saldoDisplay.textContent = '--';
            }
        }
        
        if (fields.monto && saldo > 0) {
            fields.monto.max = saldo;
        }
        
        validarMonto();
    }

    function validarMonto() {
        if (!fields.monto || !fields.factura) return;
        
        const saldo = getSaldoFactura();
        const monto = getNumericValue(fields.monto);
        
        if (saldo > 0 && monto > saldo) {
            fields.monto.setCustomValidity(`El monto no puede exceder $${saldo.toFixed(2)}`);
            fields.monto.classList.add('border-red-500', 'bg-red-50');
        } else {
            fields.monto.setCustomValidity('');
            fields.monto.classList.remove('border-red-500', 'bg-red-50');
        }
    }

    if (fields.factura) {
        fields.factura.addEventListener('change', actualizarInfo);
    }
    
    if (fields.monto) {
        fields.monto.addEventListener('input', debounce(validarMonto, 150));
    }
    
    actualizarInfo();
}

// =============================================================================
// DISPLAY DE CÁLCULOS
// =============================================================================

function updateCalculationDisplay(form, values) {
    const display = form.querySelector('[data-calc-summary]');
    if (!display) return;
    
    Object.entries(values).forEach(([key, value]) => {
        const el = display.querySelector(`[data-summary="${key}"]`);
        if (el) {
            el.textContent = formatCurrencyDisplay(value);
        }
    });
}

// =============================================================================
// UTILIDAD DEBOUNCE (si no existe)
// =============================================================================

if (typeof debounce === 'undefined') {
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    window.debounce = debounce;
}

// Exportar para uso externo
window.CalculationsModule = {
    CONFIG,
    calcularDerechosEmision,
    getNumericValue,
    setNumericValue,
    formatCurrencyDisplay,
    initFacturaCalculations,
    initDetalleRamoCalculations,
    initPagoCalculations,
    initNotaCreditoCalculations,
};
