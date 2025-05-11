#!/bin/bash
# IP Quality Score Checker
# Usage: 
#   ./check_ip.sh <ip_address> [threshold]
#   ./check_ip.sh -p <country_code> <session_name> [threshold]
#   ./check_ip.sh -p <country_code> -c <city_name> <session_name> [threshold]
# If no IP is provided, it will check the current public IP

# IPQS Configuration
ipqs_api_key="740F92cS9nqqV41L0u7jfbSepB3dff08"
ipqs_base_url="https://ipqualityscore.com/api/json/ip/${ipqs_api_key}"
user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# SmartProxy Configuration
username="user-sp5uwd5fih"
password="15yFvupp9fbN_zzP0D"
proxy_server="gate.decodo.com:7000"
session_duration="60"  # in minutes (1-1440)

# Default threshold (IP is considered clean if fraud_score is below this value)
threshold=50
use_proxy=false
proxy_country=""
proxy_session=""
proxy_city=""
proxy_state=""
proxy_continent=""
proxy_asn=""

# Parse arguments
if [[ "$1" == "-p" || "$1" == "--proxy" ]]; then
    use_proxy=true
    proxy_country="$2"
    
    # Check for city option
    if [[ "$3" == "-c" || "$3" == "--city" ]]; then
        proxy_city="${4//[ ]/_}"  # Replace spaces with underscores
        proxy_session="$5"
        # If threshold is provided as 6th argument
        if [[ -n "$6" ]]; then
            threshold=$6
        fi
    # Check for state option
    elif [[ "$3" == "-s" || "$3" == "--state" ]]; then
        proxy_state="us_${4//[ ]/_}"  # US state format: us_state_name
        proxy_session="$5"
        # If threshold is provided as 6th argument
        if [[ -n "$6" ]]; then
            threshold=$6
        fi
    # Check for continent option
    elif [[ "$3" == "--continent" ]]; then
        proxy_continent="$4"
        proxy_session="$5"
        # If threshold is provided as 6th argument
        if [[ -n "$6" ]]; then
            threshold=$6
        fi
    # Check for ASN option
    elif [[ "$3" == "--asn" ]]; then
        proxy_asn="$4"
        proxy_session="$5"
        # If threshold is provided as 6th argument
        if [[ -n "$6" ]]; then
            threshold=$6
        fi
    else
        # Standard country + session
        proxy_session="$3"
        # If threshold is provided as 4th argument
        if [[ -n "$4" ]]; then
            threshold=$4
        fi
    fi
    
    # If no session name is provided, generate one
    if [[ -z "$proxy_session" ]]; then
        proxy_session="p$(date +%s)"
        echo "No session name provided, using auto-generated: $proxy_session"
    fi
else
    # Non-proxy mode
    if [[ -n "$2" ]]; then
        threshold=$2
    fi
fi

# Build the authentication string based on configured parameters
build_auth_string() {
    local auth_string="${username}"
    
    # Add location parameters (in priority order)
    if [[ -n "$proxy_continent" ]]; then
        auth_string="${auth_string}-continent-${proxy_continent}"
    elif [[ -n "$proxy_country" ]]; then
        auth_string="${auth_string}-country-${proxy_country}"
        
        if [[ -n "$proxy_state" ]]; then
            auth_string="${auth_string}-state-${proxy_state}"
        elif [[ -n "$proxy_city" ]]; then
            auth_string="${auth_string}-city-${proxy_city}"
        fi
    fi
    
    # Add ASN if specified (cannot be combined with city)
    if [[ -n "$proxy_asn" && -z "$proxy_city" ]]; then
        auth_string="${auth_string}-asn-${proxy_asn}"
    fi
    
    # Add session parameters
    auth_string="${auth_string}-session-${proxy_session}"
    auth_string="${auth_string}-sessionduration-${session_duration}"
    
    echo "${auth_string}:${password}"
}

# Check for required tools
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Please install jq to run this script."
    exit 1
fi

# Get IP to check
if $use_proxy; then
    # Build location string for display
    location_str="$proxy_country"
    if [[ -n "$proxy_city" ]]; then
        location_str="$proxy_city, $proxy_country"
    elif [[ -n "$proxy_state" ]]; then
        location_str="$proxy_state, $proxy_country"
    elif [[ -n "$proxy_continent" ]]; then
        location_str="continent: $proxy_continent"
    elif [[ -n "$proxy_asn" ]]; then
        location_str="ASN: $proxy_asn"
    fi
    
    echo "Checking IP through SmartProxy with session '$proxy_session' from $location_str..."
    auth_string=$(build_auth_string)
    
    response=$(curl -s -U "${auth_string}" -x "${proxy_server}" "https://ip.decodo.com/json")
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to connect to proxy."
        echo "Try using different session names like: p1, p2, p3..."
        exit 1
    fi
    
    ip_to_check=$(echo $response | jq -r '.proxy.ip')
    city=$(echo $response | jq -r '.city.name')
    country_name=$(echo $response | jq -r '.country.name')
    
    if [ -z "$ip_to_check" ] || [ "$ip_to_check" = "null" ]; then
        echo "Error: Failed to get IP from proxy."
        echo "Try using different session names or location parameters."
        exit 1
    fi
    
    echo "Proxy IP: $ip_to_check ($city, $country_name)"
    
    # Store the proxy command for later
    proxy_cmd="curl -U \"${auth_string}\" -x \"${proxy_server}\""
