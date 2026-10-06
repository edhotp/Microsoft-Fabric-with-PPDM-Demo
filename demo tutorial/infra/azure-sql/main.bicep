// PIEP SSOT workshop - Azure SQL Database sumber (data sintetis)
// Microsoft Entra-only authentication, serverless General Purpose, TLS 1.2, tanpa SQL login.
targetScope = 'resourceGroup'

@description('Lokasi resource. Samakan region dengan kapasitas Fabric bila memungkinkan.')
param location string = resourceGroup().location

@description('Nama logical server (global unik, huruf kecil).')
@minLength(3)
@maxLength(63)
param serverName string

@description('Nama database sumber.')
param databaseName string = 'sqldb_piep_source_demo'

@description('Nama tampilan (UPN atau nama grup) Microsoft Entra admin server.')
param entraAdminLogin string

@description('Object ID Microsoft Entra admin (user atau grup).')
param entraAdminObjectId string

@description('Tipe principal admin.')
@allowed([
  'User'
  'Group'
  'Application'
])
param entraAdminPrincipalType string = 'User'

@description('Enabled = endpoint publik + firewall. Disabled = hanya private endpoint (lihat private-network.bicep). Gunakan Disabled bila kebijakan organisasi melarang akses publik.')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'

@description('IP publik klien yang menjalankan loader Python. Kosongkan untuk melewati aturan.')
param clientIpAddress string = ''

@description('Izinkan layanan Azure (0.0.0.0). Default false; aktifkan hanya bila koneksi Fabric memerlukannya dan sudah disetujui keamanan.')
param allowAzureServices bool = false

@description('Kapasitas maksimum vCore serverless.')
@allowed([
  1
  2
  4
])
param maxVCores int = 2

@description('Menit idle sebelum auto-pause (minimal 60). Gunakan -1 untuk menonaktifkan.')
param autoPauseDelayMinutes int = 60

param tags object = {
  workload: 'piep-ssot-workshop'
  dataClassification: 'synthetic'
  owner: 'workshop-facilitator'
}

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: serverName
  location: location
  tags: tags
  properties: {
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: publicNetworkAccess
    administrators: {
      administratorType: 'ActiveDirectory'
      azureADOnlyAuthentication: true
      login: entraAdminLogin
      sid: entraAdminObjectId
      principalType: entraAdminPrincipalType
      tenantId: tenant().tenantId
    }
  }
}

resource database 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  tags: tags
  sku: {
    name: 'GP_S_Gen5'
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: maxVCores
  }
  properties: {
    autoPauseDelay: autoPauseDelayMinutes
    minCapacity: json('0.5')
    maxSizeBytes: 34359738368
    zoneRedundant: false
    requestedBackupStorageRedundancy: 'Local'
  }
}

resource clientRule 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = if (publicNetworkAccess == 'Enabled' && !empty(clientIpAddress)) {
  parent: sqlServer
  name: 'workshop-client'
  properties: {
    startIpAddress: clientIpAddress
    endIpAddress: clientIpAddress
  }
}

resource azureServicesRule 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = if (publicNetworkAccess == 'Enabled' && allowAzureServices) {
  parent: sqlServer
  name: 'AllowAllWindowsAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output serverFqdn string = sqlServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
