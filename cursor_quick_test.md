# Cursor Token消耗快速测试

## 测试1：简单代码优化（验证基本消耗）
```cursor
/model: gpt-5.2-codex
请优化backend/database.py中的get_chart_data函数，添加错误处理和性能监控。
```

## 测试2：UI改进（验证Opus消耗）
```cursor
/model: opus-4.6
请改进frontend/css/style.css，添加现代化的动画效果和过渡。
```

## 测试3：文档生成（验证Kimi消耗）
```cursor
/model: kimi
请为backend/main.py生成详细的API文档，包括参数说明和示例。
```

## 验证步骤
1. 依次执行上述3个命令
2. 每个命令后查看Cursor使用统计
3. 记录各模型的token增量
4. 确认所有模型都有消耗
