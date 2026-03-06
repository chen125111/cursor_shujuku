# 贡献指南（Contributing）

感谢你愿意改进本项目。为了让协作高效、可回溯、可持续，请在提交前遵循以下约定。

---

## 开发环境

### 安装依赖

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements-dev.txt
```

### 配置

建议复制并使用配置模板：

```bash
cp .env.example .env
set -a && . ./.env && set +a
```

启动开发服务：

```bash
python3 -m uvicorn backend.main:app --reload
```

---

## 测试要求

提交前请确保测试通过：

```bash
python3 -m pytest
```

如果你新增了 API、数据校验规则或数据库逻辑：

- **必须**补充对应的单元测试
- **建议**补充至少一条集成测试（FastAPI TestClient 路径级验证）

测试隔离说明见 `docs/TESTING.md`。

---

## 代码风格与质量

项目使用 `ruff` / `mypy`（配置见 `pyproject.toml`）：

```bash
ruff check .
mypy .
```

> 说明：当前仓库对历史代码做了部分忽略（例如长行），新代码请尽量保持简洁与一致。

---

## 文档要求

当你新增/修改功能时，请同步更新：

- `README.md`（如影响使用方式/配置）
- `docs/API.md`（如新增/变更接口）
- `docs/CONFIGURATION.md`（如新增环境变量/配置项）

---

## 安全注意事项（必须）

- 不要提交任何真实密钥、token、密码或生产数据库地址
- 不要把真实 `.env` 提交到仓库（仓库已忽略 `.env`）
- 任何涉及认证/权限/限流/审计的改动，必须带测试，并在 PR 描述中说明威胁模型与回滚策略

---

## 提交信息建议

保持提交信息清晰可追溯：

- `docs: ...` 文档更新
- `feat: ...` 新功能
- `fix: ...` 修复
- `test: ...` 测试补充
- `chore: ...` 杂项（构建、脚本、CI）

---

## 许可证

提交贡献即表示你同意你的贡献在本项目的 MIT License 下发布（见 `LICENSE`）。

