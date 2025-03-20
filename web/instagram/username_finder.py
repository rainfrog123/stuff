import requests
import time
import random
import string
import itertools
import os
import json
from requests.exceptions import RequestException
from username_checker import check_instagram_username

def generate_username_variations(base_name, max_length=5):
    """
    Generate variations of a base name with maximum length
    
    Args:
        base_name (str): Base name to generate variations from
        max_length (int): Maximum length of usernames
    
    Returns:
        list: List of username variations
    """
    variations = []
    
    # Original name if it fits the length requirement
    if len(base_name) <= max_length:
        variations.append(base_name)
    
    # Truncated versions
    for i in range(1, len(base_name)):
        if len(base_name[:i]) <= max_length:
            variations.append(base_name[:i])
    
    # Common variations for jeffrey/jefr
    custom_variations = [
        "jefry", "jefri", "jefre", "jeffr", "jefr", "jfrey", 
        "jfry", "jfri", "jfre", "jfr", "jeffy", "jffy",
        "jeff", "jef", "jff", "jfey", "jfy"
    ]
    
    # Filter by length
    variations.extend([v for v in custom_variations if len(v) <= max_length])
    
    # Add numbers to short variations
    short_vars = [v for v in variations if len(v) < max_length]
    for v in short_vars:
        remaining = max_length - len(v)
        for i in range(10**(remaining)):
            num_str = str(i).zfill(remaining)
            variations.append(f"{v}{num_str}")
    
    # Remove duplicates and sort
    variations = sorted(list(set(variations)))
    
    return variations

def check_instagram_username_with_proxy(username, proxies=None, max_retries=3):
    """
    Enhanced version of check_instagram_username that supports proxies
    
    Args:
        username (str): The username to check
        proxies (dict): Dictionary of proxies to use
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
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    
    session = requests.Session()
    
    for attempt in range(max_retries):
        try:
            # Add a larger random delay to avoid rate limiting
            if attempt > 0:
                delay = 5 + random.random() * 10
                print(f"Retry attempt {attempt+1}/{max_retries}. Waiting {delay:.1f} seconds...")
                time.sleep(delay)
                
            response = session.get(url, headers=headers, proxies=proxies, timeout=15)
            
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
                    time.sleep(15 + attempt * 10)  # Longer backoff
                    continue
                return f"⚠️ Rate limited by Instagram. Try again later or use a VPN."
            else:
                return f"⚠️ Unexpected response (HTTP {response.status_code}). Try again later."
                
        except RequestException as e:
            if attempt < max_retries - 1:
                print(f"Request error: {e}. Retrying {attempt+1}/{max_retries}...")
                time.sleep(5)
                continue
            return f"⚠️ Error checking username: {e}"
    
    return "⚠️ Failed after multiple attempts. Try again later."

def load_progress(filename="username_progress.json"):
    """Load progress from a file if it exists"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            return {"checked": [], "available": [], "taken": [], "uncertain": []}
    return {"checked": [], "available": [], "taken": [], "uncertain": []}

def save_progress(progress, filename="username_progress.json"):
    """Save progress to a file"""
    with open(filename, 'w') as f:
        json.dump(progress, f)

