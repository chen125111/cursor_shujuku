/**
 * 气体混合物数据管理系统 - Vue 3 前端应用
 * 前后端分离架构 v2.0
 * 包含：数据可视化、导入导出功能
 */

const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue;

// API 基础地址
const API_BASE = '/api';

// Chart.js 全局配置
Chart.defaults.color = '#8899a8';
Chart.defaults.borderColor = '#253041';

// 创建 Vue 应用
const app = createApp({
    setup() {
        // ==================== 响应式状态 ====================
        const loading = ref(true);
        const importing = ref(false);
        const records = ref([]);
        const showCharts = ref(false);
        const statistics = ref({
            total_records: 0,
            min_temperature: 0,
            max_temperature: 0,
            avg_temperature: 0,
            min_pressure: 0,
            max_pressure: 0,
            avg_pressure: 0
        });
        
        // 图表实例
        let tempChart = null;
        let pressureChart = null;
        let scatterChart = null;
        
        // 分页状态
        const pagination = reactive({
            page: 1,
            perPage: 15,
            total: 0,
            totalPages: 1
        });
        
        // 筛选条件
        const filters = reactive({
            tempMin: '',
            tempMax: '',
            pressureMin: '',
            pressureMax: ''
        });
        
        // 弹窗状态
        const modal = reactive({
            show: false,
            title: '添加数据',
            editId: null
        });
        
        // 表单数据
        const form = reactive({
            temperature: '',
            pressure: '',
            x_ch4: 0,
            x_c2h6: 0,
            x_c3h8: 0,
            x_co2: 0,
            x_n2: 0,
            x_h2s: 0,
            x_ic4h10: 0
        });
        
        // Toast 消息列表
        const toasts = ref([]);

        // ==================== API 调用 ====================
        
        // 获取记录列表
        async function fetchRecords() {
            loading.value = true;
            try {
                const params = new URLSearchParams({
                    page: pagination.page,
                    per_page: pagination.perPage
                });
                
                if (filters.tempMin) params.append('temp_min', filters.tempMin);
                if (filters.tempMax) params.append('temp_max', filters.tempMax);
                if (filters.pressureMin) params.append('pressure_min', filters.pressureMin);
                if (filters.pressureMax) params.append('pressure_max', filters.pressureMax);
                
                const response = await fetch(`${API_BASE}/records?${params}`);
                const data = await response.json();
                
                records.value = data.records;
                pagination.total = data.total;
                pagination.totalPages = data.total_pages;
            } catch (error) {
                showToast('获取数据失败: ' + error.message, 'error');
            } finally {
                loading.value = false;
            }
        }
        
        // 获取统计信息
        async function fetchStatistics() {
            try {
                const response = await fetch(`${API_BASE}/statistics`);
                const data = await response.json();
                Object.assign(statistics.value, data);
            } catch (error) {
                console.error('获取统计信息失败:', error);
            }
        }
        
        // 创建记录
        async function createRecord() {
            try {
                const response = await fetch(`${API_BASE}/records`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        temperature: parseFloat(form.temperature),
                        pressure: parseFloat(form.pressure),
                        x_ch4: parseFloat(form.x_ch4) || 0,
                        x_c2h6: parseFloat(form.x_c2h6) || 0,
                        x_c3h8: parseFloat(form.x_c3h8) || 0,
                        x_co2: parseFloat(form.x_co2) || 0,
                        x_n2: parseFloat(form.x_n2) || 0,
                        x_h2s: parseFloat(form.x_h2s) || 0,
                        x_ic4h10: parseFloat(form.x_ic4h10) || 0
                    })
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('添加成功', 'success');
                    closeModal();
                    fetchRecords();
                    fetchStatistics();
                    if (showCharts.value) loadCharts();
                } else {
                    showToast(result.detail || '添加失败', 'error');
                }
            } catch (error) {
                showToast('网络错误: ' + error.message, 'error');
            }
        }
        
        // 更新记录
        async function updateRecord() {
            try {
                const response = await fetch(`${API_BASE}/records/${modal.editId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        temperature: parseFloat(form.temperature),
                        pressure: parseFloat(form.pressure),
                        x_ch4: parseFloat(form.x_ch4) || 0,
                        x_c2h6: parseFloat(form.x_c2h6) || 0,
                        x_c3h8: parseFloat(form.x_c3h8) || 0,
                        x_co2: parseFloat(form.x_co2) || 0,
                        x_n2: parseFloat(form.x_n2) || 0,
                        x_h2s: parseFloat(form.x_h2s) || 0,
                        x_ic4h10: parseFloat(form.x_ic4h10) || 0
                    })
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('更新成功', 'success');
                    closeModal();
                    fetchRecords();
                    fetchStatistics();
                    if (showCharts.value) loadCharts();
                } else {
                    showToast(result.detail || '更新失败', 'error');
                }
            } catch (error) {
                showToast('网络错误: ' + error.message, 'error');
            }
        }
        
        // 删除记录
        async function deleteRecord(id) {
            if (!confirm('确定要删除这条记录吗？')) return;
            
            try {
                const response = await fetch(`${API_BASE}/records/${id}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    showToast('删除成功', 'success');
                    fetchRecords();
                    fetchStatistics();
                    if (showCharts.value) loadCharts();
                } else {
                    const result = await response.json();
                    showToast(result.detail || '删除失败', 'error');
                }
            } catch (error) {
                showToast('网络错误: ' + error.message, 'error');
            }
        }

        // ==================== 图表功能 ====================
        
        function toggleCharts() {
            showCharts.value = !showCharts.value;
            if (showCharts.value) {
                nextTick(() => loadCharts());
            }
        }
        
        async function loadCharts() {
            try {
                // 加载温度分布图
                const tempResponse = await fetch(`${API_BASE}/chart/temperature`);
                const tempData = await tempResponse.json();
                renderBarChart('tempChart', tempData, 'rgba(255, 153, 64, 0.8)', tempChart, (chart) => { tempChart = chart; });
                
                // 加载压力分布图
                const pressureResponse = await fetch(`${API_BASE}/chart/pressure`);
                const pressureData = await pressureResponse.json();
                renderBarChart('pressureChart', pressureData, 'rgba(61, 158, 255, 0.8)', pressureChart, (chart) => { pressureChart = chart; });
                
                // 加载散点图
                const scatterResponse = await fetch(`${API_BASE}/chart/scatter`);
                const scatterData = await scatterResponse.json();
                renderScatterChart('scatterChart', scatterData);
                
            } catch (error) {
                console.error('加载图表失败:', error);
            }
        }
        
        function renderBarChart(canvasId, data, color, existingChart, setChart) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;
            
            if (existingChart) {
                existingChart.destroy();
            }
            
            const chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: data.title,
                        data: data.data,
                        backgroundColor: color,
                        borderColor: color.replace('0.8', '1'),
                        borderWidth: 1,
                        borderRadius: 6
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
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
            
            setChart(chart);
        }
        
        function renderScatterChart(canvasId, data) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;
            
            if (scatterChart) {
                scatterChart.destroy();
            }
            
            scatterChart = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: '温度-压力',
                        data: data.data,
                        backgroundColor: 'rgba(0, 212, 170, 0.6)',
                        borderColor: 'rgba(0, 212, 170, 1)',
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (context) => `温度: ${context.parsed.x.toFixed(1)}K, 压力: ${context.parsed.y.toFixed(2)}MPa`
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: { display: true, text: '温度 (K)', color: '#8899a8' },
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        y: {
                            title: { display: true, text: '压力 (MPa)', color: '#8899a8' },
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        }
                    }
                }
            });
        }

        // ==================== 导入导出功能 ====================
        
        function exportCSV() {
            window.location.href = `${API_BASE}/export/csv`;
            showToast('正在下载 CSV 文件...', 'success');
        }
        
        function exportExcel() {
            window.location.href = `${API_BASE}/export/excel`;
            showToast('正在下载 Excel 文件...', 'success');
        }
        
        async function handleImport(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            // 验证文件类型
            const validTypes = ['.csv', '.xlsx', '.xls'];
            const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'));
            if (!validTypes.includes(ext)) {
                showToast('请上传 CSV 或 Excel 文件', 'error');
                event.target.value = '';
                return;
            }
            
            importing.value = true;
            
            try {
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch(`${API_BASE}/import`, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    showToast(result.message, 'success');
                    fetchRecords();
                    fetchStatistics();
                    if (showCharts.value) loadCharts();
                } else {
                    showToast(result.detail || result.message || '导入失败', 'error');
                }
            } catch (error) {
                showToast('导入失败: ' + error.message, 'error');
            } finally {
                importing.value = false;
                event.target.value = '';
            }
        }

        // ==================== UI 操作 ====================
        
        // 打开添加弹窗
        function openAddModal() {
            modal.title = '添加数据';
            modal.editId = null;
            resetForm();
            modal.show = true;
        }
        
        // 打开编辑弹窗
        async function openEditModal(id) {
            try {
                const response = await fetch(`${API_BASE}/records/${id}`);
                const record = await response.json();
                
                modal.title = '编辑数据';
                modal.editId = id;
                
                form.temperature = record.temperature;
                form.pressure = record.pressure;
                form.x_ch4 = record.x_ch4;
                form.x_c2h6 = record.x_c2h6;
                form.x_c3h8 = record.x_c3h8;
                form.x_co2 = record.x_co2;
                form.x_n2 = record.x_n2;
                form.x_h2s = record.x_h2s;
                form.x_ic4h10 = record.x_ic4h10;
                
                modal.show = true;
            } catch (error) {
                showToast('获取记录失败', 'error');
            }
        }
        
        // 关闭弹窗
        function closeModal() {
            modal.show = false;
        }
        
        // 重置表单
        function resetForm() {
            form.temperature = '';
            form.pressure = '';
            form.x_ch4 = 0;
            form.x_c2h6 = 0;
            form.x_c3h8 = 0;
            form.x_co2 = 0;
            form.x_n2 = 0;
            form.x_h2s = 0;
            form.x_ic4h10 = 0;
        }
        
        // 保存记录
        function saveRecord() {
            if (!form.temperature || !form.pressure) {
                showToast('请填写温度和压力', 'error');
                return;
            }
            
            if (modal.editId) {
                updateRecord();
            } else {
                createRecord();
            }
        }
        
        // 搜索
        function search() {
            pagination.page = 1;
            fetchRecords();
        }
        
        // 清除搜索
        function clearSearch() {
            filters.tempMin = '';
            filters.tempMax = '';
            filters.pressureMin = '';
            filters.pressureMax = '';
            pagination.page = 1;
            fetchRecords();
        }
        
        // 刷新数据
        function refresh() {
            fetchRecords();
            fetchStatistics();
            if (showCharts.value) loadCharts();
        }
        
        // 跳转页面
        function goToPage(page) {
            if (page < 1 || page > pagination.totalPages) return;
            pagination.page = page;
            fetchRecords();
        }
        
        // 显示 Toast
        function showToast(message, type = 'success') {
            const id = Date.now();
            toasts.value.push({ id, message, type });
            setTimeout(() => {
                toasts.value = toasts.value.filter(t => t.id !== id);
            }, 3000);
        }
        
        // 格式化数字
        function formatNumber(num, decimals = 3) {
            if (num === null || num === undefined) return '0.000';
            return Number(num).toFixed(decimals);
        }
        
        // 计算显示的页码
        const visiblePages = computed(() => {
            const pages = [];
            const current = pagination.page;
            const total = pagination.totalPages;
            
            let start = Math.max(1, current - 2);
            let end = Math.min(total, current + 2);
            
            if (end - start < 4) {
                if (start === 1) {
                    end = Math.min(total, 5);
                } else {
                    start = Math.max(1, total - 4);
                }
            }
            
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        });

        // ==================== 生命周期 ====================
        onMounted(() => {
            fetchRecords();
            fetchStatistics();
            
            // ESC 关闭弹窗
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') closeModal();
            });
        });

        // 返回模板需要的数据和方法
        return {
            loading,
            importing,
            records,
            statistics,
            pagination,
            filters,
            modal,
            form,
            toasts,
            visiblePages,
            showCharts,
            
            fetchRecords,
            deleteRecord,
            openAddModal,
            openEditModal,
            closeModal,
            saveRecord,
            search,
            clearSearch,
            refresh,
            goToPage,
            formatNumber,
            toggleCharts,
            exportCSV,
            exportExcel,
            handleImport
        };
    }
});

// 挂载应用
app.mount('#app');
