@description('Azure App Service for the FastAPI backend (Python 3.12 Linux)')

param name string
param location string
param tags object = {}
param appServicePlanId string

@secure()
param githubToken string
param llmModel string = 'gpt-4o-mini'

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
      // Tell App Service to run our startup.sh after pip install
      appCommandLine: 'bash /home/site/wwwroot/startup.sh'
      // Ensure the build step (pip install -r requirements.txt) runs during deployment
      scmType: 'None'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
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
          name: 'DATABASE_URL'
          value: 'sqlite:////home/data/ai_app.db'
        }
        {
          name: 'ALLOWED_ORIGINS'
          value: '*'  // Update to Static Web App URL after first deploy
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

output defaultHostname string = appService.properties.defaultHostName
output id string = appService.id
output name string = appService.name