elif [ -z "$1" ]; then
    echo "No IP provided. Checking current public IP..."
    current_ip=$(curl -s https://ip.decodo.com/json | jq -r '.ip')
    if [ -z "$current_ip" ] || [ "$current_ip" = "null" ]; then
        echo "Error: Failed to get current public IP."
        exit 1
    fi
    ip_to_check=$current_ip
    echo "Current IP: $ip_to_check"
else
    ip_to_check=$1
fi

# Validate IP format (basic validation)
if [[ "$ip_to_check" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # IPv4 address
    ip_type="IPv4"
elif [[ "$ip_to_check" =~ ^[0-9a-fA-F:]+$ ]]; then
    # IPv6 address
    ip_type="IPv6"
else
    echo "Error: Invalid IP address format."
    exit 1
fi

echo "Checking $ip_type: $ip_to_check with IPQS..."
url="${ipqs_base_url}/${ip_to_check}"
response=$(curl -s "$url" \
    --get \
    --data-urlencode "strictness=3" \
    --data-urlencode "user_agent=$user_agent" \
    --data-urlencode "user_language=en-US")

if [ $? -ne 0 ]; then
    echo "Error: Failed to connect to IPQS API."
    exit 1
fi

# Parse response
success=$(echo "$response" | jq -r '.success')
if [ "$success" != "true" ]; then
    error_message=$(echo "$response" | jq -r '.message')
    echo "API Error: $error_message"
    exit 1
fi

# Extract key information
fraud_score=$(echo "$response" | jq -r '.fraud_score')
country=$(echo "$response" | jq -r '.country_code')
city=$(echo "$response" | jq -r '.city')
isp=$(echo "$response" | jq -r '.ISP')
is_proxy=$(echo "$response" | jq -r '.proxy')
is_vpn=$(echo "$response" | jq -r '.vpn')
is_tor=$(echo "$response" | jq -r '.tor')
is_crawler=$(echo "$response" | jq -r '.crawler')
is_bot=$(echo "$response" | jq -r '.bot_status')

# Display results
echo "------------------------------------"
echo "IP Quality Score Report"
echo "------------------------------------"
echo "IP: $ip_to_check ($ip_type)"
echo "Fraud Score: $fraud_score/100"
echo "Location: $city, $country"
echo "ISP: $isp"
echo "------------------------------------"
echo "Proxy: $([ "$is_proxy" == "true" ] && echo "YES" || echo "No")"
echo "VPN: $([ "$is_vpn" == "true" ] && echo "YES" || echo "No")"
echo "TOR: $([ "$is_tor" == "true" ] && echo "YES" || echo "No")"
echo "Crawler: $([ "$is_crawler" == "true" ] && echo "YES" || echo "No")"
echo "Bot: $([ "$is_bot" == "true" ] && echo "YES" || echo "No")"
echo "------------------------------------"

# Determine if the IP is clean based on threshold
if [ "$fraud_score" -lt "$threshold" ]; then
    echo "✅ CLEAN: Fraud score ($fraud_score) is below threshold ($threshold)"
    
    # If using proxy and IP is clean, show the proxy command
    if $use_proxy; then
        echo ""
        echo "✓ Proxy Command:"
        echo "$proxy_cmd"
        
        # Create a one-liner for easy copy/paste
        echo ""
        echo "One-liner for curl requests:"
        clean_cmd=$(echo $proxy_cmd | sed 's/"//g')
        echo "$clean_cmd \"https://example.com\""
    fi
    
    exit 0
else
    echo "❌ SUSPICIOUS: Fraud score ($fraud_score) is above threshold ($threshold)"
    
    if $use_proxy; then
        echo ""
        echo "Try another session name or location. Example commands:"
        # Generate some sample session names
        echo "./check_ip.sh -p $proxy_country p$(( ( RANDOM % 100 )  + 1 ))"
        if [[ -z "$proxy_city" && -z "$proxy_state" ]]; then
            echo "./check_ip.sh -p $proxy_country -c berlin p$(( ( RANDOM % 100 )  + 1 ))"
        fi
    fi
    
    exit 1
fi 