/**
 * Dashboard Charts V2 - Gráficos dinámicos con filtros
 * Sistema de Seguros UTPL
 * 
 * Este archivo maneja los gráficos del dashboard con soporte para
 * datos dinámicos basados en los filtros aplicados.
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('dashboard-data');
    if (!container) return;

    // Obtener datos desde data attributes
    const getData = (key) => {
        const value = container.dataset[key];
        if (!value) return null;
        try {
            return JSON.parse(value);
        } catch (e) {
            console.warn(`Error parsing data for key: ${key}`, e);
            return null;
        }
    };

    // Configuración global de Chart.js
    Chart.defaults.font.family = 'Plus Jakarta Sans, Inter, system-ui, sans-serif';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.95)';
    Chart.defaults.plugins.tooltip.titleFont = { weight: '600', size: 13 };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
    Chart.defaults.plugins.tooltip.padding = 14;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.tooltip.boxPadding = 6;

    // Paleta de colores profesional
    const colors = {
        brand: {
            primary: '#3B82F6',
            light: 'rgba(59, 130, 246, 0.15)',
            dark: '#2563EB'
        },
        success: {
            primary: '#10B981',
            light: 'rgba(16, 185, 129, 0.15)',
            dark: '#059669'
        },
        danger: {
            primary: '#EF4444',
            light: 'rgba(239, 68, 68, 0.15)',
            dark: '#DC2626'
        },
        warning: {
            primary: '#F59E0B',
            light: 'rgba(245, 158, 11, 0.15)',
            dark: '#D97706'
        },
        purple: {
            primary: '#8B5CF6',
            light: 'rgba(139, 92, 246, 0.15)',
            dark: '#7C3AED'
        },
        cyan: {
            primary: '#06B6D4',
            light: 'rgba(6, 182, 212, 0.15)',
            dark: '#0891B2'
        },
        slate: {
            primary: '#64748B',
            light: 'rgba(100, 116, 139, 0.15)',
            dark: '#475569'
        }
    };

    // Colores para gráficos de pastel/dona
    const chartColors = [
        '#3B82F6', '#10B981', '#F59E0B', '#EF4444', 
        '#8B5CF6', '#06B6D4', '#EC4899', '#14B8A6'
    ];

    // Obtener datos del chart
    const chartData = getData('chart');
    const yearComparison = getData('yearComparison');

    // Inicializar todos los gráficos
    if (chartData) {
        initInvoicingTrendChart(chartData.invoicing_trend);
        initClaimsTrendChart(chartData.claims_trend);
        initPolicyStateChart(chartData.by_policy_state);
        initByInsurerChart(chartData.by_insurer);
        initClaimTypeChart(chartData.by_claim_type);
    }

    /**
     * Gráfico de tendencia de facturación
     */
    function initInvoicingTrendChart(data) {
        const canvas = document.getElementById('invoicingTrendChart');
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        
        // Crear gradientes
        const invoicedGradient = ctx.createLinearGradient(0, 0, 0, 300);
        invoicedGradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
        invoicedGradient.addColorStop(1, 'rgba(16, 185, 129, 0)');

        const paidGradient = ctx.createLinearGradient(0, 0, 0, 300);
        paidGradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
        paidGradient.addColorStop(1, 'rgba(59, 130, 246, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Facturado',
                        data: data.amounts,
                        borderColor: colors.success.primary,
                        backgroundColor: invoicedGradient,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 4,
                        pointBackgroundColor: colors.success.primary,
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Cobrado',
                        data: data.paid,
                        borderColor: colors.brand.primary,
                        backgroundColor: paidGradient,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 4,
                        pointBackgroundColor: colors.brand.primary,
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
                                return `${context.dataset.label}: $${context.parsed.y.toLocaleString('es-EC')}`;
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
     * Gráfico de tendencia de siniestros
     */
    function initClaimsTrendChart(data) {
        const canvas = document.getElementById('claimsTrendChart');
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        
        // Crear gradiente
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Cantidad',
                        data: data.counts,
                        backgroundColor: colors.danger.primary,
                        borderRadius: 6,
                        borderSkipped: false,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Monto Estimado',
                        data: data.amounts,
                        type: 'line',
                        borderColor: colors.warning.primary,
                        backgroundColor: 'transparent',
                        borderWidth: 3,
                        pointRadius: 4,
                        pointBackgroundColor: colors.warning.primary,
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
                        labels: { usePointStyle: true, padding: 20, font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.datasetIndex === 1) {
                                    return `Monto: $${context.parsed.y.toLocaleString('es-EC')}`;
                                }
                                return `Cantidad: ${context.parsed.y}`;
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
                        title: { display: true, text: 'Cantidad', font: { size: 11 } }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        grid: { display: false },
                        title: { display: true, text: 'Monto ($)', font: { size: 11 } },
                        ticks: {
                            callback: function(value) {
                                if (value >= 1000) {
                                    return '$' + (value / 1000).toFixed(0) + 'K';
                                }
                                return '$' + value;
                            }
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de pólizas por estado (Doughnut)
     */
    function initPolicyStateChart(data) {
        const canvas = document.getElementById('policyStateChart');
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.counts,
                    backgroundColor: data.colors || chartColors,
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
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${context.label}: ${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de pólizas por compañía (Bar horizontal)
     */
    function initByInsurerChart(data) {
        const canvas = document.getElementById('byInsurerChart');
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Pólizas',
                    data: data.counts,
                    backgroundColor: chartColors.map(c => c + 'CC'),
                    borderRadius: 6,
                    borderSkipped: false,
                    barThickness: 18
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const total = data.totals[context.dataIndex];
                                return `Suma asegurada: $${total.toLocaleString('es-EC')}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: {
                            font: { size: 11 },
                            callback: function(value, index) {
                                const label = this.getLabelForValue(value);
                                return label.length > 15 ? label.substring(0, 15) + '...' : label;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de siniestros por tipo (Polar Area - Radial)
     */
    function initClaimTypeChart(data) {
        const canvas = document.getElementById('claimTypeChart');
        if (!canvas || !data) return;

        const ctx = canvas.getContext('2d');
        
        // Genera colores dinámicamente para todos los tipos de siniestros
        function generateColors(count) {
            const colors = [];
            const baseHues = [0, 25, 45, 60, 85, 140, 165, 185, 210, 260, 290, 320];
            for (let i = 0; i < count; i++) {
                // Usa los hues base cíclicamente y varía la saturación/luminosidad
                const hue = baseHues[i % baseHues.length];
                const saturation = 70 + (Math.floor(i / baseHues.length) * 5);
                const lightness = 50 + (Math.floor(i / baseHues.length) * 5);
                colors.push(`hsla(${hue}, ${saturation}%, ${lightness}%, 0.75)`);
            }
            return colors;
        }
        
        const polarColors = generateColors(data.labels.length);
        
        new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.counts,
                    backgroundColor: polarColors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 12,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: { size: 10 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${context.label}: ${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    r: {
                        grid: { 
                            color: 'rgba(0,0,0,0.06)',
                            circular: true
                        },
                        ticks: { 
                            display: false 
                        },
                        pointLabels: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    /**
     * Función para actualizar gráficos dinámicamente via AJAX
     */
    window.updateDashboardCharts = async function(filters = {}) {
        const chartsUrl = container.dataset.apiChartsUrl;
        if (!chartsUrl) return;

        try {
            const params = new URLSearchParams(filters);
            const response = await fetch(`${chartsUrl}?${params.toString()}`);
            const data = await response.json();

            // Destruir gráficos existentes y recrear con nuevos datos
            Chart.helpers.each(Chart.instances, function(instance) {
                instance.destroy();
            });

            initInvoicingTrendChart(data.invoicing_trend);
            initClaimsTrendChart(data.claims_trend);
            initPolicyStateChart(data.by_policy_state);
            initByInsurerChart(data.by_insurer);
            initClaimTypeChart(data.by_claim_type);

        } catch (error) {
            console.error('Error updating charts:', error);
        }
    };

    /**
     * Formateador de moneda
     */
    function formatCurrency(value) {
        return new Intl.NumberFormat('es-EC', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
    }
});

