using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'aiappimprover')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus')
param githubToken = readEnvironmentVariable('GITHUB_TOKEN', '')
param llmProvider = readEnvironmentVariable('LLM_PROVIDER', 'auto')
param llmModel = readEnvironmentVariable('LLM_MODEL', 'gpt-4o-mini')
param geminiApiKey = readEnvironmentVariable('GEMINI_API_KEY', '')
param geminiModel = readEnvironmentVariable('GEMINI_MODEL', 'gemini-2.0-flash')
param azureOpenAIEndpoint = readEnvironmentVariable('AZURE_OPENAI_ENDPOINT', '')
param azureOpenAIApiKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY', '')
param azureOpenAIDeployment = readEnvironmentVariable('AZURE_OPENAI_DEPLOYMENT', '')
param azureOpenAIApiVersion = readEnvironmentVariable('AZURE_OPENAI_API_VERSION', '2024-10-21')
param staticWebAppLocation = readEnvironmentVariable('AZURE_SWA_LOCATION', 'eastus2')
