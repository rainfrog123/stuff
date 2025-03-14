#!/bin/bash

# IPQS Configuration
ipqs_api_key="740F92cS9nqqV41L0u7jfbSepB3dff08"
ipqs_base_url="https://ipqualityscore.com/api/json/ip/${ipqs_api_key}"
user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# Output file
output_file="proxy_results.txt"

# Check for required tools
if ! command -v jq &> /dev/null; then
    echo "jq could not be found, please install it to run this script."
    exit 1
fi

# Array of servers to check
declare -a servers=(
    # Trojan servers
    "5eba8cd0e9e6fccc4dd2433e7a16b0b6.node.tro.node-is.green"
    "9929c672708a51eec1069696caa945d8.node.tro.node-is.green"
    "d90dc489460b44d3380562fda94dc14b.node.tro.node-is.green"
    "08c428263898a040484772faa09f41e3.node.tro.node-is.green"
    "38715d22fc10783767d0a395545950cf.node.tro.node-is.green"
    "3c8221fa469809d3db134b64eb662989.node.tro.node-is.green"
    "7ed3d2a950a823c344031030703e82f0.node.tro.node-is.green"
    "1f7fca825c1df62cdc860027dc791154.node.tro.node-is.green"
    "509d4089168db08bda55be7aa5b59c41.node.tro.node-is.green"
    "a7a6810b16a0d8af0d809df04ed1b5fd.node.tro.node-is.green"
    "47f4c4ead7dd1d68797677427c9181f1.node.tro.node-is.green"
    "36fb551009c983bdad7ad934d18de4da.node.tro.node-is.green"
    "74487aec540d8d3e604ec41e00025e85.node.tro.node-is.green"
    "3564c5d34ab3f374c684c27a9887b575.node.tro.node-is.green"
    "9460fbd711873066c1c3e4c6c94e193a.node.tro.node-is.green"
    "b4152528c8f4ad7f554efcfd408fc91c.node.tro.node-is.green"
    "4b8b5242711645d669a65383a787d94c.node.tro.node-is.green"
    "c2777732cefd32a526ba792b333c4cd5.node.tro.node-is.green"
    "9c89b5ec2a69ae61833be56d92bfe67c.node.tro.node-is.green"
    "ec30bf708fcbad82996e9bbcfc70fa9a.node.tro.node-is.green"
    "2b3d2196384d49da0adb50c7dc47f70f.node.tro.node-is.green"
    "577483369b414e8dd6dc660179132445.node.tro.node-is.green"
    "75230ccf0fcc7db191bd4d37c4af1363.node.tro.node-is.green"
    "b08e80903376f8a35686e3c8d5fe9cef.node.tro.node-is.green"
    "bf49af63198541636a6c7f8bb489ffda.node.tro.node-is.green"
    "689ebcbe166b3411f7003a0c7fb4d16a.node.tro.node-is.green"
    "cc.rk1.node-is.green"
    # Shadowsocks servers
    "a.naiun.node-is.green"
    "b.naiun.node-is.green"
    "c.naiun.node-is.green"
)

echo "Testing IPQS fraud scores for proxy servers..."
echo "----------------------------------------------"
echo "Results will be saved to $output_file"

# Clear the output file
> "$output_file"
echo "Proxy Server IPQS Test Results - $(date)" >> "$output_file"
echo "----------------------------------------------" >> "$output_file"

# Counter for progress
total=${#servers[@]}
current=0

# Check each server
for server in "${servers[@]}"; do
    ((current++))
    echo -n "[$current/$total] Server: $server - "
    
    # Try to resolve hostname to IP using multiple methods
    ip=""
    
    # Try host command
    if command -v host &> /dev/null; then
        ip=$(timeout 5s host "$server" 2>/dev/null | grep "has address" | head -n 1 | awk '{print $NF}')
    fi
    
    # If host failed, try dig
    if [ -z "$ip" ] && command -v dig &> /dev/null; then
        ip=$(timeout 5s dig +short "$server" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1)
    fi
    
    # If dig failed, try nslookup
    if [ -z "$ip" ] && command -v nslookup &> /dev/null; then
        ip=$(timeout 5s nslookup "$server" 2>/dev/null | grep -A1 "Name:" | grep "Address:" | head -n 1 | awk '{print $NF}')
    fi
    
    # If all DNS resolution methods failed, try a direct ping to get IP
    if [ -z "$ip" ] && command -v ping &> /dev/null; then
        ip=$(timeout 5s ping -c 1 "$server" 2>/dev/null | head -n 1 | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
    fi
    
    if [ -z "$ip" ]; then
        echo "Failed to resolve IP"
        echo "Server: $server - Failed to resolve IP" >> "$output_file"
        continue
    fi
    
    echo -n "IP: $ip - "
    
    # Check IP with IPQS with timeout
    url="${ipqs_base_url}/${ip}"
    response=$(timeout 10s curl -s "$url" \
        --get \
        --data-urlencode "strictness=3" \
        --data-urlencode "user_agent=$user_agent" \
        --data-urlencode "user_language=en-US" || echo '{"success":false,"message":"Request timed out"}')

    success=$(echo "$response" | jq -r '.success' 2>/dev/null || echo "false")
    if [ "$success" = "true" ]; then
        fraud_score=$(echo "$response" | jq -r '.fraud_score')
        country=$(echo "$response" | jq -r '.country_code')
        region=$(echo "$response" | jq -r '.region')
        city=$(echo "$response" | jq -r '.city')
        
        # Print result with color based on fraud score
        if [ "$fraud_score" -lt 50 ]; then
            # Green for low fraud score
            printf "\033[0;32mScore: %3d\033[0m - %s, %s, %s\n" "$fraud_score" "$city" "$region" "$country"
            # Save to file
            printf "Server: %-60s IP: %-15s Score: %3d - %s, %s, %s [GOOD]\n" "$server" "$ip" "$fraud_score" "$city" "$region" "$country" >> "$output_file"
        elif [ "$fraud_score" -lt 80 ]; then
            # Yellow for medium fraud score
            printf "\033[0;33mScore: %3d\033[0m - %s, %s, %s\n" "$fraud_score" "$city" "$region" "$country"
            # Save to file
            printf "Server: %-60s IP: %-15s Score: %3d - %s, %s, %s [MEDIUM]\n" "$server" "$ip" "$fraud_score" "$city" "$region" "$country" >> "$output_file"
        else
            # Red for high fraud score
            printf "\033[0;31mScore: %3d\033[0m - %s, %s, %s\n" "$fraud_score" "$city" "$region" "$country"
            # Save to file
            printf "Server: %-60s IP: %-15s Score: %3d - %s, %s, %s [BAD]\n" "$server" "$ip" "$fraud_score" "$city" "$region" "$country" >> "$output_file"
        fi
    else
        error_message=$(echo "$response" | jq -r '.message' 2>/dev/null || echo "Unknown error")
        echo "API error: $error_message"
        echo "Server: $server - IP: $ip - API error: $error_message" >> "$output_file"
    fi

    # Add a small delay to respect API rate limits
    sleep 1
done

echo ""
echo "Testing complete! Results saved to $output_file"
echo "Summary of good proxies (fraud score < 50):"
grep "\[GOOD\]" "$output_file" || echo "No good proxies found." 