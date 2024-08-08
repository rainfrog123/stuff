import json
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys

from profile_class import Profile
from fingerprint_config import FingerprintConfig, RandomUA
from user_proxy_config import UserProxyConfig

# Define the payload
payload = Profile(
    name='test7',
    group_id='4683840',
    fingerprint_config=FingerprintConfig(
        random_ua=RandomUA(ua_system_version=['Mac OS X 13']),
        fonts=['Arial']
    ),
    user_proxy_config=UserProxyConfig(proxy_soft='no_proxy')
).to_dict()

# Define the URL and headers
url = "http://local.adspower.net:50325/api/v1/user/create"
headers = {
    'Content-Type': 'application/json'
}

# Make the POST request
response = requests.post(url, headers=headers, json=payload)

# Print the response and extract the user ID
print(response.text)
response_data = response.json()
user_id = response_data['data']['id']
print(f"User ID: {user_id}")

# Open and start the browser session
ads_id = user_id
open_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={ads_id}"
close_url = f"http://local.adspower.net:50325/api/v1/browser/stop?user_id={ads_id}"

resp = requests.get(open_url).json()
print(resp)
if resp["code"] != 0:
    print(resp["msg"])
    print("Please check ads_id")
    sys.exit()

chrome_driver = resp["data"]["webdriver"]
service = Service(executable_path=chrome_driver)
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", resp["data"]["ws"]["selenium"])

driver = webdriver.Chrome(service=service, options=chrome_options)
print(driver.title)
driver.get("https://www.browserscan.net")

def highlight(element):
    driver.execute_script("arguments[0].style.border='3px solid red'", element)

try:
    # Open the signup page
    driver.get("https://dashboard.residential.rayobyte.com/user-area/#/signup")
    driver.refresh()

    # Wait for the page to load and locate input elements
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[@id='eml']"))
    )
    pwd_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[@id='pwd']"))
    )

    # Highlight and enter the email and password
    highlight(email_input)
    highlight(pwd_input)
    email_input.send_keys("crwon@edgesoftware.xyz")
    pwd_input.send_keys("sBpCMKDIUU4A")

    # Locate, highlight, and click the checkbox
    checkbox = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//*[@id='input-42']"))
    )
    highlight(checkbox)
    checkbox.click()

    # Locate, highlight, and click the signup button
    signup_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='app']/div/main/div/div[2]/div/div/form/div/div[2]/div/div/button/span"))
    )
    highlight(signup_btn)
    time.sleep(2)
    signup_btn.click()

    # Wait for and print the error message, if any
    try:
        error_message = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[@id='app']/div[2]/div/div/div[2]/div/div/div/span"))
        )
        highlight(error_message)
        print("Error message content:", error_message.text)
    except Exception as e:
        print("Manual check required")
finally:
    # Close the browser session
    requests.get(close_url)
    # driver.quit()
    pass