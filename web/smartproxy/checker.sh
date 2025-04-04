#!/bin/bash

# SmartProxy Configuration
base_url="https://ip.smartproxy.com/json"
username="user-sp5uwd5fih"
password="15yFvupp9fbN_zzP0D"
proxy_server="gate.smartproxy.com:7000"
session_duration="60"
os="ios"
country="fi"

# IPQS Configuration
ipqs_api_key="740F92cS9nqqV41L0u7jfbSepB3dff08"
ipqs_base_url="https://ipqualityscore.com/api/json/ip/${ipqs_api_key}"
user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# Check for required tools
if ! command -v jq &> /dev/null; then
    echo "jq could not be found, please install it to run this script."
    exit 1
fi

# Initialize arrays and associative array for proxy links
declare -a ip_list
declare -a city_list
declare -a country_list
declare -A proxy_links

echo "Phase 1: Collecting IPs from SmartProxy..."
# Loop through sessions
for session in {10..30}
do
    proxy="socks5h://${username}-session-${session}-sessionduration-${session_duration}-os-${os}-country-${country}:${password}@${proxy_server}"
    response=$(curl -s -x "$proxy" "$base_url")

    if [ $? -eq 0 ]; then
        ip=$(echo $response | jq -r '.proxy.ip')
        city=$(echo $response | jq -r '.city.name')
        country_code=$(echo $response | jq -r '.country.code')
        country_name=$(echo $response | jq -r '.country.name')
        
        if [ "$ip" != "null" ]; then
            ip_list+=("$ip")
            city_list+=("$city")
            country_list+=("$country_name")
            # Store the proxy link with its corresponding IP
            proxy_links["$ip"]="$proxy"
            printf "Session %2d: %-15s (%s, %s)\n" "$session" "$ip" "$city" "$country_name"
        else
            printf "Session %2d: Failed to connect\n" "$session"
        fi
    else
        printf "Session %2d: Failed to connect\n" "$session"
    fi
done

echo -e "\nPhase 2: Checking IPs with IPQS..."
# Check each IP with IPQS
for ip in "${ip_list[@]}"; do
    url="${ipqs_base_url}/${ip}"
    response=$(curl -s "$url" \
        --get \
        --data-urlencode "strictness=3" \
        --data-urlencode "user_agent=$user_agent" \
        --data-urlencode "user_language=en-US")

    if [ $? -eq 0 ]; then
        success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            fraud_score=$(echo "$response" | jq -r '.fraud_score')
            
            # Find the index of this IP in ip_list to get corresponding city and country
            for i in "${!ip_list[@]}"; do
                if [[ "${ip_list[$i]}" = "${ip}" ]]; then
                    city="${city_list[$i]}"
                    country="${country_list[$i]}"
                    break
                fi
            done
            
            printf "IP: %-15s Score: %3d - %s, %s\n" "$ip" "$fraud_score" "$city" "$country"
            
            # If fraud score is less than 50, print the corresponding proxy link
            if [ "$fraud_score" -lt 50 ]; then
                echo "✓ SOCKS:"
                echo "${proxy_links[$ip]}"
                echo ""
            fi
        else
            error_message=$(echo "$response" | jq -r '.message')
            echo "IP: $ip - API error: $error_message"
        fi
    else
        echo "IP: $ip - Failed to connect to IPQS API"
    fi

    # Add a small delay to respect API rate limits
    sleep 1
done 