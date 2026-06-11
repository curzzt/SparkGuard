# 火花续航 · SparkGuard

火花续航是一款单页面 Web 工具，帮助已绑定抖音账号的用户在每日指定时间，按官方允许的方式自动向预设对象发起「续火花」互动，并完整记录每次执行结果。

产品坚持「能力边界透明」原则：官方接口不支持的场景标记为 `unsupported`，绝不伪造成功，也不使用抓包、模拟点击等非官方手段。

![火花续航面板首页](docs/homepage.png)

## 功能概览

- **用户体系**：手机号 + 密码注册登录，JWT 鉴权，接口限流。
- **抖音账号**：OAuth 授权绑定、扫码关联、Token 加密存储与自动刷新、解绑。
- **续火花对象**：对象 CRUD、批量启用/停用、最近联系人导入、今日状态与失败原因展示。
- **自动续火花**：全局开关、每日执行时间、默认/随机消息模板、每日上限、跳过今日。
- **执行与日志**：APScheduler 每分钟扫描到点任务、立即执行、今日状态汇总、最近 7 天执行记录。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + Vite + TypeScript + Ant Design + React Query + Zustand |
| 后端 | FastAPI + SQLAlchemy(async) + Alembic + APScheduler + Pydantic v2 |
| 数据库 | PostgreSQL 15 |
| 集成 | 抖音开放平台 API（httpx）、Playwright（扫码登录） |
| 安全 | JWT、bcrypt、Fernet 加密、slowapi 限流 |

## 目录结构

```text
SparkGuard/
├── backend/                 # FastAPI 服务
│   ├── app/
│   │   ├── api/v1/          # auth / douyin / spark 路由
│   │   ├── core/            # 配置、安全、依赖、限流、错误
│   │   ├── integrations/    # 抖音开放平台集成
│   │   ├── jobs/            # APScheduler 调度
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── schemas/         # Pydantic 模型
│   │   └── services/        # 业务服务
│   └── alembic/             # 数据库迁移
├── frontend/                # React 单页应用
│   └── src/
│       ├── api/             # 接口封装
│       ├── components/spark # 面板各区块组件
│       ├── pages/           # 登录页与火花续航面板
│       └── types/           # 类型定义
├── docs/                    # 设计文档
└── docker-compose.yml
```

## 快速开始（Docker Compose）

确保已安装 Docker 与 Docker Compose，在项目根目录执行：

```bash
docker compose up --build
```

启动后访问：

- 前端：http://localhost:5573
- 后端 API：http://localhost:8800
- API 文档：http://localhost:8800/docs

开发模式下 `DEV_BYPASS_AUTH=true`，可跳过登录直接进入面板调试。

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 环境变量

后端关键配置（参考 `docker-compose.yml`，本地可放入 `backend/.env`）：

```env
APP_ENV=development
JWT_SECRET=请替换为随机密钥
JWT_EXPIRE_HOURS=24
FERNET_KEY=请替换为 Fernet 密钥
DATABASE_URL=postgresql+asyncpg://sparkguard:sparkguard@localhost:5432/sparkguard
FRONTEND_URL=http://localhost:5573
PLAYWRIGHT_HEADLESS=true
RATE_LIMIT_ENABLED=true

# 抖音开放平台
DOUYIN_CLIENT_KEY=
DOUYIN_CLIENT_SECRET=
DOUYIN_REDIRECT_URI=http://localhost:8000/api/douyin/callback
```

`FERNET_KEY` 可通过 `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 生成。

## 设计文档

完整的产品定位、表设计、API 约定、调度与执行流程见 [docs/火花续航-首期设计文档.md](docs/火花续航-首期设计文档.md)。
