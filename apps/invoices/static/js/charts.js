// Store chart instances globally
let temporalChartInstance = null;
let categoryChartInstance = null;
let expandedChartInstance = null;

// Store data globally for expansion
let globalChartData = null;

// Fetch chart data and render charts
async function loadCharts() {
    try {
        let url = '/dashboard/api/chart-data/';
        let params = [];
        if (typeof SELECTED_MONTH !== 'undefined' && SELECTED_MONTH) {
            params.push('month=' + SELECTED_MONTH);
        }
        if (typeof SELECTED_CARD !== 'undefined' && SELECTED_CARD) {
            params.push('card=' + SELECTED_CARD);
        }
        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        const response = await fetch(url);
        const data = await response.json();
        
        // Salva dados globalmente para uso no modal
        globalChartData = data;

        // Always render temporal chart (shows global data)
        if (data.temporal) {
            const temporalCanvas = document.getElementById('temporalChart');
            if (temporalCanvas) {
                renderTemporalChart(data.temporal);
            }
        }

        // Render category chart (always)
        const categoryCanvas = document.getElementById('categoryChart');
        if (categoryCanvas) {
            renderCategoryChart(data.category);
        }
    } catch (error) {
        console.error('Erro ao carregar dados dos gráficos:', error);
    }
}

// Update charts with new data (for AJAX card filter)
function updateChartsFromData(data) {
    globalChartData = data;
    
    // Always update temporal chart (shows global data regardless of month filter)
    if (data.temporal) {
        const temporalCanvas = document.getElementById('temporalChart');
        if (temporalCanvas) {
            if (temporalChartInstance) {
                temporalChartInstance.destroy();
            }
            renderTemporalChart(data.temporal);
        }
    }

    // Always update category chart
    const categoryCanvas = document.getElementById('categoryChart');
    if (categoryCanvas) {
        if (categoryChartInstance) {
            categoryChartInstance.destroy();
        }
        renderCategoryChart(data.category);
    }
}

function getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
        textColor: isDark ? '#a0aec0' : '#64748b',
        gridColor: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.06)',
        tooltipBg: isDark ? '#1a1f3a' : '#ffffff',
        tooltipTitle: isDark ? '#ffffff' : '#1a202c',
        tooltipBody: isDark ? '#a0aec0' : '#64748b',
        tooltipBorder: isDark ? 'rgba(102, 126, 234, 0.3)' : 'rgba(0, 0, 0, 0.1)',
    };
}

const categoryColors = [
    '#667eea', '#f5576c', '#43e97b', '#fa709a', '#fee140',
    '#30cfd0', '#a8edea', '#764ba2', '#4facfe', '#f093fb'
];

function renderTemporalChart(data) {
    const ctx = document.getElementById('temporalChart');
    if (!ctx) return;
    const colors = getChartColors();
    temporalChartInstance = createTemporalChart(ctx, data, colors, false);
}

function createTemporalChart(ctx, data, colors, isExpanded) {
    const chartDatasets = data.datasets ? data.datasets.map((ds, index) => ({
        label: ds.label,
        data: ds.data,
        borderColor: ds.color || '#667eea',
        backgroundColor: (ctx) => {
            const chart = ctx.chart;
            const { ctx: chartCtx, chartArea } = chart;
            if (!chartArea) return 'rgba(102, 126, 234, 0.1)';
            const gradient = chartCtx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
            gradient.addColorStop(0, 'rgba(102, 126, 234, 0)');
            gradient.addColorStop(1, 'rgba(102, 126, 234, 0.2)');
            return gradient;
        },
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: isExpanded ? 8 : 6,
        pointBackgroundColor: ds.color || '#667eea',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        datalabels: {
            display: isExpanded && (index === data.datasets.length - 1),
            align: 'top',
            anchor: 'end',
            offset: 10,
            color: '#ffffff',
            backgroundColor: 'rgba(102, 126, 234, 0.8)',
            borderRadius: 6,
            padding: { top: 4, bottom: 4, left: 8, right: 8 },
            font: { weight: 'bold', size: 11, family: 'Inter' },
            textAlign: 'center',
            formatter: (value, context) => {
                const dataIndex = context.dataIndex;
                let sum = 0;
                context.chart.data.datasets.forEach(dataset => {
                    sum += dataset.data[dataIndex] || 0;
                });
                return `R$ ${sum.toLocaleString('pt-BR')}`;
            }
        }
    })) : [{
        label: 'Gastos (R$)',
        data: data.data,
        borderColor: '#667eea',
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: isExpanded ? 8 : 6,
        datalabels: {
            display: isExpanded,
            align: 'top',
            anchor: 'end',
            offset: 10,
            color: '#ffffff',
            backgroundColor: 'rgba(102, 126, 234, 0.8)',
            borderRadius: 6,
            padding: { top: 4, bottom: 4, left: 8, right: 8 },
            font: { weight: 'bold', size: 12 },
            formatter: (val) => `R$ ${val.toLocaleString('pt-BR')}`
        }
    }];

    return new Chart(ctx, {
        type: 'line',
        data: { labels: data.labels, datasets: chartDatasets },
        options: {
            layout: {
                padding: isExpanded ? {
                    left: 50,
                    right: 50,
                    top: 50,
                    bottom: 10
                } : {
                    left: 0,
                    right: 0,
                    top: 0,
                    bottom: 0
                }
            },
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'center',
                    labels: { 
                        color: colors.textColor, 
                        font: { family: 'Inter', size: 12, weight: 600 }, 
                        usePointStyle: true, 
                        padding: isExpanded ? 5 : 10 
                    }
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipTitle,
                    bodyColor: colors.tooltipBody,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    padding: 14,
                    callbacks: {
                        afterTitle: function(context) {
                            let sum = 0;
                            context[0].chart.data.datasets.forEach(dataset => {
                                if (dataset.data[context[0].dataIndex]) {
                                    sum += dataset.data[context[0].dataIndex];
                                }
                            });
                            return '⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\nTotal: R$ ' + sum.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        },
                        label: function (context) {
                            return ' ' + context.dataset.label + ': R$ ' + context.parsed.y.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        }
                    }
                },
                datalabels: {
                    display: isExpanded
                }
            },
            scales: {
                y: {
                    stacked: true,
                    display: !isExpanded,
                    beginAtZero: true,
                    grace: isExpanded ? '15%' : '0%',
                    grid: { color: colors.gridColor, drawBorder: false },
                    ticks: { 
                        color: colors.textColor,
                        callback: function (value) {
                            return 'R$ ' + value.toLocaleString('pt-BR');
                        }
                    }
                },
                x: {
                    stacked: true,
                    grid: { display: false, drawBorder: false },
                    ticks: { 
                        color: colors.textColor,
                        font: { family: 'Inter', size: isExpanded ? 12 : 11, weight: 600 },
                        minRotation: isExpanded ? 0 : 30,
                        maxRotation: isExpanded ? 0 : 30
                    }
                }
            }
        },
        plugins: isExpanded ? [ChartDataLabels] : []
    });
}

