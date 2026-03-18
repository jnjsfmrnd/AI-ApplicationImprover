targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment (used to generate unique resource names)')
param environmentName string

@minLength(1)
@description('Primary Azure region for all resources')
param location string

// Tags applied to every resource
var tags = {
  'azd-env-name': environmentName
}

// Derive a short, globally-unique prefix from environmentName
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// ── Resource Group ──────────────────────────────────────────────────────────

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

// ── App Service Plan (F1 free) ───────────────────────────────────────────────

module appServicePlan 'modules/appserviceplan.bicep' = {
  name: 'appServicePlan'
  scope: rg
  params: {
    name: 'asp-${resourceToken}'
    location: location
    tags: tags
  }
}

// ── App Service (FastAPI backend) ────────────────────────────────────────────

module appService 'modules/appservice.bicep' = {
  name: 'appService'
  scope: rg
  params: {
    name: 'app-${resourceToken}'
    location: location
    tags: tags
    appServicePlanId: appServicePlan.outputs.id
    githubToken: githubToken
    llmModel: llmModel
    allowedOrigins: 'https://${staticWebApp.outputs.defaultHostname}'
  }
}

// ── Static Web App (React frontend) ─────────────────────────────────────────

module staticWebApp 'modules/staticwebapp.bicep' = {
  name: 'staticWebApp'
  scope: rg
  params: {
    name: 'swa-${resourceToken}'
    location: staticWebAppLocation
    tags: tags
  }
}

// ── Parameters ───────────────────────────────────────────────────────────────

@secure()
@description('GitHub PAT with Models permission (for GitHub Models AI inference)')
param githubToken string

@description('GitHub Models model name to use, e.g. gpt-4o-mini')
param llmModel string = 'gpt-4o-mini'

@description('Azure region for Static Web App (limited availability)')
param staticWebAppLocation string = 'eastus2'

// ── Outputs (consumed by azd) ────────────────────────────────────────────────

output BACKEND_URL string = 'https://${appService.outputs.defaultHostname}'
output STATIC_WEB_APP_URL string = 'https://${staticWebApp.outputs.defaultHostname}'
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_LOCATION string = location
