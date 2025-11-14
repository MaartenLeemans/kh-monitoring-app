param location string = resourceGroup().location
param environmentName string = 'kh-monitoring-env'
param containerAppName string = 'kh-monitoring-app'
param logAnalyticsName string = 'kh-monitoring-law'
param containerImage string

// Log Analytics
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

var logKey = listKeys(logAnalytics.id, '2020-08-01')

// Managed Environment
resource env 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logKey.primarySharedKey
      }
    }
  }
}

// Container App
resource app 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 5000
      }
    }
    template: {
      revisionSuffix: 'v1'
      containers: [
        {
          name: 'monitoring'
          image: containerImage
          resources: {
            cpu: 1.0
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}
