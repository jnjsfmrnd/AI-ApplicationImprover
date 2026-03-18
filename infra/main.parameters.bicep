using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'aiappimprover')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus')
param githubToken = readEnvironmentVariable('GITHUB_TOKEN', '')
param llmModel = readEnvironmentVariable('LLM_MODEL', 'gpt-4o-mini')
param staticWebAppLocation = readEnvironmentVariable('AZURE_SWA_LOCATION', 'eastus2')
