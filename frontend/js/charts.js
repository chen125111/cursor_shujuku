/**
 * 数据可视化图表模块
 * 使用 Chart.js 创建交互式图表
 */

class GasCharts {
    constructor() {
        this.charts = {};
        this.initialized = false;
        this.statsTimer = null;
        this.resizeHandler = null;
        this.selectedScatterIndex = null;
        this.chartKeyMap = {
            temperatureChart: 'temperature',
            pressureChart: 'pressure',
            scatterChart: 'scatter',
            compositionChart: 'composition'
        };
        this.colors = {
            blue: 'rgba(61, 158, 255, 0.78)',
            cyan: 'rgba(0, 212, 170, 0.78)',
            orange: 'rgba(255, 153, 64, 0.78)',
            red: 'rgba(255, 99, 132, 0.85)',
            purple: 'rgba(183, 148, 246, 0.8)',
            green: 'rgba(72, 187, 120, 0.8)',
            yellow: 'rgba(250, 176, 5, 0.82)'
        };
        this.chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                intersect: false
            },
            animation: {
                duration: 420,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#e8eef5',
                        usePointStyle: true,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#cbd5e1',
                    borderColor: '#334155',
                    borderWidth: 1,
                    cornerRadius: 10,
                    displayColors: true,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(71, 85, 105, 0.36)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { color: 'rgba(71, 85, 105, 0.36)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        };
        this.registerPlugins();
    }

    registerPlugins() {
        if (typeof Chart === 'undefined' || GasCharts.pluginsRegistered) return;
        Chart.register({
            id: 'hoverCrosshair',
            afterDatasetsDraw(chart) {
                if (!chart?.tooltip || !chart.tooltip._active || !chart.tooltip._active.length) return;
                const active = chart.tooltip._active[0];
                const x = active?.element?.x;
                if (typeof x !== 'number' || !chart.chartArea) return;
                const ctx = chart.ctx;
                const top = chart.chartArea.top;
                const bottom = chart.chartArea.bottom;
                ctx.save();
                ctx.beginPath();
                ctx.moveTo(x, top);
                ctx.lineTo(x, bottom);
                ctx.lineWidth = 1;
                ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)';
                ctx.stroke();
                ctx.restore();
            }
        });
        GasCharts.pluginsRegistered = true;
    }

