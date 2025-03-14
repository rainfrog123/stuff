#!/bin/bash

# Configuration
output_file="proxy_real_ips.txt"
ip_check_url="https://api.ipify.org?format=json"
timeout_seconds=15

# Check for required tools
if ! command -v jq &> /dev/null; then
    echo "jq could not be found, please install it to run this script."
    exit 1
fi

# Clear the output file
> "$output_file"
echo "Proxy Real IP Test Results - $(date)" >> "$output_file"
echo "----------------------------------------------" >> "$output_file"

# Function to test a Trojan proxy
test_trojan_proxy() {
    local name=$1
    local server=$2
    local port=$3
    local password=$4
    local sni=$5
    
    echo "Testing $name ($server:$port)..."
    echo "Server: $server, Port: $port, SNI: $sni" >> "$output_file"
    
    # We can't directly connect to Trojan proxies with curl
    # Instead, we'll just resolve the hostname and check the IP
    ip=""
    
    # Try host command
    if command -v host &> /dev/null; then
        ip=$(timeout 5s host "$server" 2>/dev/null | grep "has address" | head -n 1 | awk '{print $NF}')
    fi
    
    # If host failed, try dig
    if [ -z "$ip" ] && command -v dig &> /dev/null; then
        ip=$(timeout 5s dig +short "$server" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1)
    fi
    
    if [ -z "$ip" ]; then
        echo "  Failed to resolve IP for $server" | tee -a "$output_file"
    else
        echo "  Resolved IP: $ip" | tee -a "$output_file"
        
        # Check IPQS score for this IP
        check_ipqs_score "$ip"
    fi
    
    echo "" >> "$output_file"
}

# Function to test a Shadowsocks proxy
test_ss_proxy() {
    local name=$1
    local server=$2
    local port=$3
    
    echo "Testing $name ($server:$port)..."
    echo "Server: $server, Port: $port" >> "$output_file"
    
    # Resolve the hostname
    ip=""
    
    # Try host command
    if command -v host &> /dev/null; then
        ip=$(timeout 5s host "$server" 2>/dev/null | grep "has address" | head -n 1 | awk '{print $NF}')
    fi
    
    # If host failed, try dig
    if [ -z "$ip" ] && command -v dig &> /dev/null; then
        ip=$(timeout 5s dig +short "$server" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1)
    fi
    
    if [ -z "$ip" ]; then
        echo "  Failed to resolve IP for $server" | tee -a "$output_file"
    else
        echo "  Resolved IP: $ip" | tee -a "$output_file"
        
        # Check IPQS score for this IP
        check_ipqs_score "$ip"
    fi
    
    echo "" >> "$output_file"
}

# Function to check IPQS score for an IP
check_ipqs_score() {
    local ip=$1
    local ipqs_api_key="740F92cS9nqqV41L0u7jfbSepB3dff08"
    local ipqs_base_url="https://ipqualityscore.com/api/json/ip/${ipqs_api_key}"
    local user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    
    # Check IP with IPQS
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
            printf "  IPQS: \033[0;32mScore: %3d\033[0m - %s, %s, %s\n" "$fraud_score" "$city" "$region" "$country" | tee -a "$output_file"
        elif [ "$fraud_score" -lt 80 ]; then
            # Yellow for medium fraud score
            printf "  IPQS: \033[0;33mScore: %3d\033[0m - %s, %s, %s\n" "$fraud_score" "$city" "$region" "$country" | tee -a "$output_file"
        else
            # Red for high fraud score
            printf "  IPQS: \033[0;31mScore: %3d\033[0m - %s, %s, %s\n" "$fraud_score" "$city" "$region" "$country" | tee -a "$output_file"
        fi
    else
        error_message=$(echo "$response" | jq -r '.message' 2>/dev/null || echo "Unknown error")
        echo "  IPQS API error: $error_message" | tee -a "$output_file"
    fi
}

echo "Testing real IPs for proxies..."
echo "----------------------------------------------"

# Test Trojan proxies
test_trojan_proxy "剩余流量：6 GB" "5eba8cd0e9e6fccc4dd2433e7a16b0b6.node.tro.node-is.green" "47507" "8f559695-10b6-435c-9480-620b743f9d49" "hk.naiun.bilibili.com"
test_trojan_proxy "套餐到期：2025-03-13" "9929c672708a51eec1069696caa945d8.node.tro.node-is.green" "47507" "8f559695-10b6-435c-9480-620b743f9d49" "hk.naiun.bilibili.com"
test_trojan_proxy "🇭🇰TJ|香港C01|直连节点" "d90dc489460b44d3380562fda94dc14b.node.tro.node-is.green" "47507" "8f559695-10b6-435c-9480-620b743f9d49" "hk.naiun.bilibili.com"
test_trojan_proxy "🇭🇰TJ|香港C01|NF解锁" "08c428263898a040484772faa09f41e3.node.tro.node-is.green" "40636" "8f559695-10b6-435c-9480-620b743f9d49" "hk.01.naiun.bilibili.com"
test_trojan_proxy "🇹🇼TJ|台湾C01|NF解锁" "38715d22fc10783767d0a395545950cf.node.tro.node-is.green" "49680" "8f559695-10b6-435c-9480-620b743f9d49" "tw.01.naiun.bilibili.com"
test_trojan_proxy "🇸🇬TJ|新加坡C01|NF解锁" "3c8221fa469809d3db134b64eb662989.node.tro.node-is.green" "43999" "8f559695-10b6-435c-9480-620b743f9d49" "sg.01.naiun.bilibili.com"
test_trojan_proxy "🇯🇵TJ|日本C01|NF解锁" "7ed3d2a950a823c344031030703e82f0.node.tro.node-is.green" "45192" "8f559695-10b6-435c-9480-620b743f9d49" "jp.01.naiun.bilibili.com"
test_trojan_proxy "🇺🇸TJ|美国C01|NF解锁" "1f7fca825c1df62cdc860027dc791154.node.tro.node-is.green" "45226" "8f559695-10b6-435c-9480-620b743f9d49" "us.01.naiun.bilibili.com"
test_trojan_proxy "🇹🇭TJ|泰国C01|IDC" "509d4089168db08bda55be7aa5b59c41.node.tro.node-is.green" "40679" "8f559695-10b6-435c-9480-620b743f9d49" "th.01.naiun.bilibili.com"
test_trojan_proxy "🇰🇷TJ|韩国C01|IDC" "a7a6810b16a0d8af0d809df04ed1b5fd.node.tro.node-is.green" "43535" "8f559695-10b6-435c-9480-620b743f9d49" "kr.01.naiun.bilibili.com"

# Test a few more important ones
test_trojan_proxy "🇭🇰TJ|香港C02|直连节点" "cc.rk1.node-is.green" "10116" "8f559695-10b6-435c-9480-620b743f9d49" "hk.naiun.bilibili.com"

# Test Shadowsocks proxies
test_ss_proxy "🇭🇰SS|香港A01|NF解锁" "a.naiun.node-is.green" "51101"
test_ss_proxy "🇭🇰SS|香港B01|NF解锁" "b.naiun.node-is.green" "51101"
test_ss_proxy "🇭🇰SS|香港01|IPLC x3" "c.naiun.node-is.green" "52101"

echo ""
echo "Testing complete! Results saved to $output_file" 