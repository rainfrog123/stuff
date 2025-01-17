import requests

# Define the IPQS API URL and API key
api_key = "740F92cS9nqqV41L0u7jfbSepB3dff08"
url_template = f"https://ipqualityscore.com/api/json/ip/{api_key}/{{}}"

# List of IP addresses to test
ip_list = ['146.70.207.194','81.94.66.233','81.94.66.233','146.70.207.194','83.188.34.189','90.226.100.42','90.226.100.42','90.226.100.42','146.70.207.194','81.94.66.233','2.249.93.174','62.20.41.218','83.188.34.189','83.188.34.189','90.226.100.42','90.226.100.42','90.226.100.42','94.234.99.47','81.235.31.167','83.188.34.189']


# Define parameters for the request with the highest strictness level
params = {
    "strictness": 3,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "user_language": "en-US"
}

# Loop through each IP and check its fraud score
for ip in ip_list:
    url = url_template.format(ip)
    response = requests.get(url, params=params)
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            fraud_score = data.get("fraud_score", "N/A")
            print(f"IP: {ip} - Fraud Score: {fraud_score}")
        else:
            print(f"IP: {ip} - API request was not successful: {data.get('message')}")
    else:
        print(f"IP: {ip} - Failed to connect to the API: {response.status_code}")
