// Store chart instances globally
let temporalChartInstance = null;
let categoryChartInstance = null;

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

        // Render temporal chart (only if not filtered)
        if (!data.filtered && data.temporal) {
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
    // Update temporal chart if exists and data is available
    if (!data.filtered && data.temporal) {
        const temporalCanvas = document.getElementById('temporalChart');
        if (temporalCanvas) {
            // Destroy existing chart
            if (temporalChartInstance) {
                temporalChartInstance.destroy();
            }
            renderTemporalChart(data.temporal);
        }
    }

    // Always update category chart
    const categoryCanvas = document.getElementById('categoryChart');
    if (categoryCanvas) {
        // Destroy existing chart
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

// Cores vibrantes para categorias
const categoryColors = [
    '#667eea', '#f5576c', '#43e97b', '#fa709a', '#fee140',
    '#30cfd0', '#a8edea', '#764ba2', '#4facfe', '#f093fb'
];

function renderTemporalChart(data) {
    const ctx = document.getElementById('temporalChart');
    if (!ctx) return;

    const colors = getChartColors();

    const chartDatasets = data.datasets ? data.datasets.map(ds => ({
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
        pointRadius: 6,
        pointBackgroundColor: ds.color || '#667eea',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointHoverRadius: 8,
        pointHoverBorderWidth: 3,
        pointHoverBorderColor: '#ffffff'
    })) : [{
        label: 'Gastos (R$)',
        data: data.data,
        borderColor: '#667eea',
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
        pointRadius: 6,
        pointBackgroundColor: '#667eea',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointHoverRadius: 8,
        pointHoverBorderWidth: 3,
        pointHoverBorderColor: '#ffffff'
    }];

    temporalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: chartDatasets
        },
        options: {
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
                        padding: 10
                    }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipTitle,
                    bodyColor: colors.tooltipBody,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    padding: 14,
                    titleFont: { size: 14, weight: 'bold', family: 'Inter' },
                    bodyFont: { size: 13, family: 'Inter' },
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function (context) {
                            return ' ' + context.dataset.label + ': R$ ' + context.parsed.y.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                        }
                    }
                }
            },
            scales: {
                y: {
                    stacked: true,
                    beginAtZero: true,
                    grid: {
                        color: colors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.textColor,
                        font: { family: 'Inter', size: 11 },
                        padding: 10,
                        callback: function (value) {
                            return 'R$ ' + value.toLocaleString('pt-BR');
                        }
                    }
                },
                x: {
                    stacked: true,
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.textColor,
                        font: { family: 'Inter', size: 11 },
                        padding: 10
                    }
                }
            },
            animation: {
                duration: 1200,
                easing: 'easeOutQuart',
                y: {
                    duration: 800,
                    from: (ctx) => {
                        if (ctx.type === 'data' && ctx.mode === 'default') {
                            return 0;
                        }
                    }
                }
            }
        }
    });
}

function renderCategoryChart(data) {
    const ctx = document.getElementById('categoryChart');
    const colors = getChartColors();

    // Pegar as 5 maiores categorias e agregar o restante em "Outros"
    const combined = data.labels.map((label, i) => ({
        label: label,
        value: data.data[i]
    }));
    combined.sort((a, b) => b.value - a.value);

    const top5 = combined.slice(0, 5);
    const others = combined.slice(5);

    const labels = top5.map(item => item.label);
    const values = top5.map(item => item.value);

    // Adicionar categoria "Outros" se houver mais categorias
    if (others.length > 0) {
        const othersSum = others.reduce((sum, item) => sum + item.value, 0);
        labels.push('Outros');
        values.push(othersSum);
    }

    // Calcular total para percentual
    const total = values.reduce((a, b) => a + b, 0);

    categoryChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Gastos por Categoria (R$)',
                data: values,
                backgroundColor: labels.map((_, i) => categoryColors[i % categoryColors.length]),
                borderRadius: 8,
                borderSkipped: false,
                barPercentage: 0.8,
                categoryPercentage: 0.9,
                maxBarThickness: 80
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
                    color: colors.textColor,
                    font: {
                        family: 'Inter',
                        size: 14,
                        weight: 'bold'
                    },
                    formatter: function (value) {
                        return value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    },
                    offset: 4
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipTitle,
                    bodyColor: colors.tooltipBody,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 1,
                    padding: 14,
                    titleFont: { size: 14, weight: 'bold', family: 'Inter' },
                    bodyFont: { size: 13, family: 'Inter' },
                    cornerRadius: 8,
                    callbacks: {
                        label: function (context) {
                            const value = context.parsed.y;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return ' R$ ' + value.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) + ' (' + percentage + '%)';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.textColor,
                        font: { family: 'Inter', size: 12, weight: '500' },
                        padding: 10,
                        maxRotation: 0,
                        minRotation: 0
                    }
                },
                y: {
                    beginAtZero: true,
                    display: false,
                    grace: '30%',
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart',
                delay: (context) => {
                    if (context.type === 'data' && context.mode === 'default') {
                        return context.dataIndex * 100;
                    }
                    return 0;
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

// Load charts when page loads
document.addEventListener('DOMContentLoaded', loadCharts);
