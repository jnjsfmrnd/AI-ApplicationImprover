# AI Application Improver

MVP project that uploads a resume, accepts a job description, and generates:
- Recruiter rewrite
- ATS-optimized resume
- Tailored cover letter
- Skill gap analysis
- Same-day skill micro-project scopes + resume bullets

It includes an Agent Orchestrator + MCP-style tool adapters and supports in-app preview + PDF download for resume and cover letter.

## Stack
- Frontend: React + TypeScript (Vite) → deployed to **Azure Static Web Apps (Free)**
- Backend: FastAPI (Python 3.12) → deployed to **Azure App Service (F1 free)**
- Persistence: SQLite on App Service `/home` (persistent Azure Files mount)
- PDF: reportlab
- AI: **GitHub Models** via `azure-ai-inference` SDK (gpt-4o-mini, completely free)
- IaC: Azure Developer CLI (azd) + Bicep

---

## Local development

### 1. Get a GitHub Models token
1. Go to <https://github.com/settings/tokens> and create a **fine-grained PAT**.
2. Under **Permissions → Account permissions**, enable **Models** (read).
3. Copy the token.

### 2. Backend setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
copy .env.example .env       # then edit .env and paste your token
```

Edit `backend/.env`:
```
GITHUB_TOKEN=ghp_...         # your GitHub Models token
LLM_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./ai_application_improver.db
```

```bash
python -m alembic upgrade head
# From the repo root:
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --app-dir backend --reload-dir backend/app
```

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
```
Open <http://localhost:5173>.

---

## Azure deployment (one command)

### Prerequisites
| Tool | Install |
|------|---------|
| [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) | `winget install Microsoft.AzureCLI` |
| [Azure Developer CLI (azd)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd) | `winget install Microsoft.Azd` |
| Node 18+ | `winget install OpenJS.NodeJS.LTS` |
| Python 3.12 | `winget install Python.Python.3.12` |
| Git | Push this repo to GitHub first |

> **Note:** App Service only runs Python up to 3.12. The codebase is fully
> compatible — no syntax changes needed.

### First-time setup

1. **Create a free Azure account** at <https://azure.microsoft.com/free/> (includes $200 credit, F1/Free-tier resources are always free).

2. **Sign in:**
   ```bash
   az login
   azd auth login
   ```

3. **Set your GitHub token** (needed by Bicep provisioning):
   ```bash
   $env:GITHUB_TOKEN = "ghp_..."   # PowerShell
   # or
   export GITHUB_TOKEN=ghp_...     # bash
   ```

4. **Provision + deploy everything:**
   ```bash
   azd up
   ```
   When prompted:
   - **Environment name**: e.g. `aiappimprover`
   - **Azure subscription**: pick your subscription
   - **Location**: e.g. `eastus`

   `azd up` will:
   1. Create a resource group `rg-aiappimprover`
   2. Provision an App Service Plan (F1 free) + App Service (Python 3.12)
   3. Provision an Azure Static Web App (Free tier)
   4. Build & deploy the FastAPI backend (pip install runs on App Service)
   5. Build the React frontend with `VITE_API_BASE_URL` set to your App Service URL, then deploy to Static Web Apps

5. **After first deploy — tighten CORS (optional but recommended):**
   ```bash
   # Replace <swa-url> with the URL printed by azd (e.g. https://yellow-beach-xxx.azurestaticapps.net)
   az webapp config appsettings set \
     --resource-group rg-aiappimprover \
     --name app-<token> \
     --settings ALLOWED_ORIGINS=<swa-url>
   azd deploy backend
   ```

### Subsequent deploys
```bash
azd deploy          # redeploy both services
azd deploy backend  # backend only
azd deploy frontend # frontend only
```

### Tear down
```bash
azd down            # deletes all Azure resources (keeps local code unchanged)
```

---

## API endpoints
- `POST /api/resume/upload`
- `POST /api/generate/rewrite`
- `POST /api/generate/ats`
- `POST /api/generate/cover-letter`
- `POST /api/generate/skill-gap`
- `POST /api/generate/skill-projects`
- `POST /api/export/pdf`
- `GET  /api/mcp/tools`
- `POST /api/mcp/run`
- `GET  /health`

## Notes
- Resume upload supports `.txt`, `.pdf`, and `.docx` text extraction.
- Resume uploads and generated artifacts are persisted to the SQLite database (`resumes`, `generations` tables).
- App Service F1 is shared infrastructure with no "Always On" — the first request after idle may take ~10–30 seconds (cold start). Acceptable for a portfolio demo.
- To use a different GitHub Models model, change `LLM_MODEL` in `backend/.env` (local) or the App Service application setting (Azure). Available models: `gpt-4o-mini`, `gpt-4o`, `Phi-3.5-mini-instruct`.
- If `GITHUB_TOKEN` is not set (or the inference call fails), the app uses mock generation output so the workflow still runs.
