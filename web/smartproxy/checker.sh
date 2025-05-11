#!/bin/bash

# SmartProxy Configuration
base_url="https://ip.decodo.com/json"
username="user-sp5uwd5fih"
password="15yFvupp9fbN_zzP0D"
proxy_server="gate.decodo.com:7000"
session_duration="60"  # in minutes (1-1440)
country="de"           # two-letter country code
# city="Hamburg"         # city name (use underscores for spaces)
# state=""            # state code (for US - use us_state_name format)
# continent=""        # continent code (eu, na, as, sa, af, oc)
# asn=""              # ASN number

# Session prefix (p = persistent, r = random)
session_prefix="p"

# Define number of sessions to test
num_sessions=30

# IPQS Configuration
ipqs_api_key="740F92cS9nqqV41L0u7jfbSepB3dff08"
ipqs_base_url="https://ipqualityscore.com/api/json/ip/${ipqs_api_key}"
user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# Check for required tools
if ! command -v jq &> /dev/null; then
    echo "jq could not be found, please install it to run this script."
    exit 1
fi

# Build the authentication string based on configured parameters
build_auth_string() {
    local session_name=$1
    local auth_string="${username}"
    
    # Add location parameters (in priority order)
    if [[ -n "$continent" ]]; then
        auth_string="${auth_string}-continent-${continent}"
    elif [[ -n "$country" ]]; then
        auth_string="${auth_string}-country-${country}"
        
        if [[ -n "$state" ]]; then
            auth_string="${auth_string}-state-${state}"
        elif [[ -n "$city" ]]; then
            auth_string="${auth_string}-city-${city}"
        fi
    fi
    
    # Add ASN if specified (cannot be combined with city)
    if [[ -n "$asn" && -z "$city" ]]; then
        auth_string="${auth_string}-asn-${asn}"
    fi
    
    # Add session parameters
    auth_string="${auth_string}-session-${session_name}"
    auth_string="${auth_string}-sessionduration-${session_duration}"
    
    echo "${auth_string}:${password}"
}

# Initialize arrays and associative array for proxy links
declare -a ip_list
declare -a city_list
declare -a country_list
declare -A proxy_links
declare -A session_to_ip
declare -A fraud_scores
declare -a clean_ips

echo "====================================== 🚀🚀🚀"
echo "Decodo SmartProxy IP Checker"
echo "======================================"
echo "Proxy server: $proxy_server"
if [[ -n "$city" ]]; then
    echo "Location: $city, $country"
else
    echo "Location: $country"
fi
echo "Session duration: $session_duration minutes"
echo "======================================"

echo "Phase 1: Collecting IPs from SmartProxy..."
# Loop through session names
for i in $(seq 1 $num_sessions)
do
    session="${session_prefix}$i"
    auth_string=$(build_auth_string "$session")
    
    echo -n "Testing session: ${session}... "
    response=$(curl -s -U "${auth_string}" -x "${proxy_server}" "${base_url}")

    if [ $? -eq 0 ]; then
        ip=$(echo $response | jq -r '.proxy.ip')
        city=$(echo $response | jq -r '.city.name')
        country_code=$(echo $response | jq -r '.country.code')
        country_name=$(echo $response | jq -r '.country.name')
        
        if [ "$ip" != "null" ]; then
            # Check if this IP is already in our list
            duplicate=false
            for existing_ip in "${ip_list[@]}"; do
                if [[ "$existing_ip" == "$ip" ]]; then
                    duplicate=true
                    echo "DUPLICATE IP: $ip"
                    break
                fi
            done
            
            if ! $duplicate; then
                ip_list+=("$ip")
                city_list+=("$city")
                country_list+=("$country_name")
                # Store the proxy details and session name
                clean_cmd=$(echo "${auth_string}" | sed 's/"//g')
                proxy_links["$ip"]="$clean_cmd"
                session_to_ip["$session"]="$ip"
                echo "OK - $ip ($city)"
            fi
        else
            echo "Failed to get IP"
        fi
    else
        echo "Failed to connect"
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
            fraud_scores["$ip"]=$fraud_score
            
            # Find the index of this IP in ip_list to get corresponding city and country
            for i in "${!ip_list[@]}"; do
                if [[ "${ip_list[$i]}" = "${ip}" ]]; then
                    city="${city_list[$i]}"
                    country="${country_list[$i]}"
                    break
                fi
            done
            
            # Find session names associated with this IP
            sessions_with_ip=""
            for session in "${!session_to_ip[@]}"; do
                if [[ "${session_to_ip[$session]}" == "$ip" ]]; then
                    if [[ -z "$sessions_with_ip" ]]; then
                        sessions_with_ip="$session"
                    else
                        sessions_with_ip="$sessions_with_ip, $session"
                    fi
                fi
            done
            
            # Print minimal info with score
            printf "IP: %-45s Score: %3d - %s (Sessions: %s)\n" "$ip" "$fraud_score" "$city" "$sessions_with_ip"
            
            # If fraud score is less than 50, add to clean IPs array
            if [ "$fraud_score" -lt 50 ]; then
                clean_ips+=("$ip")
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

echo -e "\n====================================== 🚀🚀🚀"
echo "Ranked Clean IPs by Fraud Score"
echo "======================================"

# Sort and display clean IPs by fraud score
if [ ${#clean_ips[@]} -gt 0 ]; then
    # Sort clean_ips by fraud_score (low to high)
    IFS=$'\n' sorted_ips=($(
        for ip in "${clean_ips[@]}"; do
            echo "$ip ${fraud_scores[$ip]}"
        done | sort -k2n | awk '{print $1}'
    ))
    unset IFS
    
    # Display sorted clean IPs
    for ip in "${sorted_ips[@]}"; do
        score=${fraud_scores[$ip]}
        
        # Find session for this IP
        session=""
        for s in "${!session_to_ip[@]}"; do
            if [[ "${session_to_ip[$s]}" == "$ip" ]]; then
                session=$s
                break
            fi
        done
        
        # Find city for this IP
        city=""
        for i in "${!ip_list[@]}"; do
            if [[ "${ip_list[$i]}" = "${ip}" ]]; then
                city="${city_list[$i]}"
                break
            fi
        done
        
        # Get proxy link
        link="${proxy_links[$ip]}"
        
        # Print with emojis based on score
        if [ "$score" -eq 0 ]; then
            emoji="✅✅✅"
        elif [ "$score" -lt 20 ]; then
            emoji="✅✅"
        elif [ "$score" -lt 40 ]; then
            emoji="✅"
        else
            emoji="⚠️"
        fi
        
        echo "$emoji Score: $score - IP: $ip ($city, Session: $session)"
        echo "socks5h://$link@gate.decodo.com:7000"
    done
    
    # Print the final best link
    if [ ${#sorted_ips[@]} -gt 0 ]; then
        best_ip=${sorted_ips[0]}
        best_link="${proxy_links[$best_ip]}"
        echo -e "\n====================================== 🚀🚀🚀"
        echo "Best Proxy Connection:"
        echo "======================================"
        echo "socks5h://$best_link@gate.decodo.com:7000"
    fi
else
    echo "No clean IPs found (score < 50)"
fi 