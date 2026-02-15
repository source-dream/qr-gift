# QRGift Backend

## 开发启动

推荐使用 `uv`：

```bash
uv sync --extra dev
uv run python scripts/db_upgrade.py
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

若本机未安装 `uv`，可使用 `pip`：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install -e .
python scripts/db_upgrade.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

首次访问登录页时会引导创建管理员账号。

若历史数据库是旧版本直接建表（无迁移记录），`scripts/db_upgrade.py` 会自动补齐版本号并继续迁移。

如需本地重置管理员密码：

```bash
uv run python scripts/reset_admin.py --username admin --password 新密码
```
