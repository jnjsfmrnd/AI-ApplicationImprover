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

> **Note on App Service tier:** The project uses **B1** (Basic tier, ~$13/month). F1 Free tier was tested but its 60 CPU-min/day shared quota causes Kudu/SCM deploys to fail whenever the cap is hit, making it unreliable for portfolio demos.

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
   5. Deploy the React frontend from `frontend/dist` to Static Web Apps

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

Before `azd deploy frontend`, rebuild the Vite app so `frontend/dist` contains the latest production assets:
```bash
cd frontend
npm run build
cd ..
azd deploy frontend
```

## GitHub Actions deployment

This repo includes a production deployment workflow at [.github/workflows/deploy-azure.yml](.github/workflows/deploy-azure.yml).

Add these GitHub repository secrets:
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `GH_MODELS_TOKEN` - GitHub PAT with Models access for the backend inference calls

Add these GitHub repository variables if you want to override the defaults:
- `AZD_ENV_NAME`
- `AZURE_LOCATION`
- `AZURE_SWA_LOCATION`
- `LLM_MODEL`

The committed workflow currently defaults to:
- `AZD_ENV_NAME=JJAI-resumeImprover`
- `AZURE_LOCATION=westcentralus`
- `AZURE_SWA_LOCATION=eastus2`
- `LLM_MODEL=gpt-4o-mini`

If you want different values, either edit [.github/workflows/deploy-azure.yml](.github/workflows/deploy-azure.yml) directly or change the workflow to read from repository variables.

The workflow does this in order:
1. Logs into Azure using GitHub OIDC
2. Creates/selects the azd environment for the runner
3. Provisions infrastructure with `azd provision`
4. Reads `BACKEND_URL` from azd outputs
5. Builds the Vite frontend with `VITE_API_BASE_URL=<BACKEND_URL>/api`
6. Deploys backend and frontend with `azd deploy`

To enable Azure OIDC for GitHub Actions:
1. Create an Azure AD app or user-assigned managed identity for deployment
2. Add a federated credential for your GitHub repo and branch
3. Grant it permission over the subscription or resource group used by this project

After that, pushes to `main` or a manual `workflow_dispatch` run will deploy the app.

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
