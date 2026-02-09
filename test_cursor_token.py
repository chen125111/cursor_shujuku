#!/usr/bin/env python3
"""
Cursor Token消耗验证脚本
这个脚本生成需要在Cursor中执行的任务，确保token被消耗
"""

import os
from datetime import datetime

def generate_cursor_tasks():
    """生成Cursor任务列表"""
    
    tasks = [
        {
            "model": "gpt-5.2-codex",
            "task": """请优化backend/database.py中的query_by_composition函数：
1. 添加查询缓存，避免重复计算
2. 优化算法复杂度，从O(n)降低到O(log n)
3. 添加详细的性能监控
4. 编写单元测试验证优化效果

请生成具体的代码实现和测试用例。""",
            "expected_tokens": "8K-15K",
            "file": "backend/database.py"
        },
        {
            "model": "opus-4.6", 
            "task": """请重新设计前端数据可视化界面：
1. 创建现代化的仪表板布局
2. 添加实时数据刷新功能
3. 实现图表联动（点击一个图表，其他图表相应过滤）
4. 添加深色/浅色主题切换
5. 优化移动端响应式设计

请生成完整的HTML/CSS/JS代码。""",
            "expected_tokens": "12K-25K",
            "file": "frontend/index.html"
        },
        {
            "model": "grok-code",
            "task": """请实现高级缓存系统：
1. 二级缓存（内存 + Redis）
2. 缓存预热机制
3. 缓存失效策略（TTL + LRU）
4. 缓存命中率监控
5. 分布式缓存支持

请生成cache_advanced.py和相关配置。""",
            "expected_tokens": "10K-20K",
            "file": "backend/cache_advanced.py"
        },
        {
            "model": "kimi",
            "task": """请创建完整的项目文档：
1. API接口文档（OpenAPI规范）
2. 部署指南（Docker, Kubernetes, 云平台）
3. 开发者指南（代码规范、测试、CI/CD）
4. 用户手册（功能说明、使用示例）
5. 故障排查指南

请生成docs/目录下的完整文档。""",
            "expected_tokens": "15K-30K",
            "file": "docs/README.md"
        }
    ]
    
    return tasks

def create_cursor_commands(tasks):
    """生成Cursor命令文件"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"cursor_commands_{timestamp}.md"
    
    content = f"""# Cursor多模型任务执行指南
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 使用说明
1. 在Cursor中打开本项目
2. 复制下面的命令到Cursor聊天窗口
3. 执行命令并查看token消耗
4. 检查Cursor使用统计

## 任务列表

"""
    
    for i, task in enumerate(tasks, 1):
        content += f"""### 任务{i}: {task['model']} - {task['file']}

**预计token消耗**: {task['expected_tokens']}

**执行命令**:
```cursor
/model: {task['model']}
{task['task']}
```

**验证方法**:
1. 执行上述命令
2. 等待AI生成代码
3. 查看Cursor使用统计
4. 确认{task['model']}有token消耗

**成功标准**:
- ✅ 代码被实际修改/创建
- ✅ Cursor统计显示token消耗
- ✅ 功能正常工作

---

"""
    
    content += """
## Token消耗验证步骤

### 1. 执行前检查
- 打开Cursor → 设置 → 账户 → 使用统计
- 记录各模型的当前token使用量

### 2. 执行任务
- 按顺序执行上述任务
- 每个任务完成后保存更改

### 3. 执行后验证
- 再次查看使用统计
- 对比前后token使用量
- 确认有实际消耗

### 4. 问题排查
如果token没有消耗：
1. 确认使用了正确的`/model:`命令
2. 检查任务复杂度是否足够
3. 尝试重启Cursor
4. 联系Cursor技术支持

## 预期结果

| 任务 | 模型 | 最小token消耗 | 实际消耗 |
|------|------|---------------|----------|
| 任务1 | GPT-5.2 Codex | 8,000 | |
| 任务2 | Opus 4.6 | 12,000 | |
| 任务3 | Grok Code | 10,000 | |
| 任务4 | Kimi | 15,000 | |

**总计预计**: 45,000+ tokens

## 注意事项
1. 确保网络连接稳定
2. 每个任务可能需要2-5分钟
3. 复杂的任务消耗更多tokens
4. 保存所有生成的代码

---
*生成此文件用于验证Cursor多模型协作的token消耗情况*
"""
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    return output_file

def create_quick_test():
    """创建快速测试任务"""
    
    quick_test = """# Cursor Token消耗快速测试

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
"""
    
    with open("cursor_quick_test.md", "w", encoding="utf-8") as f:
        f.write(quick_test)
    
    return "cursor_quick_test.md"

def main():
    """主函数"""
    print("="*80)
    print("Cursor Token消耗验证工具")
    print("="*80)
    
    print("\n1. 生成详细任务列表...")
    tasks = generate_cursor_tasks()
    detailed_file = create_cursor_commands(tasks)
    print(f"   ✓ 生成详细任务文件: {detailed_file}")
    
    print("\n2. 生成快速测试任务...")
    quick_file = create_quick_test()
    print(f"   ✓ 生成快速测试文件: {quick_file}")
    
    print("\n3. 创建验证脚本...")
    verification_script = """#!/bin/bash
# Cursor Token消耗验证脚本

echo "Cursor Token消耗验证"
echo "======================"

echo "1. 请打开Cursor编辑器"
echo "2. 打开项目: /home/cc/桌面/cursor_shujuku/cursor_shujuku"
echo "3. 执行以下步骤验证token消耗:"
echo ""
echo "步骤A: 查看当前token使用量"
echo "  - 点击Cursor左下角账户图标"
echo "  - 选择'使用统计'"
echo "  - 记录各模型的当前使用量"
echo ""
echo "步骤B: 执行测试任务"
echo "  - 打开文件: cursor_quick_test.md"
echo "  - 复制第一个命令到Cursor聊天窗口"
echo "  - 执行并等待完成"
echo "  - 再次查看使用统计"
echo ""
echo "步骤C: 验证消耗"
echo "  - 对比前后token使用量"
echo "  - 确认GPT-5.2 Codex有增量"
echo "  - 重复测试其他模型"
echo ""
echo "如果token没有消耗，请检查:"
echo "  1. 是否使用了正确的/model:命令"
echo "  2. 任务是否足够复杂"
echo "  3. Cursor是否是最新版本"
echo "  4. 账户是否有可用额度"
"""
    
    with open("verify_cursor.sh", "w", encoding="utf-8") as f:
        f.write(verification_script)
    
    os.chmod("verify_cursor.sh", 0o755)
    print(f"   ✓ 生成验证脚本: verify_cursor.sh")
    
    print("\n" + "="*80)
    print("使用说明:")
    print("="*80)
    print("1. 在Cursor中打开本项目")
    print("2. 运行验证脚本: ./verify_cursor.sh")
    print("3. 按照提示执行测试任务")
    print("4. 查看Cursor使用统计确认token消耗")
    print("")
    print("生成的文件:")
    print(f"  - {detailed_file}: 详细的多模型任务")
    print(f"  - {quick_file}: 快速测试任务")
    print(f"  - verify_cursor.sh: 验证脚本")
    print("")
    print("关键检查点:")
    print("  ✅ 使用/model:命令切换模型")
    print("  ✅ 执行具体的编码任务")
    print("  ✅ 查看Cursor使用统计")
    print("  ✅ 确认token有实际消耗")
    print("="*80)

if __name__ == "__main__":
    main()