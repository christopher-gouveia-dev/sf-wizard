# SF Wizard (sf-wizard) — v0.1.0

SF Wizard is a **local** companion tool for Salesforce developers and release managers.

This version (v0.1.0) focuses on a single vertical slice:
- Detect the currently connected Salesforce orgs via **SF CLI**
- Select an org and run **SOQL queries** (API) via SF CLI
- Show results and logs, with a **Copy Excel** button

> UI language is **English** by design.

---

## Requirements

### Option A — Run with Docker (recommended)
- Docker + Docker Compose
- Internet access to build images (first run)

### Option B — Run without Docker
- Python **3.10+**
- Node.js **18+**
- Salesforce CLI (`sf`) installed and authenticated

---

## Run with Docker

From the repository root:

```bash
docker compose -f docker/compose.yml up --build
```

Open:
- Web UI: http://localhost:5173
- API Health: http://localhost:8000/api/health

> SF CLI auth is persisted by mounting your local `~/.sf` into the container.
> If your orgs are not listed, run `sf org list` on your machine first, or authenticate.

Stop:

```bash
docker compose -f docker/compose.yml down
```

---

## Run without Docker

### 1) Backend (FastAPI)

```bash
cd apps/api
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn sf_wizard.main:app --reload --host 127.0.0.1 --port 8000
```

### 2) Frontend (Vite)

In another terminal:

```bash
cd apps/web
npm install
npm run dev
```

Open:
- Web UI: http://localhost:5173

The dev server proxies `/api` to `http://127.0.0.1:8000`.

---

## Basic usage

1. Make sure you're authenticated with SF CLI:
   ```bash
   sf org list
   ```
2. In SF Wizard, pick an org in the header dropdown.
3. Go to **Query** and run a SOQL query.

---

## Project structure

- `apps/api`: FastAPI backend, SF CLI orchestration
- `apps/web`: Vue 3 + Vite + Tailwind frontend
- `docker`: Dockerfiles + compose
- `data`: local persisted settings/runs (mounted in Docker)

---

## Versioning

Use annotated tags:

```bash
git tag -a v0.1.0 -m "sf-wizard v0.1.0"
git push origin v0.1.0
```

---

## Notes

- v0.1.0 uses **SF CLI** for query execution (`sf data query`).
- Bulk API mode is intentionally not included in v0.1.0.
