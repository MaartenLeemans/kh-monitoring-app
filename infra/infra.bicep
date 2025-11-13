param location string = resourceGroup().location
param environmentName string = 'kh-monitoring-env'
param containerAppName string = 'kh-monitoring-app'
param logAnalyticsName string = 'kh-monitoring-law'
param containerImage string

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

resource logKeys 'Microsoft.OperationalInsights/workspaces/sharedKeys@2020-08-01' = {
  name: 'default'
  parent: logAnalytics
}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logKeys.properties.primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 5000
      }
    }
    template: {
      containers: [
        {
          name: 'monitoring'
          image: containerImage
          resources: {
            cpu: 0.5
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