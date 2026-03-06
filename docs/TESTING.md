# 测试指南

项目使用 `pytest` 编写单元测试与集成测试，测试目录为 `tests/`。

---

## 安装测试依赖

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
```

---

## 运行测试

```bash
python3 -m pytest
```

带覆盖率：

```bash
python3 -m pytest --cov
```

---

## 测试隔离策略（重要）

测试通过 `tests/conftest.py` 在导入 `backend.*` 之前设置环境变量，确保：

- 使用临时 SQLite 文件（隔离真实数据）
- 禁用缓存（`CACHE_ENABLED=0`）与 Redis 连接
- 固定 `SECRET_KEY` 与管理员密码，便于集成测试登录

如果你新增了“导入即读取环境变量”的模块，请确保测试仍然在 import 之前完成必要的 `os.environ` 设置。