function renderCategoryChart(data) {
    const ctx = document.getElementById('categoryChart');
    const colors = getChartColors();
    categoryChartInstance = createCategoryChart(ctx, data, colors, false);
}

function createCategoryChart(ctx, data, colors, isExpanded) {
    let labels, values;

    if (!isExpanded) {
        const combined = data.labels.map((label, i) => ({ label: label, value: data.data[i] }));
        combined.sort((a, b) => b.value - a.value);
        const top5 = combined.slice(0, 5);
        const others = combined.slice(5);
        labels = top5.map(item => item.label);
        values = top5.map(item => item.value);
        if (others.length > 0) {
            labels.push('Outros');
            values.push(others.reduce((sum, item) => sum + item.value, 0));
        }
    } else {
        labels = data.labels;
        values = data.data;
    }

    const total = values.reduce((a, b) => a + b, 0);

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Gastos (R$)',
                data: values,
                backgroundColor: labels.map((_, i) => categoryColors[i % categoryColors.length]),
                borderRadius: 8,
                maxBarThickness: isExpanded ? 100 : 80
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                datalabels: {
                    anchor: 'end',
                    align: 'top',
                    color: isExpanded ? '#ffffff' : colors.textColor,
                    backgroundColor: isExpanded ? 'rgba(102, 126, 234, 0.8)' : 'transparent',
                    borderRadius: isExpanded ? 6 : 0,
                    padding: isExpanded ? { top: 4, bottom: 4, left: 8, right: 8 } : 0,
                    font: { weight: 'bold', size: isExpanded ? 13 : 12 },
                    formatter: (val) => 'R$ ' + val.toLocaleString('pt-BR')
                }
            },
            scales: {
                x: { 
                    grid: { display: false, drawBorder: false },
                    ticks: { 
                        color: colors.textColor, 
                        font: { family: 'Inter', size: isExpanded ? 12 : 11, weight: 600 } 
                    } 
                },
                y: { 
                    display: false, 
                    grace: isExpanded ? '20%' : '15%' 
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

// Modal Functions
function openChartModal(type) {
    const modal = document.getElementById('chartModal');
    const canvas = document.getElementById('expandedChartCanvas');
    const title = document.getElementById('modalTitle');
    const colors = getChartColors();

    if (!globalChartData) return;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent scroll

    if (expandedChartInstance) expandedChartInstance.destroy();

    if (type === 'temporal') {
        title.innerHTML = '<i class="fi fi-br-chart-line-up"></i> Evolução Detalhada de Gastos';
        expandedChartInstance = createTemporalChart(canvas, globalChartData.temporal, colors, true);
    } else {
        title.innerHTML = '<i class="fi fi-br-chart-pie"></i> Distribuição Completa por Categoria';
        expandedChartInstance = createCategoryChart(canvas, globalChartData.category, colors, true);
    }
}

function closeChartModal() {
    const modal = document.getElementById('chartModal');
    modal.classList.add('closing');
    
    // Aguarda o tempo da animação (300ms) definida no CSS
    setTimeout(() => {
        modal.style.display = 'none';
        modal.classList.remove('closing');
        document.body.style.overflow = 'auto';
        if (expandedChartInstance) {
            expandedChartInstance.destroy();
            expandedChartInstance = null;
        }
    }, 300);
}

document.addEventListener('DOMContentLoaded', loadCharts);
