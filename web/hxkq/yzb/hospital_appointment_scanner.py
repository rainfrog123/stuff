
#!/usr/bin/env python3
"""
Hospital Appointment Scanner - Complete Single File Implementation
Scans Chinese medical appointment system for available appointments.

Usage: python hospital_appointment_scanner.py
"""

import re
import requests
from datetime import datetime, timedelta


# =============================================================================
# CONFIGURATION
# =============================================================================

# Base URL and request parameters
BASE_URL = "http://his.mobimedical.cn/index.php"

# Department IDs
DEPARTMENTS = {
    "中医科": "086028000A000110", 
    "牙周病科": "086028000A000011"
}

# Headers for HTTP requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.61(0x18003d28) NetType/WIFI Language/en',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Cookie': 'KQjumpUrl=%22http%3A%5C%2F%5C%2Fhis.mobimedical.cn%5C%2Findex.php%3Fg%3DWeixin%26m%3DCloudRegisterOne%26a%3Dfour%26deptHisId%3D086028000A000110%26docHisId%3D1572%26doc_code%3D20106010%26regType%3D0%26wx%3DMbTXAN0k%22; PHPSESSID=gpj741if8flgq7144i4bcucrr5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Accept-Language': 'en-GB,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate'
}

# Request parameters
REQUEST_PARAMS = {
    'g': 'Weixin',
    'm': 'CloudRegisterOne', 
    'a': 'three',
    'isYH': '',
    'ImplantData': '',
    'regType': '0',
    'wx': 'MbTXAN0k'
}

# Scan settings - Dynamic date calculation
START_DATE = datetime.now().strftime("%Y-%m-%d")  # Today's date
SCAN_DAYS = 8  # Next 9 days from today


# =============================================================================
# HTTP CLIENT
# =============================================================================

class SimpleHttpClient:
    """Simplified HTTP client for hospital appointment system."""
    
    def __init__(self):
        """Initialize HTTP client with session."""
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def get_department_page(self, department_id: str, date: str) -> str:
        """
        Get department page for a specific date.
        
        Args:
            department_id: Hospital department ID
            date: Date string in YYYY-MM-DD format
            
        Returns:
            HTML content as string
        """
        # Build request parameters
        params = REQUEST_PARAMS.copy()
        params.update({
            'deptHisId': department_id,
            'date': date
        })
        
        # Build referer URL
        referer = f"{BASE_URL}?g=Weixin&m=CloudRegisterOne&a=three&deptHisId={department_id}&regType=0&wx=MbTXAN0k"
        headers = {'Referer': referer}
        
        try:
            response = self.session.get(BASE_URL, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"HTTP Error: {e}")
            return ""
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# =============================================================================
# SCANNER LOGIC
# =============================================================================

def generate_scan_dates(start_date: str, num_days: int) -> list:
    """Generate list of dates to scan."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    dates = []
    for i in range(num_days):
        date = start + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    return dates


def extract_doctor_info(html_content: str) -> list:
    """Extract doctor names and availability from HTML content."""
    available_doctors = []
    
    # Precise pattern based on actual HTML structure:
    # <span>DoctorName<!--comment--><em>level</em></span><i class="collect-btn">...</i><span class="numBasic haveNum">有号</span>
    pattern = r'<span>([^<]+)<!--[^>]*--><em>[^<]*</em></span><i class="collect-btn"[^>]*>.*?</i><span class="numBasic haveNum">有号</span>'
    
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    for doctor_name in matches:
        doctor_name = doctor_name.strip()
        available_doctors.append({
            'name': doctor_name,
            'available': True
        })
    
    return available_doctors


def scan_department(client: SimpleHttpClient, dept_name: str, dept_id: str, dates: list) -> dict:
    """Scan a department for available appointments across multiple dates."""
    print(f"\n🏥 Scanning {dept_name} ({dept_id})")
    print("=" * 50)
    
    results = {
        'department': dept_name,
        'department_id': dept_id,
        'scan_dates': dates,
        'available_appointments': [],
        'summary': {
            'total_dates_scanned': 0,
            'dates_with_availability': 0,
            'total_available_slots': 0
        }
    }
    
    for date in dates:
        print(f"📅 Scanning {date}...")
        
        # Get department page
        html_content = client.get_department_page(dept_id, date)
        if not html_content:
            print(f"  ❌ Failed to fetch data for {date}")
            continue
        
        results['summary']['total_dates_scanned'] += 1
        
        # Extract doctor information (only available doctors)
        available_doctors = extract_doctor_info(html_content)
        
        if available_doctors:
            results['summary']['dates_with_availability'] += 1
            results['summary']['total_available_slots'] += len(available_doctors)
            
            print(f"  ✅ {len(available_doctors)} available slots found:")
            for doctor in available_doctors:
                print(f"     • {doctor['name']}")
            
            results['available_appointments'].append({
                'date': date,
                'available_doctors': available_doctors
            })
        else:
            print(f"  ⭕ No available appointments")
    
    return results


def print_summary(all_results: list):
    """Print overall summary of scan results."""
    print("\n" + "=" * 60)
    print("📊 SCAN SUMMARY")
    print("=" * 60)
    
    total_slots = 0
    total_available_dates = 0
    
    for result in all_results:
        dept_name = result['department']
        summary = result['summary']
        
        print(f"\n🏥 {dept_name}:")
        print(f"   📅 Dates scanned: {summary['total_dates_scanned']}")
        print(f"   ✅ Dates with availability: {summary['dates_with_availability']}")
        print(f"   🎯 Total available slots: {summary['total_available_slots']}")
        
        total_slots += summary['total_available_slots']
        total_available_dates += summary['dates_with_availability']
    
    print(f"\n🎯 OVERALL TOTALS:")
    print(f"   📈 Total available slots: {total_slots}")
    print(f"   📅 Total dates with availability: {total_available_dates}")


def main():
    """Main scanner function."""
    print("🏥 Hospital Appointment Scanner")
    print("=" * 60)
    print(f"📅 Scanning period: {START_DATE} for {SCAN_DAYS} days")
    print(f"🔍 Looking for available appointments (有号)")
    
    # Generate scan dates
    scan_dates = generate_scan_dates(START_DATE, SCAN_DAYS)
    print(f"📋 Dates to scan: {', '.join(scan_dates)}")
    
    all_results = []
    
    # Scan each department
    with SimpleHttpClient() as client:
        for dept_name, dept_id in DEPARTMENTS.items():
            try:
                result = scan_department(client, dept_name, dept_id, scan_dates)
                all_results.append(result)
            except Exception as e:
                print(f"❌ Error scanning {dept_name}: {e}")
    
    # Print summary
    print_summary(all_results)
    
    return all_results


if __name__ == "__main__":
    results = main() 