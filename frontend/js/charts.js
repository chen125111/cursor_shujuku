/**
 * 数据可视化图表模块
 * 使用 Chart.js 创建交互式图表
 */

class GasCharts {
    constructor() {
        this.charts = {};
        this.colors = {
            blue: 'rgba(61, 158, 255, 0.8)',
            cyan: 'rgba(0, 212, 170, 0.8)',
            orange: 'rgba(255, 153, 64, 0.8)',
            red: 'rgba(255, 85, 85, 0.8)',
            purple: 'rgba(183, 148, 246, 0.8)',
            green: 'rgba(72, 187, 120, 0.8)',
            yellow: 'rgba(250, 176, 5, 0.8)'
        };
        
        this.chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#e8eef5',
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(22, 29, 39, 0.9)',
                    titleColor: '#e8eef5',
                    bodyColor: '#8899a8',
                    borderColor: '#253041',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(37, 48, 65, 0.5)'
                    },
                    ticks: {
                        color: '#8899a8'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(37, 48, 65, 0.5)'
                    },
                    ticks: {
                        color: '#8899a8'
                    }
                }
            }
        };
    }
    
    /**
     * 初始化所有图表
     */
    init() {
        this.initTemperatureDistribution();
        this.initPressureDistribution();
        this.initTemperaturePressureScatter();
        this.initCompositionPie();
        this.initStatsCards();
        
        // 监听窗口大小变化，重新调整图表
        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => {
                if (chart) chart.resize();
            });
        });
    }
    
    /**
     * 初始化温度分布直方图
     */
    initTemperatureDistribution() {
        const ctx = document.getElementById('temperatureChart');
        if (!ctx) return;
        
        // 销毁现有图表
        if (this.charts.temperature) {
            this.charts.temperature.destroy();
        }
        
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
                    borderRadius: 4
                }]
            },
            options: {
                ...this.chartOptions,
                plugins: {
                    ...this.chartOptions.plugins,
                    title: {
                        display: true,
                        text: '温度分布',
                        color: '#e8eef5',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                }
            }
        });
        
        this.loadTemperatureData();
    }
    
    /**
     * 加载温度分布数据
     */
    async loadTemperatureData() {
        try {
            const response = await fetch('/api/charts/temperature');
            if (!response.ok) throw new Error('获取温度数据失败');
            
            const data = await response.json();
            
            if (this.charts.temperature) {
                this.charts.temperature.data.labels = data.labels || [];
                this.charts.temperature.data.datasets[0].data = data.data || [];
                this.charts.temperature.update();
            }
        } catch (error) {
            console.error('加载温度数据失败:', error);
            this.showChartError('temperatureChart', '无法加载温度分布数据');
        }
    }
    
    /**
     * 初始化压力分布直方图
     */
    initPressureDistribution() {
        const ctx = document.getElementById('pressureChart');
        if (!ctx) return;
        
        if (this.charts.pressure) {
            this.charts.pressure.destroy();
        }
        
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
                    borderRadius: 4
                }]
            },
            options: {
                ...this.chartOptions,
                plugins: {
                    ...this.chartOptions.plugins,
                    title: {
                        display: true,
                        text: '压力分布',
                        color: '#e8eef5',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                }
            }
        });
        
        this.loadPressureData();
    }
    
    /**
     * 加载压力分布数据
     */
    async loadPressureData() {
        try {
            const response = await fetch('/api/charts/pressure');
            if (!response.ok) throw new Error('获取压力数据失败');
            
            const data = await response.json();
            
            if (this.charts.pressure) {
                this.charts.pressure.data.labels = data.labels || [];
                this.charts.pressure.data.datasets[0].data = data.data || [];
                this.charts.pressure.update();
            }
        } catch (error) {
            console.error('加载压力数据失败:', error);
            this.showChartError('pressureChart', '无法加载压力分布数据');
        }
    }
    
    /**
     * 初始化温度-压力散点图
     */
    initTemperaturePressureScatter() {
        const ctx = document.getElementById('scatterChart');
        if (!ctx) return;
        
        if (this.charts.scatter) {
            this.charts.scatter.destroy();
        }
        
        this.charts.scatter = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '温度-压力关系',
                    data: [],
                    backgroundColor: this.colors.orange,
                    borderColor: 'rgba(255, 153, 64, 1)',
                    borderWidth: 1,
                    pointRadius: 5,
                    pointHoverRadius: 8
                }]
            },
            options: {
                ...this.chartOptions,
                plugins: {
                    ...this.chartOptions.plugins,
                    title: {
                        display: true,
                        text: '温度-压力分布',
                        color: '#e8eef5',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    x: {
                        ...this.chartOptions.scales.x,
                        title: {
                            display: true,
                            text: '温度 (K)',
                            color: '#8899a8'
                        }
                    },
                    y: {
                        ...this.chartOptions.scales.y,
                        title: {
                            display: true,
                            text: '压力 (MPa)',
                            color: '#8899a8'
                        }
                    }
                }
            }
        });
        
        this.loadScatterData();
    }
    
    /**
     * 加载散点图数据
     */
    async loadScatterData() {
        try {
            const response = await fetch('/api/charts/scatter');
            if (!response.ok) throw new Error('获取散点图数据失败');
            
            const data = await response.json();
            
            if (this.charts.scatter) {
                this.charts.scatter.data.datasets[0].data = data.data || [];
                this.charts.scatter.update();
            }
        } catch (error) {
            console.error('加载散点图数据失败:', error);
            this.showChartError('scatterChart', '无法加载温度-压力分布数据');
        }
    }
    
    /**
     * 初始化组分饼图
     */
    initCompositionPie() {
        const ctx = document.getElementById('compositionChart');
        if (!ctx) return;
        
        if (this.charts.composition) {
            this.charts.composition.destroy();
        }
        
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
            type: 'pie',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: compositionColors,
                    borderColor: 'rgba(22, 29, 39, 0.8)',
                    borderWidth: 2
                }]
            },
            options: {
                ...this.chartOptions,
                plugins: {
                    ...this.chartOptions.plugins,
                    title: {
                        display: true,
                        text: '平均组分比例',
                        color: '#e8eef5',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                }
            }
        });
        
        this.loadCompositionData();
    }
    
    /**
     * 加载组分数据
     */
    async loadCompositionData() {
        try {
            const response = await fetch('/api/charts/composition');
            if (!response.ok) throw new Error('获取组分数据失败');
            
            const data = await response.json();
            
            if (this.charts.composition) {
                this.charts.composition.data.labels = data.labels || [];
                this.charts.composition.data.datasets[0].data = data.data || [];
                this.charts.composition.update();
            }
        } catch (error) {
            console.error('加载组分数据失败:', error);
            this.showChartError('compositionChart', '无法加载组分比例数据');
        }
    }
    
    /**
     * 初始化统计卡片
     */
    initStatsCards() {
        this.updateStatsCards();
        
        // 每30秒更新一次统计
        setInterval(() => this.updateStatsCards(), 30000);
    }
    
    /**
     * 更新统计卡片
     */
    async updateStatsCards() {
        try {
            const response = await fetch('/api/statistics');
            if (!response.ok) throw new Error('获取统计信息失败');
            
            const stats = await response.json();
            
            // 更新卡片数据
            this.updateCardValue('totalRecords', stats.total_records || 0);
            this.updateCardValue('avgTemperature', stats.avg_temperature ? `${stats.avg_temperature.toFixed(2)} K` : 'N/A');
            this.updateCardValue('avgPressure', stats.avg_pressure ? `${stats.avg_pressure.toFixed(2)} MPa` : 'N/A');
            this.updateCardValue('tempRange', stats.min_temperature && stats.max_temperature ? 
                `${stats.min_temperature.toFixed(1)}-${stats.max_temperature.toFixed(1)} K` : 'N/A');
            
        } catch (error) {
            console.error('更新统计卡片失败:', error);
        }
    }
    
    /**
     * 更新卡片数值
     */
    updateCardValue(cardId, value) {
        const card = document.getElementById(cardId);
        if (card) {
            // 添加动画效果
            card.style.opacity = '0.5';
            card.style.transform = 'scale(0.95)';
            
            setTimeout(() => {
                card.textContent = value;
                card.style.opacity = '1';
                card.style.transform = 'scale(1)';
            }, 150);
        }
    }
    
    /**
     * 显示图表错误
     */
    showChartError(canvasId, message) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const parent = canvas.parentElement;
        if (!parent) return;
        
        // 创建错误消息元素
        const errorDiv = document.createElement('div');
        errorDiv.className = 'chart-error';
        errorDiv.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #8899a8;">
                <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                <h3 style="color: #e8eef5; margin-bottom: 8px;">图表加载失败</h3>
                <p>${message}</p>
                <button class="btn btn-sm btn-secondary" onclick="gasCharts.retryChart('${canvasId}')" 
                        style="margin-top: 16px;">
                    重试
                </button>
            </div>
        `;
        
        // 隐藏canvas，显示错误消息
        canvas.style.display = 'none';
        parent.appendChild(errorDiv);
    }
    
    /**
     * 重试加载图表
     */
    retryChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const parent = canvas.parentElement;
        const errorDiv = parent.querySelector('.chart-error');
        
        if (errorDiv) {
            parent.removeChild(errorDiv);
        }
        
        canvas.style.display = 'block';
        
        // 重新加载对应的图表数据
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
        }
    }
    
    /**
     * 创建自定义图表（供外部调用）
     */
    createCustomChart(canvasId, type, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        // 销毁现有图表
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const mergedOptions = {
            ...this.chartOptions,
            ...options
        };
        
        this.charts[canvasId] = new Chart(ctx, {
            type: type,
            data: data,
            options: mergedOptions
        });
        
        return this.charts[canvasId];
    }
    
    /**
     * 更新图表数据
     */
    updateChart(chartId, newData) {
        const chart = this.charts[chartId];
        if (!chart) return;
        
        if (newData.labels) {
            chart.data.labels = newData.labels;
        }
        
        if (newData.datasets) {
            chart.data.datasets = newData.datasets;
        }
        
        chart.update();
    }
    
    /**
     * 导出图表为图片
     */
    exportChart(chartId, fileName = 'chart.png') {
        const chart = this.charts[chartId];
        if (!chart) return;
        
        const link = document.createElement('a');
        link.download = fileName;
        link.href = chart.toBase64Image();
        link.click();
    }
    
    /**
     * 销毁所有图表
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }
}

// 创建全局实例
const gasCharts = new GasCharts();

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', () => {
    // 延迟初始化，确保DOM完全加载
    setTimeout(() => {
        if (typeof Chart !== 'undefined') {
            gasCharts.init();
        } else {
            console.error('Chart.js 未加载');
        }
    }, 100);
});

// 导出供其他模块使用
window.GasCharts = GasCharts;
window.gasCharts = gasCharts;