# 778dbc32c7d2e7e75c68a54053011577edc9fef6e811f30233a98eb38ce8e772
# adc11bb37cb79693d9beacdd803605619d024c686a779e50895b3e30881df1c5
# Define headers and proxy settings for the account
$Headers = @{
    "Authorization" = "Bearer adc11bb37cb79693d9beacdd803605619d024c686a779e50895b3e30881df1c5"
    "Content-type" = "application/json"
}
$Proxy = "http://127.0.0.1:7890"

# Fetch account details
Invoke-WebRequest -Uri "https://api.linode.com/v4/account" -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# Fetch invoices
Invoke-WebRequest -Uri "https://api.linode.com/v4/account/invoices" -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# List Linode instances
Invoke-WebRequest -Uri "https://api.linode.com/v4/linode/instances" -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# List Linode Types
Invoke-WebRequest -Uri "https://api.linode.com/v4/linode/types" -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# Create a Linode Instance in ap-south region
$BodyApSouth = @{
    "type" = "g6-nanode-1"
    "region" = "eu-central"
    "image" = "linode/debian12"
    "root_pass" = "4dwlq5!H4uA26A8"
} | ConvertTo-Json
Invoke-WebRequest -Uri "https://api.linode.com/v4/linode/instances" -Method Post -Headers $Headers -Body $BodyApSouth -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# Create a Linode Instance in Jakarta region
$BodyJakarta = @{
    "type" = "g7-premium-4"
    "region" = "id-cgk"
    "image" = "linode/debian12"
    "root_pass" = "4dwlq5!H4uA26A8"
} | ConvertTo-Json
Invoke-WebRequest -Uri "https://api.linode.com/v4/linode/instances" -Method Post -Headers $Headers -Body $BodyJakarta -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# Rebuild a Linode Instance
$RebuildBody = @{
    "image" = "linode/debian12"
    "root_pass" = "4dwlq5!H4uA26A8"
} | ConvertTo-Json
Invoke-WebRequest -Uri "https://api.linode.com/v4/linode/instances/60300928/rebuild" -Method Post -Headers $Headers -Body $RebuildBody -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# Delete a Linode Instance
$LinodeId = "62879550"
$UriDeleteInstance = "https://api.linode.com/v4/linode/instances/" + $LinodeId
Invoke-WebRequest -Uri $UriDeleteInstance -Method Delete -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# Reboot Multiple Linode Instances
$LinodeIds = @("62780260", "61857931")
foreach ($LinodeId in $LinodeIds) {
    $UriReboot = "https://api.linode.com/v4/linode/instances/$LinodeId/reboot"
    Invoke-WebRequest -Uri $UriReboot -Method Post -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | Out-Null
    Write-Output "Reboot request sent for Linode ID: $LinodeId."
}

# List Linode Types
Invoke-WebRequest -Uri "https://api.linode.com/v4/linode/regions" -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json