def find_available_usernames(base_names, max_length=5, max_checks=50, batch_size=5, proxy=None):
    """
    Find available usernames based on base names with rate limit handling
    
    Args:
        base_names (list): List of base names to check variations for
        max_length (int): Maximum length of usernames
        max_checks (int): Maximum number of usernames to check
        batch_size (int): Number of usernames to check before a longer pause
        proxy (str): Optional proxy to use (format: "http://user:pass@ip:port")
    
    Returns:
        tuple: Lists of available, taken, and uncertain usernames
    """
    # Set up proxy if provided
    proxies = None
    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy
        }
        print(f"Using proxy: {proxy}")
    
    # Load progress if available
    progress = load_progress()
    checked_usernames = set(progress["checked"])
    available = progress["available"]
    taken = progress["taken"]
    uncertain = progress["uncertain"]
    
    all_variations = []
    
    # Generate variations for each base name
    for name in base_names:
        variations = generate_username_variations(name.lower(), max_length)
        all_variations.extend(variations)
    
    # Remove duplicates and sort
    all_variations = sorted(list(set(all_variations)))
    
    # Remove already checked usernames
    all_variations = [u for u in all_variations if u not in checked_usernames]
    
    # Limit the number of checks
    if len(all_variations) > max_checks:
        print(f"Generated {len(all_variations)} variations, limiting to {max_checks} checks")
        all_variations = all_variations[:max_checks]
    else:
        print(f"Checking {len(all_variations)} username variations")
    
    print(f"Already checked: {len(checked_usernames)} usernames")
    print(f"Current results: {len(available)} available, {len(taken)} taken, {len(uncertain)} uncertain")
    
    try:
        # Check each username
        for i, username in enumerate(all_variations):
            print(f"\nChecking {i+1}/{len(all_variations)}: {username}")
            
            # Add delay between requests
            if i > 0:
                # Add longer delays between batches
                if i % batch_size == 0:
                    long_delay = 30 + random.random() * 30
                    print(f"Taking a longer break after {batch_size} checks... ({long_delay:.1f} seconds)")
                    time.sleep(long_delay)
                else:
                    delay = 5 + random.random() * 5
                    print(f"Waiting {delay:.1f} seconds...")
                    time.sleep(delay)
            
            result = check_instagram_username_with_proxy(username, proxies)
            print(result)
            
            # Update progress
            checked_usernames.add(username)
            progress["checked"].append(username)
            
            if "✅" in result:
                available.append(username)
                progress["available"].append(username)
                print(f"Found available username: {username}")
            elif "❌" in result:
                taken.append(username)
                progress["taken"].append(username)
            else:
                uncertain.append(username)
                progress["uncertain"].append(username)
                
            # Show progress summary
            print(f"Progress: {len(available)} available, {len(taken)} taken, {len(uncertain)} uncertain")
            
            # Save progress after each check
            save_progress(progress)
            
            # If rate limited, take a long break
            if "rate limited" in result.lower():
                print("Rate limiting detected. Taking a long break (2-5 minutes)...")
                time.sleep(120 + random.random() * 180)
    
    except KeyboardInterrupt:
        print("\nSearch interrupted by user. Progress has been saved.")
    except Exception as e:
        print(f"\nError occurred: {e}. Progress has been saved.")
    
    return available, taken, uncertain

if __name__ == "__main__":
    # Base names to check
    base_names = ["jeffrey", "jefr"]
    
    # Ask for proxy (optional)
    use_proxy = input("Do you want to use a proxy? (y/n): ").lower() == 'y'
    proxy = None
    if use_proxy:
        proxy = input("Enter proxy (format: http://user:pass@ip:port): ")
    
    # Find available usernames
    available, taken, uncertain = find_available_usernames(
        base_names, 
        max_length=5,
        max_checks=50,  # Limit to avoid rate limiting
        batch_size=5,   # Check 5 usernames then take a longer break
        proxy=proxy
    )
    
    # Print results
    print("\n" + "="*50)
    print(f"RESULTS FOR {', '.join(base_names)} (MAX LENGTH: 5)")
    print("="*50)
    
    print(f"\n✅ AVAILABLE USERNAMES ({len(available)}):")
    for username in available:
        print(f"  - {username}")
    
    print(f"\n⚠️ UNCERTAIN RESULTS ({len(uncertain)}):")
    for username in uncertain:
        print(f"  - {username}")
    
    print(f"\n❌ TAKEN USERNAMES ({len(taken)}):")
    for username in taken[:10]:  # Show only first 10 taken usernames
        print(f"  - {username}")
    
    if len(taken) > 10:
        print(f"  ... and {len(taken) - 10} more")
    
    # Save results to file
    with open("instagram_username_results.txt", "w") as f:
        f.write(f"RESULTS FOR {', '.join(base_names)} (MAX LENGTH: 5)\n\n")
        
        f.write(f"AVAILABLE USERNAMES ({len(available)}):\n")
        for username in available:
            f.write(f"{username}\n")
        
        f.write(f"\nUNCERTAIN RESULTS ({len(uncertain)}):\n")
        for username in uncertain:
            f.write(f"{username}\n") 