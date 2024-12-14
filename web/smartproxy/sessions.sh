#!/bin/bash

# Base URL and credentials
base_url="https://ip.smartproxy.com/json"
username="user-sp5uwd5fih"
password="15yFvupp9fbN_zzP0D"
proxy_server="gate.smartproxy.com:7000"

# Additional proxy parameters
session_duration="60"  # Duration in minutes
os="ios"               # Operating System
country="us"           # Country Code

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found, please install it to run this script."
    exit 1
fi

# Initialize an array to store IPs and cities
declare -a ip_list
declare -a city_list

# Loop through sessions 1 to 20
for session in {40..60}
do
    # Construct the proxy string with the current session and additional parameters
    proxy="socks5h://${username}-session-${session}-sessionduration-${session_duration}-os-${os}-country-${country}:${password}@${proxy_server}"

    # Execute the curl command
    response=$(curl -s -x "$proxy" "$base_url")

    # Check if curl command succeeded
    if [ $? -eq 0 ]; then
        # Extract the IP and city and add them to the lists if the response is not empty
        ip=$(echo $response | jq -r '.proxy.ip')
        city=$(echo $response | jq -r '.city.name')
        if [ "$ip" != "null" ]; then
            ip_list+=("'$ip'")
            city_list+=("'$city'")  # Append city to the city list enclosed in single quotes
            echo "Session $session: Proxy = $proxy, IP = '$ip', City = '$city'"
        else
            echo "Session $session: Proxy = $proxy, failed to retrieve IP or City."
        fi
    else
        echo "Session $session: Failed to connect using the proxy."
    fi
done

# Output all IPs and Cities at the end in a list format with commas
echo "All IPs: [$(IFS=,; echo "${ip_list[*]}")]"
echo "All Cities: [$(IFS=,; echo "${city_list[*]}")]"
