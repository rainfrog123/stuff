#!/usr/bin/env python3
"""
Hospital Appointment Monitor - Focused on 牙周病科
Continuously monitors Chinese medical appointment system for available appointments.
Sends WeChat notifications via Server酱 when appointments become available.

Usage: python hospital_monitor.py
"""

import re
import requests
import time
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any


# =============================================================================
# CONFIGURATION
# =============================================================================

# Base URL and request parameters
BASE_URL = "http://his.mobimedical.cn/index.php"

# Focus on 牙周病科 (Periodontal Department)
TARGET_DEPARTMENT = {
    "name": "牙周病科",
    "id": "086028000A000011"
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

# Monitoring settings
SCAN_DAYS = 8  # Next 8 days from today
CHECK_INTERVAL = 30  # 30 seconds between checks

# Server酱通知配置 (WeChat Notifications)
SERVERCHAN_URL = "https://sctapi.ftqq.com/SCT282278TOxQRSjkfr6zTL0r7gQTi4wyZ.send"
NOTIFICATION_COOLDOWN = 300  # 5 minutes between notifications

# 中国标准时间 CST (UTC+8)
CST_TZ = timezone(timedelta(hours=8))


# =============================================================================
# HOSPITAL APPOINTMENT MONITOR CLASS
# =============================================================================

class HospitalMonitor:
    """Hospital Appointment Monitor focused on 牙周病科"""
    
    def __init__(self):
        """Initialize the monitor"""
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        # State tracking
        self.previous_available_dates = set()
        self.last_notification_time = 0
        
        # Log files
        self.success_log = "success.log"
        self.regular_log = "reg.log"
        
        print(f"🦷 Hospital Monitor initialized - Target: {TARGET_DEPARTMENT['name']}")
        print(f"📱 WeChat notifications: Enabled")
        print(f"⏱️ Check interval: {CHECK_INTERVAL} seconds")
        print(f"📅 Monitoring next {SCAN_DAYS} days")
    
    def generate_scan_dates(self) -> list:
        """Generate list of dates to scan (next SCAN_DAYS from today)"""
        start = datetime.now()
        dates = []
        for i in range(SCAN_DAYS):
            date = start + timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        return dates
    
    def get_department_page(self, date: str) -> str:
        """Get department page for a specific date"""
        params = REQUEST_PARAMS.copy()
        params.update({
            'deptHisId': TARGET_DEPARTMENT['id'],
            'date': date
        })
        
        referer = f"{BASE_URL}?g=Weixin&m=CloudRegisterOne&a=three&deptHisId={TARGET_DEPARTMENT['id']}&regType=0&wx=MbTXAN0k"
        headers = {'Referer': referer}
        
        try:
            response = self.session.get(BASE_URL, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"❌ HTTP Error for {date}: {e}")
            return ""
    
    def extract_doctor_info(self, html_content: str) -> list:
        """Extract doctor names and availability from HTML content"""
        available_doctors = []
        
        # Pattern to find available appointments
        pattern = r'<span>([^<]+)<!--[^>]*--><em>[^<]*</em></span><i class="collect-btn"[^>]*>.*?</i><span class="numBasic haveNum">有号</span>'
        matches = re.findall(pattern, html_content, re.DOTALL)
        
        for doctor_name in matches:
            doctor_name = doctor_name.strip()
            available_doctors.append({
                'name': doctor_name,
                'available': True
            })
        
        return available_doctors
    
    def scan_single_check(self) -> Dict[str, Any]:
        """Perform a single scan check across all dates"""
        scan_dates = self.generate_scan_dates()
        available_appointments = []
        total_slots = 0
        
        for date in scan_dates:
            html_content = self.get_department_page(date)
            if not html_content:
                continue
            
            available_doctors = self.extract_doctor_info(html_content)
            if available_doctors:
                total_slots += len(available_doctors)
                available_appointments.append({
                    'date': date,
                    'doctors': available_doctors
                })
        
        return {
            'timestamp': datetime.now(CST_TZ).strftime('%Y-%m-%d %H:%M:%S CST'),
            'department': TARGET_DEPARTMENT['name'],
            'available_appointments': available_appointments,
            'total_slots': total_slots,
            'scan_dates': scan_dates
        }
    
    def check_for_changes(self, current_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if there are new available appointments"""
        current_available_dates = set()
        changes = []
        
        # Build set of currently available dates
        for appt in current_result['available_appointments']:
            current_available_dates.add(appt['date'])
        
        # Find new available dates
        new_dates = current_available_dates - self.previous_available_dates
        
        if new_dates:
            for appt in current_result['available_appointments']:
                if appt['date'] in new_dates:
                    for doctor in appt['doctors']:
                        changes.append({
                            'date': appt['date'],
                            'doctor_name': doctor['name'],
                            'department': TARGET_DEPARTMENT['name'],
                            'change_type': 'new_availability'
                        })
        
        # Update previous state
        self.previous_available_dates = current_available_dates
        
        return changes
    
    def log_regular_check(self, result: Dict[str, Any], iteration: int):
        """Log regular check results"""
        timestamp = result['timestamp']
        total_slots = result['total_slots']
        
        # Console output
        status = f"✅ {total_slots} slots" if total_slots > 0 else "⭕ No slots"
        print(f"[{timestamp}] Check #{iteration} - {TARGET_DEPARTMENT['name']}: {status}")
        
        # File logging
        try:
            with open(self.regular_log, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] Check #{iteration} - {TARGET_DEPARTMENT['name']}: {total_slots} available slots\n")
                if result['available_appointments']:
                    for appt in result['available_appointments']:
                        doctors_str = ", ".join([d['name'] for d in appt['doctors']])
                        f.write(f"  📅 {appt['date']}: {doctors_str}\n")
        except Exception as e:
            print(f"❌ Logging error: {e}")
    
    def log_success(self, changes: List[Dict[str, Any]], full_result: Dict[str, Any]):
        """Log successful finds to success log"""
        timestamp = full_result['timestamp']
        
        try:
            with open(self.success_log, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"🎉 NEW APPOINTMENTS FOUND!\n")
                f.write(f"Time: {timestamp}\n")
                f.write(f"Department: {TARGET_DEPARTMENT['name']}\n")
                f.write(f"New available slots: {len(changes)}\n")
                f.write(f"{'='*60}\n")
                
                for change in changes:
                    f.write(f"📅 Date: {change['date']}\n")
                    f.write(f"👨‍⚕️ Doctor: {change['doctor_name']}\n")
                    f.write(f"🏥 Department: {change['department']}\n")
                    f.write(f"-" * 40 + "\n")
                
                f.write(f"\nFull scan result:\n")
                f.write(f"Total current slots: {full_result['total_slots']}\n")
                for appt in full_result['available_appointments']:
                    doctors_str = ", ".join([d['name'] for d in appt['doctors']])
                    f.write(f"  📅 {appt['date']}: {doctors_str}\n")
                f.write(f"\n")
        except Exception as e:
            print(f"❌ Success logging error: {e}")
    
    def send_notification(self, changes: List[Dict[str, Any]]):
        """Send WeChat notification via Server酱"""
        try:
            # Check cooldown
            current_time = time.time()
            if current_time - self.last_notification_time < NOTIFICATION_COOLDOWN:
                remaining = NOTIFICATION_COOLDOWN - (current_time - self.last_notification_time)
                print(f"📱 Notification cooldown: {remaining:.0f}s remaining")
                return
            
            # Prepare notification content
            title = f"🦷 牙周病科预约监控 - 发现{len(changes)}个新时段!"
            
            # Build message content
            desp_lines = [
                f"## 🦷 牙周病科预约提醒",
                f"**时间**: {datetime.now(CST_TZ).strftime('%Y-%m-%d %H:%M:%S CST')}",
                f"**新发现**: {len(changes)} 个可预约时段",
                "",
                "### 📋 可预约时段详情:"
            ]
            
            for i, change in enumerate(changes, 1):
                desp_lines.extend([
                    f"",
                    f"**时段 {i}:**",
                    f"- 📅 日期: {change['date']}",
                    f"- 👨‍⚕️ 医生: {change['doctor_name']}",
                    f"- 🏥 科室: {change['department']}",
                    f"- 💰 费用: 挂号费 + 服务费2元"
                ])
            
            desp_lines.extend([
                "",
                "---",
                f"💡 **提醒**: 请尽快登录医院预约系统进行预约！",
                f"🔗 **监控日志**: {self.success_log}"
            ])
            
            desp = "\n".join(desp_lines)
            
            # Send notification
            notification_data = {
                "title": title,
                "desp": desp,
                "short": f"牙周病科发现{len(changes)}个时段 - {changes[0]['date']}",
                "noip": "1"
            }
            
            print(f"📱 Sending WeChat notification...")
            response = requests.post(SERVERCHAN_URL, data=notification_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errno") == 0:
                    pushid = result.get("data", {}).get("pushid", "N/A")
                    print(f"✅ WeChat notification sent! PushID: {pushid}")
                    self.last_notification_time = current_time
                else:
                    print(f"❌ Server酱 error: {result.get('message', 'Unknown')}")
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Notification failed: {e}")
    
    def notify_user(self, changes: List[Dict[str, Any]], full_result: Dict[str, Any]):
        """Notify user about new appointments"""
        timestamp = full_result['timestamp']
        
        print(f"\n🎉 NEW APPOINTMENTS FOUND! 🎉")
        print(f"Time: {timestamp}")
        print(f"Department: {TARGET_DEPARTMENT['name']}")
        print(f"Found {len(changes)} new available slot(s):")
        
        for i, change in enumerate(changes, 1):
            print(f"  Slot {i}:")
            print(f"    📅 Date: {change['date']}")
            print(f"    👨‍⚕️ Doctor: {change['doctor_name']}")
            print(f"    🏥 Department: {change['department']}")
        
        print(f"📋 Details logged to: {self.success_log}")
        print("="*60)
        
        # Send WeChat notification
        self.send_notification(changes)
        
        # Try system notification
        try:
            doctors_list = ", ".join([c['doctor_name'] for c in changes])
            os.system(f'notify-send "🦷 牙周病科预约" "{len(changes)}个新时段: {doctors_list}"')
        except:
            pass
    
    def run_monitor(self):
        """Main monitoring loop"""
        print(f"\n🦷 Starting 牙周病科 appointment monitor...")
        print(f"📋 Success logging to: {self.success_log}")
        print(f"📝 Regular logging to: {self.regular_log}")
        print(f"⏰ Check interval: {CHECK_INTERVAL} seconds")
        print(f"📅 Monitoring next {SCAN_DAYS} days from today")
        print(f"📱 WeChat notifications: Enabled (5min cooldown)")
        print("="*60)
        
        # Initialize log files
        start_time = datetime.now(CST_TZ).strftime('%Y-%m-%d %H:%M:%S CST')
        for log_file in [self.success_log, self.regular_log]:
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n\n🦷 牙周病科 Monitor started at: {start_time}\n")
            except Exception as e:
                print(f"❌ Log init error: {e}")
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                
                # Perform scan
                result = self.scan_single_check()
                
                # Log regular check
                self.log_regular_check(result, iteration)
                
                # Check for changes (new appointments)
                changes = self.check_for_changes(result)
                
                if changes:
                    # Log success and notify
                    self.log_success(changes, result)
                    self.notify_user(changes, result)
                
                # Wait before next check
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print(f"\n🛑 Monitor stopped by user")
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                print(f"⏳ Continuing in {CHECK_INTERVAL} seconds...")
                time.sleep(CHECK_INTERVAL)
        
        print(f"🦷 牙周病科 Monitor stopped")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function"""
    with HospitalMonitor() as monitor:
        monitor.run_monitor()


if __name__ == "__main__":
    main() 