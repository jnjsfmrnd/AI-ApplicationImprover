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
- AI: **GitHub Models** (default) with optional Gemini and Azure provider support
- IaC: Azure Developer CLI (azd) + Bicep

> **Note on App Service tier:** The project uses **B1** (Basic tier, ~$13/month). F1 Free tier was tested but its 60 CPU-min/day shared quota causes Kudu/SCM deploys to fail whenever the cap is hit, making it unreliable for portfolio demos.

---

## Local development

### 1. Get model credentials
Use either of these:

- **GitHub Models (recommended for now):** a fine-grained PAT with **Models (read)** from <https://github.com/settings/tokens>.
- **Gemini (optional):** API key from Google AI Studio or Gemini API.
- **Azure OpenAI (optional):** endpoint, deployment name, and API key from your Azure OpenAI resource.

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
LLM_PROVIDER=auto
LLM_MODEL=gpt-4o-mini
GITHUB_MODEL_CANDIDATES=gpt-4.1-mini,gpt-4o-mini
GITHUB_MODEL_RETRY_STATUSES=408,409,425,429,500,502,503,504
GITHUB_TOKEN=ghp_...

# Optional Gemini path:
# GEMINI_API_KEY=<your_gemini_api_key>
# GEMINI_MODEL=gemini-2.0-flash

# Optional Azure provider path:
# AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
# AZURE_OPENAI_API_KEY=<your_azure_openai_key>
# AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
# AZURE_OPENAI_API_VERSION=2024-10-21
DATABASE_URL=sqlite:///./ai_application_improver.db
```

`GITHUB_MODEL_CANDIDATES` controls model routing order for GitHub Models. The backend will try each model in order when requests hit retryable errors (for example `429` rate limit or transient `5xx`), which helps maximize quality while staying within free-tier limits.

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

3. **Set your model credentials** (for provisioning app settings):
   ```bash
   # GitHub Models (recommended)
   $env:GITHUB_TOKEN = "ghp_..."   # PowerShell

   # Optional Gemini provider
   $env:GEMINI_API_KEY = "<gemini-key>"
   $env:GEMINI_MODEL = "gemini-2.0-flash"

   # Optional Azure provider
   $env:AZURE_OPENAI_ENDPOINT = "https://<resource>.openai.azure.com"
   $env:AZURE_OPENAI_API_KEY = "<key>"
   $env:AZURE_OPENAI_DEPLOYMENT = "gpt-4o-mini"
   # or
   export GITHUB_TOKEN=ghp_...
   export GEMINI_API_KEY="<gemini-key>"
   export GEMINI_MODEL="gemini-2.0-flash"
   export AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com"
   export AZURE_OPENAI_API_KEY="<key>"
   export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
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
- `GH_MODELS_TOKEN` (recommended)
- `GEMINI_API_KEY` (optional, only if using Gemini)

Add these GitHub repository variables if you want to override the defaults:
- `AZD_ENV_NAME`
- `AZURE_LOCATION`
- `AZURE_SWA_LOCATION`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `GEMINI_MODEL`

The committed workflow currently defaults to:
- `AZD_ENV_NAME=JJAI-resumeImprover`
- `AZURE_LOCATION=westcentralus`
- `AZURE_SWA_LOCATION=eastus2`
- `LLM_PROVIDER=auto`
- `LLM_MODEL=gpt-4o-mini`

If you want different values, either edit [.github/workflows/deploy-azure.yml](.github/workflows/deploy-azure.yml) directly or change the workflow to read from repository variables.

The workflow does this in order:
1. Logs into Azure using GitHub OIDC
2. Verifies the Azure auth secrets and `GH_MODELS_TOKEN` are present
3. Creates/selects the azd environment for the runner
4. Provisions infrastructure with `azd provision`
5. Reads `BACKEND_URL` from azd outputs
6. Builds the Vite frontend with `VITE_API_BASE_URL=<BACKEND_URL>/api`
7. Deploys backend and frontend with `azd deploy`

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
- `POST /api/extract/job-context`
- `POST /api/export/pdf`
- `GET  /api/mcp/tools`
- `POST /api/mcp/run`
- `GET  /health`

## Notes
- Resume upload supports `.txt`, `.pdf`, and `.docx` text extraction.
- Resume uploads and generated artifacts are persisted to the SQLite database (`resumes`, `generations` tables).
- App Service F1 is shared infrastructure with no "Always On" — the first request after idle may take ~10–30 seconds (cold start). Acceptable for a portfolio demo.
- Backend generation uses GitHub Models whenever `GITHUB_TOKEN` is set.
- Set `LLM_PROVIDER=gemini` to force Gemini when `GEMINI_API_KEY` is configured.
- If GitHub Models is not configured, backend can fall back to Azure OpenAI when `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` are set.
- GitHub Actions currently provisions the app for the GitHub Models path by passing `GH_MODELS_TOKEN` into deployment.
- If neither credential path is configured (or external calls fail), the app uses mock generation output so the workflow still runs.
