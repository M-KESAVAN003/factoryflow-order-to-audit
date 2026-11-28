# FactoryFlow — Internship Submission Checklist

> **Deployment & Verification Status**: Live Vercel Frontend, Render API (`/health`, Swagger `/docs`), Neon PostgreSQL (`factoryflow_db`), and GitHub Actions CI are deployed and verified. **Production Neon DB password & Render `SECRET_KEY` rotation remains `PENDING`**, **demo video/screenshots remain pending manual capture**, and **physical Android Chrome PWA offline verification remains `NOT VERIFIED`**.

## 1. Required Submission Links
- **Public GitHub Repository**: `https://github.com/M-KESAVAN003/factoryflow-order-to-audit`
- **Live Frontend Application (Vercel)**: `https://factoryflow-order-to-audit.vercel.app`
- **Live Backend Health Check (Render)**: `https://factoryflow-api-g1eu.onrender.com/health`
- **Backend OpenAPI / Swagger Docs**: `https://factoryflow-api-g1eu.onrender.com/docs`
- **GitHub Actions CI Workflow**: [.github/workflows/ci.yml](../.github/workflows/ci.yml)
- **Two-Page Design Note PDF**: [docs/DESIGN.pdf](DESIGN.pdf) *(verified `2` pages)*
- **Demo Video Walkthrough (<= 8 min)**: `<Pending manual screen recording using docs/DEMO_SCRIPT.md>`
- **Stage 3 PostgreSQL & QA Reports**: [docs/STAGE3_POSTGRES_ACCEPTANCE_REPORT.md](STAGE3_POSTGRES_ACCEPTANCE_REPORT.md), [docs/FINAL_QA_REPORT.md](FINAL_QA_REPORT.md), [docs/PHASE9_FINAL_VERIFICATION.md](PHASE9_FINAL_VERIFICATION.md)

## 2. Evaluator Demo Login Accounts (Hosted Demo Security Policy)
- **Default Disabled**: `DEMO_SEED_ENABLED=false` by default in `backend/.env.example` and `render.yaml`.
- **Hosted Demo Security**: Live accounts use separately generated strong passwords stored privately outside Git (never use sample passwords on live deployments). **Before public evaluator handover, rotate live Neon `production` password & Render `SECRET_KEY` (`PENDING`), and share evaluator credentials privately.**

| Evaluator Persona | Email | Role | Primary Console |
| :--- | :--- | :--- | :--- |
| **Factory Admin** | `admin@factoryflow.io` | `admin` | Full ERP + Governance + Approvals + Invoicing |
| **Factory Owner** | `owner@factoryflow.io` | `owner` | `/owner` Executive Dashboard (Read-Only + Exports) |
| **Salesman A** | `orders@factoryflow.io` | `order_manager` | Mobile & Offline PWA Order Entry (`Retailer A`, `Distributor B`) |
| **Salesman B** | `salesman_b@factoryflow.io` | `order_manager` | Multi-salesman isolation verification |
| **Production Supervisor** | `floor@factoryflow.io` | `floor_supervisor` | Production Runs, Variance, Expenses, Inventory |
| **Accountant / Auditor** | `auditor@factoryflow.io` | `auditor` | `/auditor` Read-Only Reports & Exports |
| **QA Inspector *(Optional)*** | `qa@factoryflow.io` | `qa_inspector` | BOM & Production QA Inspection |

## 3. Cloud Deployment & Post-Deploy Verification Reference
1. **GitHub Push**:
   ```bash
   git push -u origin main
   ```
2. **Managed PostgreSQL (Neon)**: Provision Neon PostgreSQL (`?sslmode=require`, Alembic head `0008_phase10_owner_role`; keep credentials strictly private).
3. **Backend (Render Web Service via `render.yaml`)**:
   - Root Directory: `backend` | Build: `pip install -r requirements.txt` | Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Health Check: `/health`.
   - Required Render env vars: `DATABASE_URL`, `SECRET_KEY` (>=32 random chars), `ENVIRONMENT=production`, `CORS_ORIGINS=["https://factoryflow-order-to-audit.vercel.app"]`, `DEMO_SEED_ENABLED=false`.
4. **Frontend (Vercel via `frontend/vercel.json`)**:
   - Root Directory: `frontend` | Build: `npm run build` | Output: `dist` | Node.js: `20.x`.
   - Env var: `VITE_API_BASE_URL=https://factoryflow-api-g1eu.onrender.com/api/v1`.
5. **Verified Live Endpoints & Remaining Manual Tasks**:
   - Confirmed `GET https://factoryflow-api-g1eu.onrender.com/health` (`HTTP 200`, `{"status":"ok","service":"factoryflow-api","database":"connected"}`), `GET /docs` (`HTTP 200`), and `https://factoryflow-order-to-audit.vercel.app` (`HTTP 200`).
   - **Pending Manual Actions**: Rotate live Neon `production` password & Render `SECRET_KEY`; execute physical Android Chrome PWA offline test on an isolated test backend (**`NOT VERIFIED`**); record `<= 8`-minute demo video + screenshots.
