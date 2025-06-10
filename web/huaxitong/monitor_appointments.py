#!/usr/bin/env python3
import requests
import json
import time
import os
import sys
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

class AppointmentMonitor:
    def __init__(self):
        self.url = "https://hytapiv2.cd120.com/cloud/appointment/doctorListModel/selDoctorDetailsTwo"
        self.headers = {
            "Host": "hytapiv2.cd120.com",
            "UUID": "25FEFB37-9D3D-4FA1-B7E8-81F7FB0A2FAD",
            "Mac": "Found",
            "Accept": "*/*",
            "Client-Version": "7.1.1",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB;q=1",
            "token": "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIyNzkwODA5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhIiwiaWF0IjoxNzQ5Mzc5NjE5LCJzdWIiOiJ7XCJ1c2VySWRcIjpcIjI3OTA4MFwiLFwiYWNjb3VudElkXCI6XCIyOTMzNjBcIixcInVzZXJUeXBlXCI6MCxcImFwcENvZGVcIjpcIkhYR1lBUFBcIixcImNoYW5uZWxDb2RlXCI6XCJQQVRJRU5UX0lPU1wiLFwiZGV2aWNlbnVtYmVyXCI6XCI5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhXCIsXCJkZXZpY2VUeXBlXCI6XCJBUFBcIixcImFjY291bnROb1wiOlwiMTM4ODI5ODUxODhcIixcIm5hbWVcIjpcIumZiOS6leW3nVwiLFwiZG9jdG9ySWRcIjpudWxsLFwib3JnYW5Db2RlXCI6bnVsbH0iLCJleHAiOjE3NTE5NzE2MTl9.oC6rNfjBJ-pykrsPDfkY0qORCrKHTMuBPAkwXAN3ITw***HXGYAPP",
            "accessToken": "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIyNzkwODA5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhIiwiaWF0IjoxNzQ5Mzc5NjE5LCJzdWIiOiJ7XCJ1c2VySWRcIjpcIjI3OTA4MFwiLFwiYWNjb3VudElkXCI6XCIyOTMzNjBcIixcInVzZXJUeXBlXCI6MCxcImFwcENvZGVcIjpcIkhYR1lBUFBcIixcImNoYW5uZWxDb2RlXCI6XCJQQVRJRU5UX0lPU1wiLFwiZGV2aWNlbnVtYmVyXCI6XCI5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhXCIsXCJkZXZpY2VUeXBlXCI6XCJBUFBcIixcImFjY291bnROb1wiOlwiMTM4ODI5ODUxODhcIixcIm5hbWVcIjpcIumZiOS6leW3nVwiLFwiZG9jdG9ySWRcIjpudWxsLFwib3JnYW5Db2RlXCI6bnVsbH0iLCJleHAiOjE3NTE5NzE2MTl9.oC6rNfjBJ-pykrsPDfkY0qORCrKHTMuBPAkwXAN3ITw***HXGYAPP",
            "Content-Type": "application/json",
            "User-Agent": "hua yi tong/7.1.1 (iPhone; iOS 15.7.1; Scale/3.00)",
            "Connection": "keep-alive",
            "Cookie": "acw_tc=ac11000117494466537182414e0065099ed81684c064d896c8d5bd165b0c3e"
        }
        # Base payload template (timestamp will be updated dynamically)
        self.payload_template = {
            "hospitalCode": "HID0101",
            "deptCode": "1649",
            "doctorId": "4028b881646e3d8701646e3d876301f6",
            "channelCode": "PATIENT_IOS",
            "appCode": "HXGYAPP",
            "hospitalAreaCode": "F0017",
            "tabAreaCode": "",
            "cardId": "0",
            "encrypt": "B+dltOVPkHRvQmtQWA65vA==",
            "deptCategoryCode": "6100-EBHK",
            "appointmentType": "2"
        }
        
        
        # Dynamic user agent generation data
        self.app_versions = [
            "7.0.8", "7.0.9", "7.1.0", "7.1.1", "7.1.2", "7.2.0"
        ]
        self.ios_versions = [
            "15.6.1", "15.7.0", "15.7.1", "15.7.2", "15.7.3", "15.7.4", "15.7.5", "15.7.6", "15.7.7", "15.7.8", "15.7.9", "15.8.0", "15.8.1", "15.8.2",
            "16.0.0", "16.0.1", "16.0.2", "16.0.3", "16.1.0", "16.1.1", "16.1.2", "16.2.0", "16.3.0", "16.3.1", "16.4.0", "16.4.1", "16.5.0", "16.5.1", "16.6.0", "16.6.1", "16.7.0", "16.7.1", "16.7.2"
        ]
        self.device_models = [
            "iPhone13,1", "iPhone13,2", "iPhone13,3", "iPhone13,4",  # iPhone 12 series
            "iPhone14,2", "iPhone14,3", "iPhone14,4", "iPhone14,5",  # iPhone 13 series  
            "iPhone14,7", "iPhone14,8",  # iPhone 13 mini/Pro Max
            "iPhone12,1", "iPhone12,3", "iPhone12,5", "iPhone12,8",  # iPhone 11 series
            "iPhone11,2", "iPhone11,4", "iPhone11,6", "iPhone11,8",  # iPhone XS series
        ]
        self.scale_values = ["2.00", "3.00"]
        
        # Track previous state of remaining numbers
        self.previous_remaining = {}
        self.log_file = "success.log"
        self.reg_log_file = "reg.log"
        
        # 中国标准时间 CST (UTC+8) 
        self.cst_tz = timezone(timedelta(hours=8))
        
        # Server酱通知配置
        self.serverchan_url = "https://sctapi.ftqq.com/SCT282278TOxQRSjkfr6zTL0r7gQTi4wyZ.send"
        self.last_notification_time = 0  # Track last notification timestamp
        self.notification_cooldown = 300  # 5 minutes in seconds
        
    def get_current_payload(self) -> Dict[str, Any]:
        """Generate payload with current timestamp"""
        payload = self.payload_template.copy()
        # Use current timestamp (Unix timestamp as string)
        payload["timestamp"] = str(int(time.time()))
        return payload
    
    def generate_random_user_agent(self) -> str:
        """Generate a completely random but realistic User-Agent"""
        app_version = random.choice(self.app_versions)
        device_model = random.choice(self.device_models)
        ios_version = random.choice(self.ios_versions)
        scale = random.choice(self.scale_values)
        
        return f"hua yi tong/{app_version} ({device_model}; iOS {ios_version}; Scale/{scale})"
    
    def generate_random_uuid(self) -> str:
        """Generate a completely random UUID"""
        return str(uuid.uuid4()).upper()
    
    def get_randomized_headers(self) -> Dict[str, str]:
        """Get headers with completely randomized User-Agent and UUID"""
        headers = self.headers.copy()
        # Generate completely random User-Agent
        headers["User-Agent"] = self.generate_random_user_agent()
        # Generate completely random UUID
        headers["UUID"] = self.generate_random_uuid()
        return headers
    
    def is_peak_hour(self) -> bool:
        """Check if current time is within peak monitoring windows (7:59-8:04 AM/PM 中国时间)"""
        now_cst = datetime.now(self.cst_tz)
        current_time = now_cst.time()
        
        # Define peak windows: 7:59:00 - 8:04:00 AM and PM (5 minutes each)
        morning_start = datetime.strptime("07:59:00", "%H:%M:%S").time()
        morning_end = datetime.strptime("08:04:00", "%H:%M:%S").time()
        evening_start = datetime.strptime("19:59:00", "%H:%M:%S").time()
        evening_end = datetime.strptime("20:04:00", "%H:%M:%S").time()
        
        is_morning_peak = morning_start <= current_time <= morning_end
        is_evening_peak = evening_start <= current_time <= evening_end
        
        return is_morning_peak or is_evening_peak
    
    def get_wait_time(self) -> float:
        """Get appropriate wait time based on current time"""
        if self.is_peak_hour():
            return 5.0  # 5 seconds during peak hours
        else:
            return random.uniform(20, 40)  # 20-40 seconds normally
    
    def send_request(self) -> Dict[str, Any]:
        """Send the API request and return the response"""
        try:
            # Add small random delay before request (0.5-2 seconds)
            time.sleep(random.uniform(0.5, 2.0))
            
            # Get dynamic payload and headers
            payload = self.get_current_payload()
            headers = self.get_randomized_headers()
            
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
    
    def extract_remaining_numbers(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all remainingNum entries from the response"""
        remaining_entries = []
        seen_ids = set()  # Track unique schedule IDs to avoid duplicates
        
        if not data or data.get("code") != "1":
            return remaining_entries
            
        response_data = data.get("data", {})
        
        def add_entry_if_unique(item):
            """Add entry only if we haven't seen this schedule ID before"""
            schedule_id = item.get("sysScheduleId")
            if schedule_id and schedule_id not in seen_ids:
                seen_ids.add(schedule_id)
                remaining_entries.append({
                    "id": schedule_id,
                    "scheduleDate": item.get("scheduleDate"),
                    "scheduleRange": item.get("scheduleRange", 0),
                    "remainingNum": item.get("remainingNum", 0),
                    "availableCount": item.get("availableCount", 0),
                    "deptName": item.get("deptName"),
                    "hospitalAreaName": item.get("hospitalAreaName"),
                    "dayDesc": item.get("dayDesc"),
                    "admLocation": item.get("admLocation")
                })
        
        # Check sourceItemsRespVos
        source_items = response_data.get("sourceItemsRespVos", [])
        for item in source_items:
            add_entry_if_unique(item)
        
        # Check nested sourceItems structure  
        source_items_nested = response_data.get("sourceItems", [])
        for area in source_items_nested:
            area_items = area.get("sourceItemsRespVos", [])
            for item in area_items:
                add_entry_if_unique(item)
        
        return remaining_entries
    
    def check_for_changes(self, current_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for appointments that changed from 0 to positive remaining numbers"""
        changes = []
        
        for entry in current_entries:
            entry_id = entry["id"]
            current_remaining = entry["remainingNum"]
            current_available = entry["availableCount"]
            
            # Check both remainingNum and availableCount
            for field_name, current_value in [("remainingNum", current_remaining), ("availableCount", current_available)]:
                key = f"{entry_id}_{field_name}"
                previous_value = self.previous_remaining.get(key, 0)
                
                # Detect change from 0 to positive number
                if previous_value == 0 and current_value > 0:
                    change_info = entry.copy()
                    change_info["changed_field"] = field_name
                    change_info["previous_value"] = previous_value
                    change_info["current_value"] = current_value
                    changes.append(change_info)
                
                # Update tracking
                self.previous_remaining[key] = current_value
        
        return changes
    
    def log_regular_check(self, entries: List[Dict[str, Any]], timestamp: str, iteration: int):
        """Log regular checks to reg.log"""
        with open(self.reg_log_file, "a", encoding="utf-8") as f:
            total_remaining = sum(e["remainingNum"] for e in entries)
            total_available = sum(e["availableCount"] for e in entries)
            is_peak = self.is_peak_hour()
            peak_marker = " [PEAK]" if is_peak else ""
            f.write(f"[{timestamp}] Check #{iteration}{peak_marker} - Total remaining: {total_remaining}, available: {total_available}\n")
            
            # Log details of each slot
            for entry in entries:
                f.write(f"  {entry['scheduleDate']} ({entry['dayDesc']}) - "
                       f"Remaining: {entry['remainingNum']}, Available: {entry['availableCount']} - "
                       f"{entry['deptName']} - {entry['hospitalAreaName']}\n")

    def log_success(self, changes: List[Dict[str, Any]], full_response: Dict[str, Any]):
        """Log successful detections to success.log"""
        timestamp = datetime.now(self.cst_tz).strftime("%Y-%m-%d %H:%M:%S CST")
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"APPOINTMENT AVAILABLE DETECTED - {timestamp}\n")
            f.write(f"{'='*80}\n")
            
            for change in changes:
                f.write(f"\nSlot Available:\n")
                f.write(f"  Schedule ID: {change['id']}\n")
                f.write(f"  Date: {change['scheduleDate']} ({change['dayDesc']})\n")
                f.write(f"  Department: {change['deptName']}\n")
                f.write(f"  Location: {change['admLocation']}\n")
                f.write(f"  Hospital Area: {change['hospitalAreaName']}\n")
                f.write(f"  Changed Field: {change['changed_field']}\n")
                f.write(f"  Previous Value: {change['previous_value']}\n")
                f.write(f"  Current Value: {change['current_value']}\n")
                f.write(f"  Schedule Range: {change['scheduleRange']}\n")
            
            f.write(f"\n{'='*80}\n")
    
    def notify_user(self, changes: List[Dict[str, Any]]):
        """Notify user about available appointments"""
        print(f"\n🎉 APPOINTMENT SLOTS AVAILABLE! 🎉")
        print(f"Time: {datetime.now(self.cst_tz).strftime('%Y-%m-%d %H:%M:%S CST')}")
        print(f"Found {len(changes)} new available slot(s):")
        
        for i, change in enumerate(changes, 1):
            print(f"\n  Slot {i}:")
            print(f"    📅 Date: {change['scheduleDate']} ({change['dayDesc']})")
            print(f"    🏥 Department: {change['deptName']}")
            print(f"    📍 Location: {change['admLocation']}")
            print(f"    🏢 Hospital Area: {change['hospitalAreaName']}")
            print(f"    🔄 {change['changed_field']}: {change['previous_value']} → {change['current_value']}")
        
        print(f"\n📋 Details logged to: {self.log_file}")
        print("="*60)
        
        # Send Server酱 WeChat notification
        self.send_serverchan_notification(changes)
        
        # Try to send system notification (if available)
        try:
            os.system(f'notify-send "Appointment Available" "{len(changes)} new slot(s) found for {changes[0]["deptName"]}"')
        except:
            pass  # Ignore if notify-send is not available
    
    def send_serverchan_notification(self, changes: List[Dict[str, Any]]):
        """Send WeChat notification via Server酱 (with 5-minute cooldown)"""
        try:
            # Check cooldown period
            current_time = time.time()
            time_since_last = current_time - self.last_notification_time
            
            if time_since_last < self.notification_cooldown:
                remaining_cooldown = self.notification_cooldown - time_since_last
                print(f"📱 Notification cooldown: {remaining_cooldown:.0f}s remaining (preventing spam)")
                return
            # Prepare notification content
            title = f"🎉 预约成功监控 - 发现{len(changes)}个空位!"
            
            # Build detailed message content in Markdown
            desp_lines = [
                f"## 📅 预约信息",
                f"**医生**: 戴晴晴",
                f"**科室**: 耳鼻喉眩晕专科", 
                f"**时间**: {datetime.now(self.cst_tz).strftime('%Y-%m-%d %H:%M:%S CST')}",
                f"**发现**: {len(changes)} 个可预约时段",
                "",
                "### 📋 可预约时段详情:"
            ]
            
            for i, change in enumerate(changes, 1):
                desp_lines.extend([
                    f"",
                    f"**时段 {i}:**",
                    f"- 📅 日期: {change['scheduleDate']} ({change['dayDesc']})",
                    f"- 🏥 科室: {change['deptName']}",
                    f"- 📍 地点: {change['admLocation']}",
                    f"- 🏢 院区: {change['hospitalAreaName']}",
                    f"- 🔄 变化: {change['changed_field']} {change['previous_value']} → {change['current_value']}",
                    f"- 💰 费用: 挂号费17元 + 服务费2元"
                ])
            
            desp_lines.extend([
                "",
                "---",
                f"💡 **提醒**: 请尽快登录华西医院App进行预约！",
                f"🔗 **监控日志**: {self.log_file}"
            ])
            
            desp = "\n".join(desp_lines)
            
            # Prepare notification data
            notification_data = {
                "title": title,
                "desp": desp,
                "short": f"发现{len(changes)}个预约时段 - {changes[0]['scheduleDate']}",
                "noip": "1"  # Hide IP for privacy
            }
            
            print(f"📱 Sending WeChat notification via Server酱...")
            
            # Send POST request
            response = requests.post(self.serverchan_url, data=notification_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errno") == 0:
                    pushid = result.get("data", {}).get("pushid", "N/A")
                    print(f"✅ WeChat notification sent successfully! PushID: {pushid}")
                    # Update last notification time
                    self.last_notification_time = current_time
                else:
                    print(f"❌ Server酱 error: {result.get('message', 'Unknown error')}")
            else:
                print(f"❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Failed to send WeChat notification: {e}")
    
    def run_monitor(self):
        """Main monitoring loop"""
        print(f"🔍 Starting appointment monitor...")
        print(f"📋 Success logging to: {self.log_file}")
        print(f"📝 Regular logging to: {self.reg_log_file}")
        print(f"⏰ Normal: 20-40s intervals | Peak: 5s intervals (7:59-8:04 AM/PM 中国时间)")
        print(f"🎯 Monitoring doctor: 戴晴晴 (耳鼻喉眩晕专科)")
        print(f"🛡️ Anti-detection: Dynamic timestamps, randomized intervals, rotating User-Agents")
        print(f"📱 WeChat notifications: Enabled via Server酱")
        print("="*60)
        
        # Initialize log files
        start_time_cst = datetime.now(self.cst_tz).strftime('%Y-%m-%d %H:%M:%S CST')
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n\nMonitor started at: {start_time_cst}\n")
        with open(self.reg_log_file, "a", encoding="utf-8") as f:
            f.write(f"\n\nMonitor started at: {start_time_cst}\n")
        
        iteration = 0
        while True:
            try:
                iteration += 1
                timestamp = datetime.now(self.cst_tz).strftime("%Y-%m-%d %H:%M:%S CST")
                
                print(f"[{timestamp}] Check #{iteration} - Sending request...")
                
                # Send request
                response_data = self.send_request()
                
                if response_data:
                    # Extract remaining numbers
                    current_entries = self.extract_remaining_numbers(response_data)
                    
                    if current_entries:
                        # Log regular check
                        self.log_regular_check(current_entries, timestamp, iteration)
                        
                        # Check for changes
                        changes = self.check_for_changes(current_entries)
                        
                        if changes:
                            # Log and notify
                            self.log_success(changes, response_data)
                            self.notify_user(changes)
                        else:
                            # Show summary of current state
                            total_remaining = sum(e["remainingNum"] for e in current_entries)
                            total_available = sum(e["availableCount"] for e in current_entries)
                            print(f"[{timestamp}] No new slots. Total remaining: {total_remaining}, available: {total_available}")
                    else:
                        print(f"[{timestamp}] No appointment data found in response")
                else:
                    print(f"[{timestamp}] Failed to get response")
                
                # Get appropriate wait time based on current time
                wait_time = self.get_wait_time()
                is_peak = self.is_peak_hour()
                peak_status = "🔥 PEAK HOUR" if is_peak else "⏳ Normal"
                print(f"[{timestamp}] {peak_status} - Waiting {wait_time:.1f} seconds until next check...")
                time.sleep(wait_time)
                
            except KeyboardInterrupt:
                stop_time_cst = datetime.now(self.cst_tz).strftime('%Y-%m-%d %H:%M:%S CST')
                print(f"\n\n⏹️  Monitor stopped by user at {stop_time_cst}")
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"Monitor stopped at: {stop_time_cst}\n")
                with open(self.reg_log_file, "a", encoding="utf-8") as f:
                    f.write(f"Monitor stopped at: {stop_time_cst}\n")
                
                # Clear log files after session ends
                print("🧹 Clearing log files...")
                with open(self.log_file, "w", encoding="utf-8") as f:
                    f.write("")  # Clear success.log
                with open(self.reg_log_file, "w", encoding="utf-8") as f:
                    f.write("")  # Clear reg.log
                print("✅ Log files cleared successfully!")
                break
            except Exception as e:
                error_time = datetime.now(self.cst_tz).strftime('%Y-%m-%d %H:%M:%S CST')
                print(f"[{error_time}] Error: {e}")
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"Error at {error_time}: {e}\n")
                with open(self.reg_log_file, "a", encoding="utf-8") as f:
                    f.write(f"Error at {error_time}: {e}\n")
                # Random wait on error too
                error_wait = random.uniform(30, 60)
                print(f"[{error_time}] Waiting {error_wait:.1f} seconds before retry...")
                time.sleep(error_wait)

if __name__ == "__main__":
    monitor = AppointmentMonitor()
    monitor.run_monitor() 