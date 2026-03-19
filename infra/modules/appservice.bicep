@description('Azure App Service for the FastAPI backend (Python 3.12 Linux)')

param name string
param location string
param tags object = {}
param appServicePlanId string
param allowedOrigins string = '*'

@secure()
param githubToken string
param llmProvider string = 'auto'
param llmModel string = 'gpt-4o-mini'
@secure()
param geminiApiKey string = ''
param geminiModel string = 'gemini-2.0-flash'
param azureOpenAIEndpoint string = ''
@secure()
param azureOpenAIApiKey string = ''
param azureOpenAIDeployment string = ''
param azureOpenAIApiVersion string = '2024-10-21'

resource appService 'Microsoft.Web/sites@2022-09-01' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': 'backend' })
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlanId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      // Oryx runs the built app from a temp extraction path, so use a relative startup command.
      appCommandLine: 'bash startup.sh'
      // Ensure the build step (pip install -r requirements.txt) runs during deployment
      scmType: 'None'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'LLM_PROVIDER'
          value: llmProvider
        }
        {
          name: 'GITHUB_TOKEN'
          value: githubToken
        }
        {
          name: 'LLM_MODEL'
          value: llmModel
        }
        {
          name: 'GEMINI_API_KEY'
          value: geminiApiKey
        }
        {
          name: 'GEMINI_MODEL'
          value: geminiModel
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: azureOpenAIEndpoint
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: azureOpenAIApiKey
        }
        {
          name: 'AZURE_OPENAI_DEPLOYMENT'
          value: azureOpenAIDeployment
        }
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: azureOpenAIApiVersion
        }
        {
          name: 'DATABASE_URL'
          value: 'sqlite:////home/data/ai_app.db'
        }
        {
          name: 'ALLOWED_ORIGINS'
          value: allowedOrigins
        }
        {
          name: 'PYTHONDONTWRITEBYTECODE'
          value: '1'
        }
        {
          name: 'PYTHONUNBUFFERED'
          value: '1'
        }
      ]
    }
  }
}

resource appServiceScmPublishingPolicy 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2022-09-01' = {
  parent: appService
  name: 'scm'
  properties: {
    allow: true
  }
}

resource appServiceFtpPublishingPolicy 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2022-09-01' = {
  parent: appService
  name: 'ftp'
  properties: {
    allow: true
  }
}

output defaultHostname string = appService.properties.defaultHostName
output id string = appService.id
output name string = appService.name
