# Define headers and proxy settings for the source account
$Headers = @{
    "Authorization" = "Bearer 4f992316ba02d7f0b8f71704c16a8e853477f1ad943508cc2de58c525b473d57"  # Replace with your actual Linode API token
    "Content-type" = "application/json"
}

$Proxy = "http://127.0.0.1:7890"  # Adjust this if your proxy settings differ

# Step 1: Generate a Service Transfer Token from the source account
$TransferBody = @{
    "entities" = @{
        "linodes" = @(61857931)  # Replace with the actual Linode instance ID as an integer
    }
} | ConvertTo-Json

# Execute the API request to generate the transfer token
$GenerateTokenResponse = Invoke-WebRequest `
    -Uri "https://api.linode.com/v4/account/service-transfers" `
    -Method Post `
    -Headers $Headers `
    -Body $TransferBody `
    -Proxy $Proxy `
    -ProxyUseDefaultCredentials | ConvertFrom-Json

# Retrieve the transfer token from the response
$TransferToken = $GenerateTokenResponse.token

# Output the transfer token (ensure this is securely sent to the receiving account)
Write-Output "Service Transfer Token: $TransferToken"

# 9E327FBA-0C9B-477D-8F73487B02D8256F

# Define headers and proxy settings for the receiving account
$Headers = @{
    "Authorization" = "Bearer e5a9dadb3e13d693b0eeb31f62b82155a15bcabc07e008f0cf1bb3ad9201df50"  
    "Content-type" = "application/json"
}

$Proxy = "http://127.0.0.1:7890"  # Adjust this if your proxy settings differ

# Step 1: Accept the Service Transfer using the provided token
$ServiceTransferToken = "46576C38-2305-48A3-8DA858BA12B01C1B"  # Replace with the actual service transfer token

# Execute the API request to accept the transfer
$AcceptTransferResponse = Invoke-WebRequest `
    -Uri "https://api.linode.com/v4/account/service-transfers/$ServiceTransferToken/accept" `
    -Method Post `
    -Headers $Headers `
    -Proxy $Proxy `
    -ProxyUseDefaultCredentials | ConvertFrom-Json

# Output the response to confirm the transfer acceptance
Write-Output "Service Transfer Response: $AcceptTransferResponse"
