// Zava Energy SSOT workshop - jalur privat untuk Azure SQL (opsional)
// Gunakan bila kebijakan organisasi menonaktifkan public network access Azure SQL.
// Membuat VNet, private endpoint SQL + private DNS, dan subnet terdelegasi untuk Fabric VNet data gateway.
targetScope = 'resourceGroup'

param location string = resourceGroup().location

@description('Nama logical server Azure SQL yang sudah dibuat oleh main.bicep.')
param serverName string

param vnetName string = 'vnet-zava-ssot'
param addressPrefix string = '10.80.0.0/16'
param privateEndpointSubnetPrefix string = '10.80.1.0/24'
param gatewaySubnetPrefix string = '10.80.2.0/24'

param tags object = {
  workload: 'zava-ssot-workshop'
  dataClassification: 'synthetic'
}

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' existing = {
  name: serverName
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: [
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-fabric-gateway'
        properties: {
          addressPrefix: gatewaySubnetPrefix
          delegations: [
            {
              name: 'powerplatform-vnetaccesslinks'
              properties: {
                serviceName: 'Microsoft.PowerPlatform/vnetaccesslinks'
              }
            }
          ]
        }
      }
    ]
  }
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${serverName}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[0].id
    }
    privateLinkServiceConnections: [
      {
        name: 'sql'
        properties: {
          privateLinkServiceId: sqlServer.id
          groupIds: [
            'sqlServer'
          ]
        }
      }
    ]
  }
}

resource dnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink${environment().suffixes.sqlServerHostname}'
  location: 'global'
  tags: tags
}

resource dnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: dnsZone
  name: '${vnetName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource dnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'sql'
        properties: {
          privateDnsZoneId: dnsZone.id
        }
      }
    ]
  }
}

output vnetName string = vnet.name
output gatewaySubnetName string = 'snet-fabric-gateway'
