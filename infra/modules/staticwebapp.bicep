@description('Azure Static Web App for the React/Vite frontend (Free tier)')

param name string
param location string
param tags object = {}

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': 'frontend' })
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    // Source control is connected after first `azd deploy` via the GitHub Actions workflow
    buildProperties: {
      appLocation: '/'
      outputLocation: 'dist'
      appBuildCommand: 'npm run build'
    }
  }
}

output defaultHostname string = staticWebApp.properties.defaultHostname
output id string = staticWebApp.id
output name string = staticWebApp.name
