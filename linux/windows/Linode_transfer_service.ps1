# Define headers and proxy settings for the source account
$Headers = @{
    "Authorization" = "Bearer adc11bb37cb79693d9beacdd803605619d024c686a779e50895b3e30881df1c5"  # Replace with your actual Linode API token
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
    "Authorization" = "Bearer 778dbc32c7d2e7e75c68a54053011577edc9fef6e811f30233a98eb38ce8e772"  
    "Content-type" = "application/json"
}

$Proxy = "http://127.0.0.1:7890"  # Adjust this if your proxy settings differ

# Step 1: Accept the Service Transfer using the provided token
$ServiceTransferToken = "C71A6193-A07B-4672-B61C845403A2C807"  # Replace with the actual service transfer token

# Execute the API request to accept the transfer
$AcceptTransferResponse = Invoke-WebRequest `
    -Uri "https://api.linode.com/v4/account/service-transfers/$ServiceTransferToken/accept" `
    -Method Post `
    -Headers $Headers `
    -Proxy $Proxy `
    -ProxyUseDefaultCredentials | ConvertFrom-Json

# Output the response to confirm the transfer acceptance
Write-Output "Service Transfer Response: $AcceptTransferResponse"