    debounce(fn, wait = 120) {
        let timer = null;
        return (...args) => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => fn(...args), wait);
        };
    }

    notify(message, type = 'info') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        }
    }

    getChartKey(chartId) {
        return this.chartKeyMap[chartId] || chartId;
    }

    getChartInstance(chartId) {
        return this.charts[this.getChartKey(chartId)] || null;
    }

    ensureChartFrame(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        const parent = canvas.parentElement;
        if (!parent) return null;
        if (parent.classList.contains('chart-frame')) return parent;

        const frame = document.createElement('div');
        frame.className = 'chart-frame';
        parent.insertBefore(frame, canvas);
        frame.appendChild(canvas);
        return frame;
    }

    setChartState(canvasId, state = '', message = '') {
        const frame = this.ensureChartFrame(canvasId);
        if (!frame) return;
        const canvas = frame.querySelector('canvas');
        let stateEl = frame.querySelector('.chart-state');
        if (!stateEl) {
            stateEl = document.createElement('div');
            stateEl.className = 'chart-state';
            frame.appendChild(stateEl);
        }

        if (!state) {
            stateEl.classList.remove('active');
            stateEl.innerHTML = '';
            if (canvas) {
                canvas.style.opacity = '1';
                canvas.style.pointerEvents = 'auto';
            }
            return;
        }

        stateEl.className = `chart-state active ${state}`;
        if (state === 'loading') {
            stateEl.innerHTML = `
                <div class="chart-state-spinner"></div>
                <div>${message || '图表加载中...'}</div>
            `;
        } else if (state === 'error') {
            stateEl.innerHTML = `
                <div style="font-size: 22px;">⚠️</div>
                <div>${message || '图表加载失败'}</div>
                <button class="btn btn-sm btn-secondary" onclick="gasCharts.retryChart('${canvasId}')">重试</button>
            `;
        } else if (state === 'empty') {
            stateEl.innerHTML = `
                <div style="font-size: 22px;">📭</div>
                <div>${message || '暂无可视化数据'}</div>
            `;
        }

        if (canvas) {
            canvas.style.opacity = state === 'loading' ? '0.4' : '0.16';
            canvas.style.pointerEvents = state === 'loading' ? 'none' : 'auto';
        }
    }

    async fetchJson(url, errorMessage) {
        const response = await fetch(url);
        let payload = null;
        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }
        if (!response.ok) {
            const msg = payload && (payload.message || payload.detail);
            throw new Error(msg || errorMessage || `请求失败（HTTP ${response.status}）`);
        }
        return payload || {};
    }

    init() {
        if (this.initialized) return;
        this.initialized = true;
        this.initTemperatureDistribution();
        this.initPressureDistribution();
        this.initTemperaturePressureScatter();
        this.initCompositionPie();
        this.initStatsCards();

        this.resizeHandler = this.debounce(() => {
            Object.values(this.charts).forEach(chart => {
                if (chart) chart.resize();
            });
        }, 130);
        window.addEventListener('resize', this.resizeHandler);
    }

    initTemperatureDistribution() {
        this.ensureChartFrame('temperatureChart');
        const ctx = document.getElementById('temperatureChart');
        if (!ctx) return;
        if (this.charts.temperature) this.charts.temperature.destroy();

        this.charts.temperature = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: '记录数量',
                    data: [],
                    backgroundColor: this.colors.blue,
                    borderColor: 'rgba(61, 158, 255, 1)',
                    borderWidth: 1,
                    borderRadius: 5,
                    hoverBackgroundColor: 'rgba(96, 165, 250, 0.9)'
                }]
            },
            options: {
                ...this.chartOptions,
                onHover: (event, elements) => {
                    const target = event && event.native && event.native.target;
                    if (target) target.style.cursor = elements.length ? 'pointer' : 'default';
                },
                plugins: {
                    ...this.chartOptions.plugins,
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ...this.chartOptions.scales.x,
                        grid: { display: false }
                    },
                    y: {
                        ...this.chartOptions.scales.y,
                        beginAtZero: true
                    }
                }
            }
        });
        this.loadTemperatureData();
    }

    async loadTemperatureData() {
        this.setChartState('temperatureChart', 'loading', '温度分布加载中...');
        try {
            const data = await this.fetchJson('/api/charts/temperature', '获取温度数据失败');
            const labels = Array.isArray(data.labels) ? data.labels : [];
            const values = Array.isArray(data.data) ? data.data : [];
            if (!labels.length || !values.length) {
                if (this.charts.temperature) {
                    this.charts.temperature.data.labels = [];
                    this.charts.temperature.data.datasets[0].data = [];
                    this.charts.temperature.update();
                }
                this.setChartState('temperatureChart', 'empty', '暂无温度分布数据');
                return;
            }
            if (this.charts.temperature) {
                this.charts.temperature.data.labels = labels;
                this.charts.temperature.data.datasets[0].data = values;
                this.charts.temperature.update();
            }
            this.setChartState('temperatureChart');
        } catch (error) {
            console.error('加载温度数据失败:', error);
            this.showChartError('temperatureChart', error.message || '无法加载温度分布数据');
        }
    }

    initPressureDistribution() {
        this.ensureChartFrame('pressureChart');
        const ctx = document.getElementById('pressureChart');
        if (!ctx) return;
        if (this.charts.pressure) this.charts.pressure.destroy();

        this.charts.pressure = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: '记录数量',
                    data: [],
                    backgroundColor: this.colors.cyan,
                    borderColor: 'rgba(0, 212, 170, 1)',
                    borderWidth: 1,
                    borderRadius: 5,
                    hoverBackgroundColor: 'rgba(45, 212, 191, 0.92)'
                }]
            },
            options: {
                ...this.chartOptions,
                onHover: (event, elements) => {
                    const target = event && event.native && event.native.target;
                    if (target) target.style.cursor = elements.length ? 'pointer' : 'default';
                },
                plugins: {
                    ...this.chartOptions.plugins,
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ...this.chartOptions.scales.x,
                        grid: { display: false }
                    },
                    y: {
                        ...this.chartOptions.scales.y,
                        beginAtZero: true
                    }
                }
            }
        });
        this.loadPressureData();
    }

    async loadPressureData() {
        this.setChartState('pressureChart', 'loading', '压力分布加载中...');
        try {
            const data = await this.fetchJson('/api/charts/pressure', '获取压力数据失败');
            const labels = Array.isArray(data.labels) ? data.labels : [];
            const values = Array.isArray(data.data) ? data.data : [];
            if (!labels.length || !values.length) {
                if (this.charts.pressure) {
                    this.charts.pressure.data.labels = [];
                    this.charts.pressure.data.datasets[0].data = [];
                    this.charts.pressure.update();
                }
                this.setChartState('pressureChart', 'empty', '暂无压力分布数据');
                return;
            }
            if (this.charts.pressure) {
                this.charts.pressure.data.labels = labels;
                this.charts.pressure.data.datasets[0].data = values;
                this.charts.pressure.update();
            }
            this.setChartState('pressureChart');
        } catch (error) {
            console.error('加载压力数据失败:', error);
            this.showChartError('pressureChart', error.message || '无法加载压力分布数据');
        }
    }

    initTemperaturePressureScatter() {
        this.ensureChartFrame('scatterChart');
        const ctx = document.getElementById('scatterChart');
        if (!ctx) return;
        if (this.charts.scatter) this.charts.scatter.destroy();

        this.charts.scatter = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '温度-压力关系',
                    data: [],
                    backgroundColor: this.colors.orange,
                    borderColor: 'rgba(255, 153, 64, 1)',
                    borderWidth: 1,
                    pointRadius: 4.5,
                    pointHoverRadius: 8,
                    pointHitRadius: 12
                }]
            },
            options: {
                ...this.chartOptions,
                plugins: {
                    ...this.chartOptions.plugins,
                    legend: { display: false },
                    tooltip: {
                        ...this.chartOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const x = context.parsed.x;
                                const y = context.parsed.y;
                                return `温度 ${x.toFixed(2)} K，压力 ${y.toFixed(3)} MPa`;
                            }
                        }
                    }
                },
                onHover: (event, elements) => {
                    const target = event && event.native && event.native.target;
                    if (target) target.style.cursor = elements.length ? 'pointer' : 'default';
                },
                onClick: (_event, elements) => {
                    if (!elements || !elements.length) return;
                    this.highlightScatterPoint(elements[0].index);
                },
                scales: {
                    x: {
                        ...this.chartOptions.scales.x,
                        title: { display: true, text: '温度 (K)', color: '#94a3b8' }
                    },
                    y: {
                        ...this.chartOptions.scales.y,
                        title: { display: true, text: '压力 (MPa)', color: '#94a3b8' }
                    }
                }
            }
        });
        this.loadScatterData();
    }

    highlightScatterPoint(index) {
        const chart = this.charts.scatter;
        if (!chart || !chart.data.datasets.length) return;
        const points = chart.data.datasets[0].data || [];
        if (!points.length) return;

        this.selectedScatterIndex = index;
        const pointColors = points.map((_, i) => (i === index ? this.colors.red : this.colors.orange));
        const pointRadius = points.map((_, i) => (i === index ? 8 : 4.5));
        chart.data.datasets[0].backgroundColor = pointColors;
        chart.data.datasets[0].borderColor = pointColors.map(color => color.replace('0.78', '1'));
        chart.data.datasets[0].pointRadius = pointRadius;
        chart.update();
    }

    async loadScatterData() {
        this.setChartState('scatterChart', 'loading', '散点图加载中...');
        try {
            const data = await this.fetchJson('/api/charts/scatter', '获取散点图数据失败');
            const points = Array.isArray(data.data) ? data.data : [];
            if (!points.length) {
                if (this.charts.scatter) {
                    this.charts.scatter.data.datasets[0].data = [];
                    this.charts.scatter.update();
                }
                this.setChartState('scatterChart', 'empty', '暂无温度-压力散点数据');
                return;
            }
            if (this.charts.scatter) {
                this.selectedScatterIndex = null;
                this.charts.scatter.data.datasets[0].data = points;
                this.charts.scatter.data.datasets[0].backgroundColor = this.colors.orange;
                this.charts.scatter.data.datasets[0].borderColor = 'rgba(255, 153, 64, 1)';
                this.charts.scatter.data.datasets[0].pointRadius = 4.5;
                this.charts.scatter.update();
            }
            this.setChartState('scatterChart');
        } catch (error) {
            console.error('加载散点图数据失败:', error);
            this.showChartError('scatterChart', error.message || '无法加载温度-压力分布数据');
        }
    }

    initCompositionPie() {
        this.ensureChartFrame('compositionChart');
        const ctx = document.getElementById('compositionChart');
        if (!ctx) return;
        if (this.charts.composition) this.charts.composition.destroy();

        const compositionColors = [
            this.colors.blue,
            this.colors.cyan,
            this.colors.orange,
            this.colors.red,
            this.colors.purple,
            this.colors.green,
            this.colors.yellow
        ];
        this.charts.composition = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: compositionColors,
                    borderColor: 'rgba(15, 23, 42, 0.85)',
                    borderWidth: 2,
                    hoverOffset: 6
                }]
            },
            options: {
                ...this.chartOptions,
                cutout: '38%',
                plugins: {
                    ...this.chartOptions.plugins,
                    legend: {
                        ...this.chartOptions.plugins.legend,
                        position: window.innerWidth < 768 ? 'bottom' : 'right'
                    }
                }
            }
        });
        this.loadCompositionData();
    }

    async loadCompositionData() {
        this.setChartState('compositionChart', 'loading', '组分比例加载中...');
        try {
            const data = await this.fetchJson('/api/charts/composition', '获取组分数据失败');
            const labels = Array.isArray(data.labels) ? data.labels : [];
            const values = Array.isArray(data.data) ? data.data : [];
            if (!labels.length || !values.length) {
                if (this.charts.composition) {
                    this.charts.composition.data.labels = [];
                    this.charts.composition.data.datasets[0].data = [];
                    this.charts.composition.update();
                }
                this.setChartState('compositionChart', 'empty', '暂无组分比例数据');
                return;
            }
            if (this.charts.composition) {
                this.charts.composition.data.labels = labels;
                this.charts.composition.data.datasets[0].data = values;
                this.charts.composition.update();
            }
            this.setChartState('compositionChart');
        } catch (error) {
            console.error('加载组分数据失败:', error);
            this.showChartError('compositionChart', error.message || '无法加载组分比例数据');
        }
    }

    initStatsCards() {
        this.updateStatsCards();
        if (this.statsTimer) {
            window.clearInterval(this.statsTimer);
        }
        this.statsTimer = window.setInterval(() => this.updateStatsCards(), 30000);
    }

    async updateStatsCards() {
        try {
            const stats = await this.fetchJson('/api/statistics', '获取统计信息失败');
            this.updateCardValue('totalRecords', stats.total_records || 0);
            this.updateCardValue('avgTemperature', stats.avg_temperature ? `${stats.avg_temperature.toFixed(2)} K` : 'N/A');
            this.updateCardValue('avgPressure', stats.avg_pressure ? `${stats.avg_pressure.toFixed(2)} MPa` : 'N/A');
            this.updateCardValue(
                'tempRange',
                stats.min_temperature && stats.max_temperature
                    ? `${stats.min_temperature.toFixed(1)}-${stats.max_temperature.toFixed(1)} K`
                    : 'N/A'
            );
        } catch (error) {
            console.error('更新统计卡片失败:', error);
        }
    }

    updateCardValue(cardId, value) {
        const card = document.getElementById(cardId);
        if (!card) return;
        card.style.opacity = '0.45';
        card.style.transform = 'scale(0.96)';
        window.setTimeout(() => {
            card.textContent = value;
            card.style.opacity = '1';
            card.style.transform = 'scale(1)';
        }, 140);
    }

    showChartError(canvasId, message) {
        this.setChartState(canvasId, 'error', message || '图表加载失败');
    }

    retryChart(canvasId) {
        switch (canvasId) {
            case 'temperatureChart':
                this.loadTemperatureData();
                break;
            case 'pressureChart':
                this.loadPressureData();
                break;
            case 'scatterChart':
                this.loadScatterData();
                break;
            case 'compositionChart':
                this.loadCompositionData();
                break;
            default:
                break;
        }
    }

    createCustomChart(canvasId, type, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        const key = this.getChartKey(canvasId);
        if (this.charts[key]) this.charts[key].destroy();

        const mergedOptions = { ...this.chartOptions, ...options };
        this.charts[key] = new Chart(ctx, { type, data, options: mergedOptions });
        return this.charts[key];
    }

    updateChart(chartId, newData) {
        const chart = this.getChartInstance(chartId);
        if (!chart) return;
        if (newData.labels) chart.data.labels = newData.labels;
        if (newData.datasets) chart.data.datasets = newData.datasets;
        chart.update();
    }

    refreshAll() {
        this.loadTemperatureData();
        this.loadPressureData();
        this.loadScatterData();
        this.loadCompositionData();
        this.updateStatsCards();
        this.notify('图表与统计已刷新', 'success');
    }

    exportChart(chartId, fileName = 'chart.png') {
        const chart = this.getChartInstance(chartId);
        if (!chart) {
            this.notify('图表尚未准备好，暂无法导出', 'warning');
            return;
        }
        const link = document.createElement('a');
        link.download = fileName;
        link.href = chart.toBase64Image('image/png', 1);
        link.click();
        this.notify('图表导出成功', 'success');
    }

    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
        if (this.statsTimer) {
            window.clearInterval(this.statsTimer);
            this.statsTimer = null;
        }
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }
        this.initialized = false;
    }
}

GasCharts.pluginsRegistered = false;

const gasCharts = new GasCharts();

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        if (typeof Chart !== 'undefined') {
            gasCharts.init();
        } else {
            console.error('Chart.js 未加载');
            if (typeof window.showToast === 'function') {
                window.showToast('Chart.js 未加载，图表功能不可用', 'error');
            }
        }
    }, 100);
});

window.GasCharts = GasCharts;
window.gasCharts = gasCharts;