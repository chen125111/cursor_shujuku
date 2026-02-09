# 气体水合物相平衡查询系统 - Cursor多模型协作指南

## 项目简介
这是一个气体水合物相平衡查询系统，用于查询气体混合物在不同温度和压力条件下的相平衡数据。

## 如何在Cursor中使用多模型协作

### 1. 启动项目分析
```bash
# 运行分析脚本
python start_cursor_collaboration.py
```

### 2. 各模型分工协作

#### GPT-5.2 Codex / Grok Code（后端优化）
```bash
# 切换到相应模型
/model gpt-5.2-codex

# 主要任务：
# - 优化 backend/database.py 中的查询算法
# - 实现多组分匹配优化
# - 添加缓存机制
# - 完善错误处理
```

#### Opus 4.6 / Sonnet 4.5（前端优化）
```bash
# 切换到相应模型
/model opus-4.6

# 主要任务：
# - 改进 frontend/index.html 界面设计
# - 添加数据可视化图表
# - 实现响应式布局
# - 优化用户交互
```

#### Fast模型（部署配置）
```bash
# 切换到相应模型
/model fast

# 主要任务：
# - 完善 Dockerfile 和 docker-compose.yml
# - 添加部署脚本
# - 实现监控告警
```

#### Kimi / 克（文档和测试）
```bash
# 切换到相应模型
/model kimi

# 主要任务：
# - 编写项目文档
# - 添加单元测试
# - 编写用户手册
```

### 3. 具体改进任务

#### 后端改进（GPT-5.2 Codex）
1. **数据验证增强**
   ```python
   # 在 backend/data_validation.py 中添加
   def validate_gas_composition(data):
       # 验证气体组分总和为1
       # 验证温度压力范围
       # 验证数据格式
       pass
   ```

2. **查询算法优化**
   ```python
   # 在 backend/database.py 中优化
   def optimized_composition_query(composition, tolerance=0.05):
       # 实现更高效的匹配算法
       # 添加缓存机制
       # 支持模糊查询
       pass
   ```

3. **性能优化**
   ```python
   # 添加缓存装饰器
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_cached_statistics():
       # 缓存统计结果
       pass
   ```

#### 前端改进（Opus 4.6）
1. **数据可视化**
   ```javascript
   // 在 frontend/js/charts.js 中添加
   function createTemperaturePressureChart(data) {
       // 使用Chart.js创建图表
       // 显示温度-压力分布
       // 添加交互功能
   }
   ```

2. **UI/UX优化**
   ```html
   <!-- 改进 frontend/index.html -->
   <!-- 添加现代化设计 -->
   <!-- 实现响应式布局 -->
   <!-- 添加动画效果 -->
   ```

3. **用户体验**
   ```javascript
   // 添加表单验证
   // 添加加载状态
   // 添加错误提示
   // 添加成功反馈
   ```

#### 部署改进（Fast模型）
1. **Docker优化**
   ```dockerfile
   # 优化 Dockerfile
   # 多阶段构建减小镜像大小
   # 添加健康检查
   # 优化资源限制
   ```

2. **部署脚本**
   ```bash
   # 创建部署脚本
   # 添加环境检查
   # 添加备份恢复
   # 添加监控配置
   ```

3. **CI/CD配置**
   ```yaml
   # 创建 GitHub Actions 配置
   # 自动化测试
   # 自动化部署
   # 代码质量检查
   ```

#### 文档改进（Kimi）
1. **项目文档**
   ```markdown
   # 编写详细文档
   # API文档
   # 部署指南
   # 用户手册
   ```

2. **测试代码**
   ```python
   # 添加单元测试
   # 添加集成测试
   # 添加性能测试
   ```

3. **代码注释**
   ```python
   # 完善代码注释
   # 添加类型提示
   # 添加文档字符串
   ```

### 4. 协作流程

1. **第一天**：项目分析和架构设计
   - 运行分析脚本
   - 确定改进方向
   - 分配具体任务

2. **第二天**：核心功能改进
   - 后端算法优化
   - 前端界面改进
   - 并行开发

3. **第三天**：部署和文档
   - 完善部署配置
   - 编写文档和测试
   - 集成测试

4. **第四天**：测试和优化
   - 性能测试
   - 用户体验测试
   - 问题修复

5. **第五天**：最终交付
   - 整理代码
   - 更新文档
   - 创建演示

### 5. 质量要求

1. **代码质量**
   - 符合PEP 8规范
   - 添加类型提示
   - 完善的错误处理

2. **前端质量**
   - 响应式设计
   - 浏览器兼容性
   - 性能优化

3. **文档质量**
   - 完整的API文档
   - 详细的部署指南
   - 清晰的用户手册

4. **测试质量**
   - 单元测试覆盖率>80%
   - 集成测试
   - 性能测试

### 6. 验收标准

1. 所有功能正常运行
2. 性能提升明显
3. 用户体验良好
4. 文档齐全准确
5. 部署简单可靠

### 7. 注意事项

1. **代码同步**
   - 定期提交代码
   - 解决冲突
   - 保持风格一致

2. **沟通协调**
   - 及时沟通问题
   - 分享进展
   - 协调接口

3. **版本控制**
   - 使用Git管理
   - 添加有意义的提交信息
   - 创建功能分支

### 8. 快速开始

```bash
# 1. 克隆项目（如果使用Git）
git clone <repository>

# 2. 安装依赖
cd cursor_shujuku
pip install -r requirements.txt

# 3. 启动分析
python start_cursor_collaboration.py

# 4. 打开Cursor编辑器
# 5. 按照分工使用不同模型
# 6. 开始改进工作
```

## 技术支持
如有问题，请参考：
- Cursor文档：https://cursor.sh/docs
- FastAPI文档：https://fastapi.tiangolo.com
- Chart.js文档：https://www.chartjs.org/docs

## 许可证
本项目采用MIT许可证。