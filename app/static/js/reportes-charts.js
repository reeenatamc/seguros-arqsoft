/**
 * Reportes Charts - Chart.js visualizations
 * Seguros UTPL
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('reportes-charts-data');
    if (!container) return;

    // Obtener datos desde data attributes
    const getData = (key) => {
        const value = container.dataset[key];
        return value ? JSON.parse(value) : [];
    };

    // Configuración global
    Chart.defaults.font.family = 'Plus Jakarta Sans, system-ui, sans-serif';

    // Inicializar gráficos
    initPolizasChart();
    initFacturasChart();
    initSiniestrosChart();

    /**
     * Gráfico de pólizas por estado
     */
    function initPolizasChart() {
        const canvas = document.getElementById('polizasChart');
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
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { 
                            padding: 20, 
                            usePointStyle: true, 
                            pointStyle: 'circle' 
                        }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de facturas por estado
     */
    function initFacturasChart() {
        const canvas = document.getElementById('facturasChart');
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
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { 
                            padding: 20, 
                            usePointStyle: true, 
                            pointStyle: 'circle' 
                        }
                    }
                }
            }
        });
    }

    /**
     * Gráfico de tendencia de siniestros
     */
    function initSiniestrosChart() {
        const canvas = document.getElementById('siniestrosChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: getData('siniestrosLabels'),
                datasets: [{
                    label: 'Siniestros',
                    data: getData('siniestrosData'),
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: '#EF4444'
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
                        grid: { color: 'rgba(0,0,0,0.05)' } 
                    },
                    x: { 
                        grid: { display: false } 
                    }
                }
            }
        });
    }
});

