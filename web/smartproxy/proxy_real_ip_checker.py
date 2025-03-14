#!/usr/bin/env python3

import json
import sys
import time
import socket
import socks
import requests
from urllib.parse import urlparse
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# IP checking services
IP_CHECK_URLS = [
    "https://api.ipify.org?format=json",
    "https://ifconfig.me/ip",
    "https://icanhazip.com",
    "https://ipinfo.io/json"
]

# Proxy configurations
PROXIES = [
    # Trojan proxies
    {
        "name": "剩余流量：6 GB",
        "type": "trojan",
        "server": "5eba8cd0e9e6fccc4dd2433e7a16b0b6.node.tro.node-is.green",
        "port": 47507,
        "password": "8f559695-10b6-435c-9480-620b743f9d49",
        "sni": "hk.naiun.bilibili.com"
    },
    {
        "name": "🇭🇰TJ|香港C01|直连节点",
        "type": "trojan",
        "server": "d90dc489460b44d3380562fda94dc14b.node.tro.node-is.green",
        "port": 47507,
        "password": "8f559695-10b6-435c-9480-620b743f9d49",
        "sni": "hk.naiun.bilibili.com"
    },
    {
        "name": "🇭🇰TJ|香港C02|直连节点",
        "type": "trojan",
        "server": "cc.rk1.node-is.green",
        "port": 10116,
        "password": "8f559695-10b6-435c-9480-620b743f9d49",
        "sni": "hk.naiun.bilibili.com"
    },
    # Shadowsocks proxies
    {
        "name": "🇭🇰SS|香港A01|NF解锁",
        "type": "ss",
        "server": "a.naiun.node-is.green",
        "port": 51101,
        "cipher": "chacha20-ietf-poly1305",
        "password": "8f559695-10b6-435c-9480-620b743f9d49"
    },
    {
        "name": "🇭🇰SS|香港B01|NF解锁",
        "type": "ss",
        "server": "b.naiun.node-is.green",
        "port": 51101,
        "cipher": "chacha20-ietf-poly1305",
        "password": "8f559695-10b6-435c-9480-620b743f9d49"
    }
]

def get_original_ip():
    """Get the original IP address without proxy"""
    try:
        response = requests.get(IP_CHECK_URLS[0], timeout=10)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        logger.error(f"Error getting original IP: {e}")
    return "Unknown"

def check_ip_with_ipqs(ip):
    """Check IP with IPQS API"""
    ipqs_api_key = "740F92cS9nqqV41L0u7jfbSepB3dff08"
    ipqs_base_url = f"https://ipqualityscore.com/api/json/ip/{ipqs_api_key}/{ip}"
    
    try:
        response = requests.get(
            ipqs_base_url,
            params={
                "strictness": 3,
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "user_language": "en-US"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                fraud_score = data.get("fraud_score", 0)
                country = data.get("country_code", "Unknown")
                region = data.get("region", "Unknown")
                city = data.get("city", "Unknown")
                
                score_color = "\033[0;32m"  # Green
                if fraud_score >= 80:
                    score_color = "\033[0;31m"  # Red
                elif fraud_score >= 50:
                    score_color = "\033[0;33m"  # Yellow
                
                result = f"  IPQS: {score_color}Score: {fraud_score:3d}\033[0m - {city}, {region}, {country}"
                return result, fraud_score, city, region, country
            else:
                error_message = data.get("message", "Unknown error")
                return f"  IPQS API error: {error_message}", None, None, None, None
        else:
            return f"  IPQS API error: HTTP {response.status_code}", None, None, None, None
    except Exception as e:
        return f"  IPQS API error: {str(e)}", None, None, None, None

def resolve_hostname(hostname):
    """Resolve hostname to IP address"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except Exception as e:
        logger.error(f"Error resolving hostname {hostname}: {e}")
        return None

def setup_socks_proxy(proxy_type, host, port):
    """Set up a SOCKS proxy for requests"""
    if proxy_type.lower() == "socks5":
        proxy_type = socks.SOCKS5
    elif proxy_type.lower() == "socks4":
        proxy_type = socks.SOCKS4
    else:
        proxy_type = socks.SOCKS5  # Default to SOCKS5
    
    socks.set_default_proxy(proxy_type, host, port)
    socket.socket = socks.socksocket

def check_ip_through_proxy(proxy_config):
    """Check IP through a proxy using requests with SOCKS"""
    name = proxy_config.get("name", "Unknown")
    proxy_type = proxy_config.get("type", "unknown")
    server = proxy_config.get("server", "")
    port = proxy_config.get("port", 0)
    
    print(f"Testing {name} ({server}:{port})...")
    
    # First, resolve the hostname
    ip = resolve_hostname(server)
    if not ip:
        print(f"  Failed to resolve IP for {server}")
        return
    
    print(f"  Resolved IP: {ip}")
    
    # Check IPQS score for the resolved IP
    ipqs_result, fraud_score, city, region, country = check_ip_with_ipqs(ip)
    print(ipqs_result)
    
    # For now, we can't actually connect through these proxies in this environment
    # We would need to install and configure the appropriate clients
    print("  Note: To get the real exit IP, you need to install and configure the appropriate client.")
    print(f"  For {proxy_type.upper()} proxies, you would need to install the {proxy_type} client.")
    
    # Instructions for installing clients
    if proxy_type == "trojan":
        print("  To install Trojan client: pip install trojan-python")
        print("  Example usage:")
        print(f"    trojan -c config.json  # where config.json contains server: {server}, port: {port}, etc.")
    elif proxy_type == "ss":
        print("  To install Shadowsocks client: pip install shadowsocks")
        print("  Example usage:")
        print(f"    sslocal -s {server} -p {port} -k PASSWORD -m CIPHER")

def main():
    """Main function"""
    print("Proxy Real IP Checker")
    print("--------------------")
    
    # Get original IP
    original_ip = get_original_ip()
    print(f"Your original IP: {original_ip}")
    print()
    
    # Check each proxy
    for proxy in PROXIES:
        check_ip_through_proxy(proxy)
        print()
    
    print("Note: To actually check the real exit IP of these proxies, you would need to:")
    print("1. Install the appropriate client (Trojan or Shadowsocks)")
    print("2. Configure the client with the proxy details")
    print("3. Connect through the proxy")
    print("4. Check your IP at a service like https://api.ipify.org")

if __name__ == "__main__":
    main() 