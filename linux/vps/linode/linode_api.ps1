# adc11bb37cb79693d9beacdd803605619d024c686a779e50895b3e30881df1c5
# 778dbc32c7d2e7e75c68a54053011577edc9fef6e811f30233a98eb38ce8e772                      
# 4f992316ba02d7f0b8f71704c16a8e853477f1ad943508cc2de58c525b473d57
# e5a9dadb3e13d693b0eeb31f62b82155a15bcabc07e008f0cf1bb3ad9201df50
# Define headers and proxy settings for the account
$Headers = @{
    "Authorization" = "Bearer e5a9dadb3e13d693b0eeb31f62b82155a15bcabc07e008f0cf1bb3ad9201df50"
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
$LinodeIds = @("61857756", "61857931")
foreach ($LinodeId in $LinodeIds) {
    $UriReboot = "https://api.linode.com/v4/linode/instances/$LinodeId/reboot"
    Invoke-WebRequest -Uri $UriReboot -Method Post -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | Out-Null
    Write-Output "Reboot request sent for Linode ID: $LinodeId."
}

# List Linode Types
Invoke-WebRequest -Uri "https://api.linode.com/v4/linode/regions" -Headers $Headers -Proxy $Proxy -ProxyUseDefaultCredentials | ConvertFrom-Json | ConvertTo-Json

# AbbassRenay——bW0YjYZ!43zNTHGpjNC——e5a9dadb3e13d693b0eeb31f62b82155a15bcabc07e008f0cf1bb3ad9201df50


# A0D18D00-527F-41AD-AF8A0608C6C310B3
# 46576C38-2305-48A3-8DA858BA12B01C1B