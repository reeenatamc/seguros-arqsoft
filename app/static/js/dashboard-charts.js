/**
 * Dashboard Charts - Chart.js visualizations
 * Seguros UTPL
 * 
 * Este archivo maneja todos los gráficos del dashboard principal,
 * incluyendo comparativas anuales, tendencias y distribuciones.
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('dashboard-charts-data');
    if (!container) return;

    // Obtener datos desde data attributes
    const getData = (key) => {
        const value = container.dataset[key];
        if (!value) return [];
        try {
            return JSON.parse(value);
        } catch (e) {
            console.warn(`Error parsing data for key: ${key}`, e);
            return [];
        }
    };

    // Configuración global de Chart.js
    Chart.defaults.font.family = 'Plus Jakarta Sans, system-ui, sans-serif';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
    Chart.defaults.plugins.tooltip.titleFont = { weight: '600' };
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;

    // Colores del tema
    const colors = {
        brand: '#3B82F6',
        brandLight: 'rgba(59, 130, 246, 0.2)',
        success: '#10B981',
        successLight: 'rgba(16, 185, 129, 0.2)',
        danger: '#EF4444',
        dangerLight: 'rgba(239, 68, 68, 0.2)',
        warning: '#F59E0B',
        warningLight: 'rgba(245, 158, 11, 0.2)',
        purple: '#8B5CF6',
        cyan: '#06B6D4',
        slate: '#94A3B8',
        slateLight: 'rgba(148, 163, 184, 0.3)'
    };

    // Inicializar todos los gráficos
    initYearComparisonChart();
    initComparativoChart();
    initPolizasEstadoChart();
    initFacturasEstadoChart();
    initSiniestrosTipoChart();
    initFacturacionChart();
    initSiniestrosMesChart();
    initPolizasTipoChart();

    /**
     * Gráfico de comparación año a año
     * Muestra la facturación del año actual vs el anterior
     */
    function initYearComparisonChart() {
        const canvas = document.getElementById('yearComparisonChart');
        if (!canvas) return;

        const yearData = getData('yearComparison');
        if (!yearData || !yearData.labels) return;

        // Actualizar etiquetas de años en el DOM
        const currentYearLabel = document.getElementById('current-year-label');
        const previousYearLabel = document.getElementById('previous-year-label');
        if (currentYearLabel) currentYearLabel.textContent = yearData.current_year;
        if (previousYearLabel) previousYearLabel.textContent = yearData.previous_year;

        const ctx = canvas.getContext('2d');
        
        // Crear gradientes para las áreas
        const currentGradient = ctx.createLinearGradient(0, 0, 0, 250);
        currentGradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
        currentGradient.addColorStop(1, 'rgba(59, 130, 246, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: yearData.labels,
                datasets: [
                    {
                        label: String(yearData.current_year),
                        data: yearData.invoices.current,
                        borderColor: colors.brand,
                        backgroundColor: currentGradient,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 5,
                        pointBackgroundColor: colors.brand,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 8
                    },
                    {
                        label: String(yearData.previous_year),
                        data: yearData.invoices.previous,
                        borderColor: colors.slate,
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointBackgroundColor: colors.slate,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: $${context.parsed.y.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
                        ticks: {
                            padding: 10,
                            callback: function(value) {
                                if (value >= 1000000) {
                                    return '$' + (value / 1000000).toFixed(1) + 'M';
                                } else if (value >= 1000) {
                                    return '$' + (value / 1000).toFixed(0) + 'K';
                                }
                                return '$' + value;
                            }
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { padding: 10 }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de actividad comparativa del sistema
     */
    function initComparativoChart() {
        const canvas = document.getElementById('comparativoChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: getData('comparativoLabels'),
                datasets: [
                    {
                        label: 'Pólizas',
                        data: getData('comparativoPolizas'),
                        borderColor: colors.brand,
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 5,
                        pointBackgroundColor: colors.brand,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 7
                    },
                    {
                        label: 'Facturas',
                        data: getData('comparativoFacturas'),
                        borderColor: colors.success,
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 5,
                        pointBackgroundColor: colors.success,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 7
                    },
                    {
                        label: 'Siniestros',
                        data: getData('comparativoSiniestros'),
                        borderColor: colors.danger,
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 5,
                        pointBackgroundColor: colors.danger,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 7
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
                        ticks: { padding: 10 }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { padding: 10 }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de pólizas por estado
     */
    function initPolizasEstadoChart() {
        const canvas = document.getElementById('polizasEstadoChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: getData('polizasLabels'),
                datasets: [{
                    data: getData('polizasData'),
                    backgroundColor: getData('polizasColors'),
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de facturas por estado
     */
    function initFacturasEstadoChart() {
        const canvas = document.getElementById('facturasEstadoChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: getData('facturasLabels'),
                datasets: [{
                    data: getData('facturasData'),
                    backgroundColor: getData('facturasColors'),
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de siniestros por tipo
     */
    function initSiniestrosTipoChart() {
        const canvas = document.getElementById('siniestrosTipoChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: getData('siniestrosTipoLabels'),
                datasets: [{
                    data: getData('siniestrosTipoData'),
                    backgroundColor: [
                        'rgba(239, 68, 68, 0.7)',
                        'rgba(249, 115, 22, 0.7)',
                        'rgba(245, 158, 11, 0.7)',
                        'rgba(234, 179, 8, 0.7)',
                        'rgba(132, 204, 22, 0.7)',
                        'rgba(34, 197, 94, 0.7)',
                        'rgba(20, 184, 166, 0.7)',
                        'rgba(6, 182, 212, 0.7)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: { size: 10 }
                        }
                    }
                },
                scales: {
                    r: {
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de facturación mensual
     */
    function initFacturacionChart() {
        const canvas = document.getElementById('facturacionChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: getData('facturacionLabels'),
                datasets: [
                    {
                        label: 'Monto Facturado',
                        data: getData('facturacionMonto'),
                        backgroundColor: 'rgba(16, 185, 129, 0.8)',
                        borderRadius: 6,
                        borderSkipped: false,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cantidad',
                        data: getData('facturacionCantidad'),
                        type: 'line',
                        borderColor: colors.brand,
                        backgroundColor: 'transparent',
                        borderWidth: 3,
                        pointRadius: 4,
                        pointBackgroundColor: colors.brand,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: { usePointStyle: true, padding: 20 }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.datasetIndex === 0) {
                                    return 'Facturado: $' + context.parsed.y.toLocaleString();
                                }
                                return 'Cantidad: ' + context.parsed.y;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)' },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        grid: { display: false }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de siniestros por mes
     */
    function initSiniestrosMesChart() {
        const canvas = document.getElementById('siniestrosMesChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Crear gradiente
        const gradient = ctx.createLinearGradient(0, 0, 0, 250);
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.4)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: getData('siniestrosMesLabels'),
                datasets: [{
                    label: 'Siniestros',
                    data: getData('siniestrosMesData'),
                    borderColor: colors.danger,
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 5,
                    pointBackgroundColor: colors.danger,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de pólizas por tipo
     */
    function initPolizasTipoChart() {
        const canvas = document.getElementById('polizasTipoChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const labels = getData('polizasTipoLabels') || [];
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Cantidad',
                    data: getData('polizasTipoData'),
                    backgroundColor: getData('polizasTipoColors'),
                    borderRadius: 6,
                    borderSkipped: false,
                    barThickness: 20,
                    maxBarThickness: 25,
                    barPercentage: 0.6,
                    categoryPercentage: 0.7
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)' },
                        ticks: {
                            stepSize: 1
                        }
                    },
                    y: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 12 },
                            padding: 8
                        }
                    }
                },
                layout: {
                    padding: {
                        top: 10,
                        bottom: 10,
                        left: 5,
                        right: 15
                    }
                }
            }
        });
    }
});

