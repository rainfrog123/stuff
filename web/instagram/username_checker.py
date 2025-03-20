import requests
import time
import random
from requests.exceptions import RequestException

def check_instagram_username(username, max_retries=3):
    """
    Check if an Instagram username is available
    
    Args:
        username (str): The username to check
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        str: Status message indicating if username is available
    """
    # Instagram URL
    url = f"https://www.instagram.com/{username}/"
    
    # Use a realistic user agent to avoid detection
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    for attempt in range(max_retries):
        try:
            # Add a small random delay to avoid rate limiting
            if attempt > 0:
                time.sleep(2 + random.random() * 3)
                
            response = requests.get(url, headers=headers, timeout=10)
            
            # Check response status
            if response.status_code == 404:
                return f"✅ Username '{username}' is available!"
            elif response.status_code == 200:
                # Check if the response contains indicators of a profile page
                if '"@type":"ProfilePage"' in response.text or f'"username":"{username}"' in response.text:
                    return f"❌ Username '{username}' is already taken."
                else:
                    # Instagram might be showing a search page instead
                    return f"⚠️ Uncertain result for '{username}' - manual check recommended."
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"Rate limited. Waiting before retry {attempt+1}/{max_retries}...")
                    time.sleep(10 + attempt * 5)  # Increasing backoff
                    continue
                return f"⚠️ Rate limited by Instagram. Try again later or use a VPN."
            else:
                return f"⚠️ Unexpected response (HTTP {response.status_code}). Try again later."
                
        except RequestException as e:
            if attempt < max_retries - 1:
                print(f"Request error: {e}. Retrying {attempt+1}/{max_retries}...")
                time.sleep(2)
                continue
            return f"⚠️ Error checking username: {e}"
    
    return "⚠️ Failed after multiple attempts. Try again later."

def check_multiple_usernames(usernames):
    """
    Check multiple usernames with delay between requests
    
    Args:
        usernames (list): List of usernames to check
    
    Returns:
        dict: Dictionary of results for each username
    """
    results = {}
    
    for i, username in enumerate(usernames):
        # Add delay between requests to avoid rate limiting
        if i > 0:
            time.sleep(3 + random.random() * 2)
            
        results[username] = check_instagram_username(username)
        print(results[username])
    
    return results

# Example Usage
if __name__ == "__main__":
    # Single username check
    username = "your_desired_username"
    print(check_instagram_username(username))
    
    # Multiple username check example
    # usernames = ["username1", "username2", "username3"]
    # check_multiple_usernames(usernames)
