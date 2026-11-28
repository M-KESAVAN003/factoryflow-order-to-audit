# FactoryFlow — Internship Submission Checklist

> **Notice**: Live external URLs remain marked as pending until the repository owner pushes to GitHub and connects Neon, Render, and Vercel credentials.

## 1. Required Submission Links
- **Public GitHub Repository**: `https://github.com/M-KESAVAN003/factoryflow-order-to-audit`
- **Live Frontend Application (Vercel)**: `https://<your-frontend>.vercel.app` *(deploy `frontend/` with `VITE_API_BASE_URL`)*
- **Live Backend Health Check (Render)**: `https://<your-backend>.onrender.com/health`
- **Backend OpenAPI / Swagger Docs**: `https://<your-backend>.onrender.com/docs`
- **GitHub Actions CI Workflow**: [.github/workflows/ci.yml](../.github/workflows/ci.yml)
- **Two-Page Design Note PDF**: [docs/DESIGN.pdf](DESIGN.pdf) *(verified <= 2 pages)*
- **Demo Video Walkthrough (<= 8 min)**: `<record using docs/DEMO_SCRIPT.md>`
- **Benchmark & QA Verification Report**: [docs/FINAL_QA_REPORT.md](FINAL_QA_REPORT.md) & [docs/PHASE9_FINAL_VERIFICATION.md](PHASE9_FINAL_VERIFICATION.md)

## 2. Evaluator Demo Login Accounts (Hosted Demo Security Policy)
- **Default Disabled**: `DEMO_SEED_ENABLED=false` by default in `backend/.env.example` and `render.yaml`.
- **Hosted Demo Seeding**: When provisioning a live demo environment, configure a unique strong `DEMO_SEED_PASSWORD` (`>= 12` chars; `scripts.seed` and FastAPI startup reject publicly documented passwords like `FactoryFlow!2026` in `ENVIRONMENT=production`), run a one-time seed (`python -m scripts.seed`), and share evaluator credentials privately rather than committing them.

| Evaluator Persona | Email | Role | Primary Console |
| :--- | :--- | :--- | :--- |
| **Factory Admin** | `admin@factoryflow.io` | `admin` | Full ERP + Governance + Approvals + Invoicing |
| **Factory Owner** | `owner@factoryflow.io` | `owner` | `/owner` Executive Dashboard (Read-Only + Exports) |
| **Salesman A** | `orders@factoryflow.io` | `order_manager` | Mobile & Offline PWA Order Entry (`Retailer A`, `Distributor B`) |
| **Salesman B** | `salesman_b@factoryflow.io` | `order_manager` | Multi-salesman isolation verification |
| **Production Supervisor** | `floor@factoryflow.io` | `floor_supervisor` | Production Runs, Variance, Expenses, Inventory |
| **Accountant / Auditor** | `auditor@factoryflow.io` | `auditor` | `/auditor` Read-Only Reports & Exports |
| **QA Inspector *(Optional)*** | `qa@factoryflow.io` | `qa_inspector` | BOM & Production QA Inspection |

## 3. Manual Cloud Deployment Steps (For Repository Owner)
1. **GitHub Push**:
   ```bash
   git push -u origin main
   ```
2. **Managed PostgreSQL (Neon)**: Create a Neon project, copy the pooled PostgreSQL URL with `?sslmode=require` (keep private — never paste into chat or commit).
3. **Backend (Render Web Service via `render.yaml`)**:
   - Root Directory: `backend` | Build: `pip install -r requirements.txt` | Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Health Check: `/health`.
   - Set secret env vars in Render Dashboard: `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT=production`, `CORS_ORIGINS=["https://<your-frontend>.vercel.app"]`, `DEMO_SEED_ENABLED=true` (strictly for evaluator demo DB), `DEMO_SEED_PASSWORD=<strong-demo-password>`.
   - Run once in Render Shell to seed dummy benchmark masters: `python -m scripts.seed`.
4. **Frontend (Vercel via `frontend/vercel.json`)**:
   - Root Directory: `frontend` | Build Command: `npm run build` | Output Directory: `dist` | Node.js: `20.x`.
   - Set env var in Vercel: `VITE_API_BASE_URL=https://<your-backend>.onrender.com/api/v1`.
5. **Post-Deploy Live Smoke Verification**:
   - Confirm `GET https://<your-backend>.onrender.com/health` returns `{"status":"ok","database":"connected"}`.
   - Open `https://<your-frontend>.vercel.app`, test login across roles, Invoice PDF download, Excel/CSV export, and offline PWA mode.
