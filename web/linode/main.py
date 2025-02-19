import requests
import json
import time
from typing import Dict, Optional, List
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import aiohttp
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class IPQualityResult:
    ip: str
    difficulty: str
    quality_level: str
    response_time: float
    error: Optional[str] = None

class ChatGPTIPTester:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://chat.openai.com/backend-api/sentinel/chat-requirements"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _analyze_difficulty(self, difficulty: str) -> str:
        """Analyze the difficulty level from the hex string."""
        if not difficulty or difficulty == 'N/A':
            return 'Unknown'
            
        clean_difficulty = difficulty.replace('0x', '').lstrip('0')
        hex_length = len(clean_difficulty)
        
        if hex_length <= 2:
            return 'High Risk'
        elif hex_length == 3:
            return 'Medium Risk'
        elif hex_length == 4:
            return 'Good'
        else:
            return 'Excellent'

    async def test_single_ip_async(self, session: aiohttp.ClientSession, proxy: str) -> IPQualityResult:
        """Test a single IP using async approach."""
        start_time = time.time()
        try:
            proxy_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            async with session.get(
                self.base_url,
                headers=self.headers,
                proxy=proxy_dict['http'],
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    difficulty = data.get('proofofwork', {}).get('difficulty', 'N/A')
                    quality_level = self._analyze_difficulty(difficulty)
                    return IPQualityResult(
                        ip=proxy,
                        difficulty=difficulty,
                        quality_level=quality_level,
                        response_time=time.time() - start_time
                    )
                else:
                    return IPQualityResult(
                        ip=proxy,
                        difficulty='N/A',
                        quality_level='Error',
                        response_time=time.time() - start_time,
                        error=f'HTTP {response.status}'
                    )
        except Exception as e:
            return IPQualityResult(
                ip=proxy,
                difficulty='N/A',
                quality_level='Error',
                response_time=time.time() - start_time,
                error=str(e)
            )

    async def test_multiple_ips_async(self, proxies: List[str]) -> List[IPQualityResult]:
        """Test multiple IPs concurrently using async approach."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.test_single_ip_async(session, proxy) for proxy in proxies]
            results = await asyncio.gather(*tasks)
            return results

    def test_ips(self, proxies: List[str]) -> List[IPQualityResult]:
        """Main method to test multiple IPs."""
        return asyncio.run(self.test_multiple_ips_async(proxies))

def save_results(results: List[IPQualityResult], output_file: str = 'ip_quality_results.json'):
    """Save results to a JSON file."""
    output = [{
        'ip': r.ip,
        'difficulty': r.difficulty,
        'quality_level': r.quality_level,
        'response_time': r.response_time,
        'error': r.error
    } for r in results]
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    logging.info(f"Results saved to {output_file}")

def main():
    # Example access token (replace with your actual token)
    access_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSJdLCJjbGllbnRfaWQiOiJhcHBfWDh6WTZ2VzJwUTl0UjNkRTduSzFqTDVnSCIsImV4cCI6MTczOTc4MDM2NywiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9hdXRoIjp7InVzZXJfaWQiOiJ1c2VyLURBdE1SZERGNGpDV3JocnpyUEJMWTdaViJ9LCJodHRwczovL2FwaS5vcGVuYWkuY29tL3Byb2ZpbGUiOnsiZW1haWwiOiJqYXI3MTFyZWRAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJpYXQiOjE3Mzg5MTYzNjYsImlzcyI6Imh0dHBzOi8vYXV0aC5vcGVuYWkuY29tIiwianRpIjoiNDA2ZDE3OGYtOTQ2Mi00NDAxLWE4ODAtMmJkNGJkNWNhZGM3IiwibmJmIjoxNzM4OTE2MzY2LCJwd2RfYXV0aF90aW1lIjoxNzM4OTE2MzY1MjE2LCJzY3AiOlsib3BlbmlkIiwiZW1haWwiLCJwcm9maWxlIiwib2ZmbGluZV9hY2Nlc3MiLCJtb2RlbC5yZXF1ZXN0IiwibW9kZWwucmVhZCIsIm9yZ2FuaXphdGlvbi5yZWFkIiwib3JnYW5pemF0aW9uLndyaXRlIl0sInNlc3Npb25faWQiOiJhdXRoc2Vzc19pWHVqc2FJSlNIMU1rUU5walhGc3YxM1MiLCJzdWIiOiJnb29nbGUtb2F1dGgyfDEwNDk2MTUzNjEyMDgxMDk0MTE4MCJ9.Iy-f0Nh5Cu3Iku5pP3YFtIe9b5rNI4B7k1unf2uC-lcJMiIferx8wvZyKWljcy9larH0T9vGToaMk4OvP7EnvUVHpZQU94ecI5vPZFfR5NfWGxTEs6o2tyQnK1GoRjZfcfN0w9GtxmuI5aHtOesmGlvU31dWpesD-h1qokSE0P7iYx4d7EiwFRr59u09bVJn4QF5RXZaZ5OXvKuyq2mRS_BpPYKPV_Lao6MeIhuGHJJr2xuUjRE7LgpPUYxXk9kzm99Bvlg8hdBbiH4IwWVNMgyjl96UP6YKKs8SQIGm8F4iEGsZ06VTgMeHp3AWac4LjRk6z2nBreQuYGmT3b2P82iljyTkVrOsXHF8CYxxXpwgmIhoWQlBznp3LIiftgRsVEEx0tEuo8mZU8KGeTkE5PD48StevZHkNvK8ar7XhvyswjGgjExpH5oqRrXkolgC-5LP31o0trZX4qP_ILbfd78S2H9-7CL1yp0s73-pKL_fZH09Ycrfa6z9LVC4r6p6HmJJF-i7mn5SsNyB0KelNBkL0askjpVd_xWHkVf3zwRoJTMDmD3dH98KPUmvh8jO8djImZsQWBFntdPbn2ni8dOBp9iey_AcXcHcWqoXz-M3YagOYtJwAIBkOYElhZR96MkF_1C-npzW8-N0y_pFYHgc9100EZ7pO2B8RAsIQgw"

    # Example list of proxies to test (replace with your actual proxy list)
    proxies = [
        "1.2.3.4:8080",
        "5.6.7.8:3128",
        # Add more proxies here
    ]

    tester = ChatGPTIPTester(access_token)
    logging.info(f"Starting IP quality test for {len(proxies)} proxies...")
    
    results = tester.test_ips(proxies)
    
    # Print results
    for result in results:
        if result.error:
            logging.warning(f"IP {result.ip}: Error - {result.error}")
        else:
            logging.info(f"IP {result.ip}: Quality={result.quality_level}, Difficulty={result.difficulty}, Time={result.response_time:.2f}s")
    
    # Save results to file
    save_results(results)

if __name__ == "__main__":
    main()
