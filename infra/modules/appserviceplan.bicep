@description('Azure App Service Plan — B1 basic tier (no shared CPU quota, always-on capable)')

param name string
param location string
param tags object = {}

resource plan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true // required for Linux
  }
}

output id string = plan.id
