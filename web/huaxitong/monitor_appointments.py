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
            "Mac": "Not Found",
            "Accept": "*/*",
            "Client-Version": "7.1.1",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB;q=1",
            "token": "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIyNzkwODA5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhIiwiaWF0IjoxNzUyMDY3MTI2LCJzdWIiOiJ7XCJ1c2VySWRcIjpcIjI3OTA4MFwiLFwiYWNjb3VudElkXCI6XCIyOTMzNjBcIixcInVzZXJUeXBlXCI6MCxcImFwcENvZGVcIjpcIkhYR1lBUFBcIixcImNoYW5uZWxDb2RlXCI6XCJQQVRJRU5UX0lPU1wiLFwiZGV2aWNlbnVtYmVyXCI6XCI5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhXCIsXCJkZXZpY2VUeXBlXCI6XCJBUFBcIixcImFjY291bnROb1wiOlwiMTM4ODI5ODUxODhcIixcIm5hbWVcIjpcIumZiOS6leW3nVwiLFwiZG9jdG9ySWRcIjpudWxsLFwib3JnYW5Db2RlXCI6bnVsbH0iLCJleHAiOjE3NTQ2NTkxMjZ9.cqAJ3RaGREQ9dxrhBgP_rxiZQfZIpMMDDP756Vk-KPo***HXGYAPP",
            "accessToken": "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIyNzkwODA5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhIiwiaWF0IjoxNzUyMDY3MTI2LCJzdWIiOiJ7XCJ1c2VySWRcIjpcIjI3OTA4MFwiLFwiYWNjb3VudElkXCI6XCIyOTMzNjBcIixcInVzZXJUeXBlXCI6MCxcImFwcENvZGVcIjpcIkhYR1lBUFBcIixcImNoYW5uZWxDb2RlXCI6XCJQQVRJRU5UX0lPU1wiLFwiZGV2aWNlbnVtYmVyXCI6XCI5NTBiOWY4NzhlNjcwZTg3Y2VjOWYwNzc5YmI5ODE0NTVhZDM3YmUyMjViZjVkODkzODA4MTM5YzYwMDgwODBhXCIsXCJkZXZpY2VUeXBlXCI6XCJBUFBcIixcImFjY291bnROb1wiOlwiMTM4ODI5ODUxODhcIixcIm5hbWVcIjpcIumZiOS6leW3nVwiLFwiZG9jdG9ySWRcIjpudWxsLFwib3JnYW5Db2RlXCI6bnVsbH0iLCJleHAiOjE3NTQ2NTkxMjZ9.cqAJ3RaGREQ9dxrhBgP_rxiZQfZIpMMDDP756Vk-KPo***HXGYAPP",
            "Content-Type": "application/json",
            "User-Agent": "hua yi tong/7.1.1 (iPhone; iOS 15.7.1; Scale/3.00)",
            "Connection": "keep-alive",
            "Cookie": "acw_tc=1a0c39d517520671325397305e006fd461912cc23204c81632e69d6d08fbc3"
        }
        
        # Multiple doctors to monitor
        self.doctors = [
            # {
            #     "name": "戴晴晴 (耳鼻喉眩晕专科)",
            #     "payload": {
            #         "hospitalCode": "HID0101",
            #         "deptCode": "1649",
            #         "doctorId": "4028b881646e3d8701646e3d876301f6",
            #         "channelCode": "PATIENT_IOS",
            #         "appCode": "HXGYAPP",
            #         "hospitalAreaCode": "F0017",
            #         "tabAreaCode": "",
            #         "cardId": "806596678557749240",
            #         "encrypt": "MR+DrCZkmnCtWy7tdyTqkA==",
            #         "deptCategoryCode": "6100-EBHK",
            #         "appointmentType": "1"
            #     }
            # },
            # {
            #     "name": "王茹 (美容烧伤整形-四级专家)",
            #     "payload": {
            #         "hospitalCode": "HID0101",
            #         "deptCode": "",
            #         "doctorId": "4028b881646e3d8701646e3d871f0071",
            #         "channelCode": "PATIENT_IOS",
            #         "appCode": "HXGYAPP",
            #         "hospitalAreaCode": "",
            #         "tabAreaCode": "",
            #         "cardId": "",
            #         "encrypt": "FU+k39GWflNAKvkCDVD+oQ==",
            #         "deptCategoryCode": "",
            #         "appointmentType": "1"
            #     }
            # },
            {
                "name": "李正勇 (美容烧伤整形-一级专家)",
                "payload": {
                    "hospitalCode": "HID0101",
                    "deptCode": "",
                    "doctorId": "4028b082715335fa017153530154008d",
                    "channelCode": "PATIENT_IOS",
                    "appCode": "HXGYAPP",
                    "hospitalAreaCode": "",
                    "tabAreaCode": "",
                    "cardId": "",
                    "encrypt": "FU+k39GWflNAKvkCDVD+oQ==",
                    "deptCategoryCode": "",
                    "appointmentType": "1"
                }
            }
            # {
            #     "name": "伍俊良 (美容烧伤整形-四级专家)",
            #     "payload": {
            #         "hospitalCode": "HID0101",
            #         "deptCode": "",
            #         "doctorId": "4028b881646e3d8701646e3d87190048",
            #         "channelCode": "PATIENT_IOS",
            #         "appCode": "HXGYAPP",
            #         "hospitalAreaCode": "",
            #         "tabAreaCode": "",
            #         "cardId": "",
            #         "encrypt": "jdMJ/J+qvttOzzmkISTAoQ==",
            #         "deptCategoryCode": "",
            #         "appointmentType": "1"
            #     }
            # }
        ]
        
        
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
        
        # Track previous state of remaining numbers for each doctor
        self.previous_remaining = {}
        self.log_file = "success.log"
        self.reg_log_file = "reg.log"
        
        # 中国标准时间 CST (UTC+8) 
        self.cst_tz = timezone(timedelta(hours=8))
        
        # Server酱通知配置
        self.serverchan_url = "https://sctapi.ftqq.com/SCT282278TOxQRSjkfr6zTL0r7gQTi4wyZ.send"
        self.last_notification_time = 0  # Track last notification timestamp
        self.notification_cooldown = 300  # 5 minutes in seconds
        
    def get_current_payload(self, doctor_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate payload with current timestamp for specific doctor"""
        payload = doctor_payload.copy()
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
            return random.uniform(15, 25)  # 15-25 seconds normally
    
    def send_request(self, doctor_payload: Dict[str, Any], doctor_name: str) -> Dict[str, Any]:
        """Send the API request and return the response for specific doctor"""
        try:
            # Add small random delay before request (0.5-2 seconds)
            time.sleep(random.uniform(0.5, 2.0))
            
            # Get dynamic payload and headers
            payload = self.get_current_payload(doctor_payload)
            headers = self.get_randomized_headers()
            
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                response_data = response.json()
                # Debug: Print response structure
                print(f"DEBUG - {doctor_name} API Response Code: {response_data.get('code')}")
                print(f"DEBUG - {doctor_name} API Response Message: {response_data.get('msg')}")
                if response_data.get('data'):
                    source_items = response_data.get('data', {}).get('sourceItemsRespVos', [])
                    print(f"DEBUG - {doctor_name} Found {len(source_items) if source_items else 0} source items")
                return response_data
            else:
                print(f"Error for {doctor_name}: HTTP {response.status_code}")
                print(f"DEBUG - Response text: {response.text[:200]}...")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error for {doctor_name}: {e}")
            return None
    
    def get_time_period_label(self, schedule_range: int) -> str:
        """Get time period label based on scheduleRange"""
        if schedule_range == 0:
            return "上午"
        elif schedule_range == 1:
            return "下午"
        else:
            return f"时段{schedule_range}"
    
    def extract_remaining_numbers(self, data: Dict[str, Any], doctor_name: str) -> List[Dict[str, Any]]:
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
                schedule_range = item.get("scheduleRange", 0)
                remaining_entries.append({
                    "id": schedule_id,
                    "scheduleDate": item.get("scheduleDate"),
                    "scheduleRange": schedule_range,
                    "timePeriod": self.get_time_period_label(schedule_range),
                    "remainingNum": item.get("remainingNum", 0),
                    "availableCount": item.get("availableCount", 0),
                    "status": item.get("status", 0),
                    "deptName": item.get("deptName"),
                    "hospitalAreaName": item.get("hospitalAreaName"),
                    "dayDesc": item.get("dayDesc"),
                    "admLocation": item.get("admLocation")
                })
        
        # Check sourceItemsRespVos
        source_items = response_data.get("sourceItemsRespVos", [])
        if source_items is None:
            source_items = []
        for item in source_items:
            # Filter for 华西坝院区 only for beauty doctors (王茹, 李正勇, 伍俊良)
            if ("王茹" in doctor_name or "李正勇" in doctor_name or "伍俊良" in doctor_name) and item.get("hospitalAreaCode") != "HID0101":
                continue
            add_entry_if_unique(item)
        
        # Check nested sourceItems structure  
        source_items_nested = response_data.get("sourceItems", [])
        if source_items_nested is None:
            source_items_nested = []
        for area in source_items_nested:
            if area is None:
                continue
            # Filter for 华西坝院区 only for beauty doctors (王茹, 李正勇, 伍俊良)
            if ("王茹" in doctor_name or "李正勇" in doctor_name or "伍俊良" in doctor_name) and area.get("areaCode") != "HID0101":
                continue
            area_items = area.get("sourceItemsRespVos", [])
            if area_items is None:
                area_items = []
            for item in area_items:
                add_entry_if_unique(item)
        
        return remaining_entries
    
    def check_for_changes(self, current_entries: List[Dict[str, Any]], doctor_name: str) -> List[Dict[str, Any]]:
        """Check for appointments that changed in availableCount (0→positive) or status (2→any)"""
        changes = []
        
        for entry in current_entries:
            entry_id = entry["id"]
            current_available = entry["availableCount"]
            current_status = entry["status"]
            
            change_detected = False
            changed_fields = []
            
            # Check availableCount changes from 0 to positive
            available_key = f"{doctor_name}_{entry_id}_availableCount"
            previous_available = self.previous_remaining.get(available_key, 0)
            
            if previous_available == 0 and current_available > 0:
                change_detected = True
                changed_fields.append(f"availableCount: {previous_available} → {current_available}")
            
            # Update availableCount tracking
            self.previous_remaining[available_key] = current_available
            
            # Check status changes FROM 2 to any other value
            status_key = f"{doctor_name}_{entry_id}_status"
            previous_status = self.previous_remaining.get(status_key, 2)  # Default to 2 for first time
            
            if previous_status == 2 and current_status != 2:
                change_detected = True
                changed_fields.append(f"status: {previous_status} → {current_status}")
            
            # Update status tracking
            self.previous_remaining[status_key] = current_status
            
            # If any change detected, add to changes dict (only one entry per appointment slot)
            if change_detected:
                change_info = entry.copy()
                change_info["changed_fields"] = changed_fields
                change_info["changes_summary"] = ", ".join(changed_fields)
                changes.append(change_info)
        
        return changes
    
    def log_regular_check(self, entries: List[Dict[str, Any]], timestamp: str, iteration: int):
        """Log regular checks to reg.log"""
        with open(self.reg_log_file, "a", encoding="utf-8") as f:
            total_available = sum(e["availableCount"] for e in entries)
            total_active_status = sum(1 for e in entries if e["status"] == 1)
            is_peak = self.is_peak_hour()
            peak_marker = " [PEAK]" if is_peak else ""
            f.write(f"[{timestamp}] Check #{iteration}{peak_marker} - Total available: {total_available}, active status: {total_active_status}\n")
            
            # Log details of each slot grouped by doctor
            current_doctor = ""
            for entry in entries:
                doctor_name = entry.get("doctor_name", "Unknown")
                if doctor_name != current_doctor:
                    f.write(f"  --- {doctor_name} ---\n")
                    current_doctor = doctor_name
                f.write(f"  {entry['scheduleDate']} {entry['timePeriod']} ({entry['dayDesc']}) - "
                       f"Available: {entry['availableCount']}, Status: {entry['status']} - "
                       f"{entry['deptName']} - {entry['hospitalAreaName']}\n")

    def log_success(self, changes: List[Dict[str, Any]], full_response: Dict[str, Any]):
        """Log successful detections to success.log"""
        timestamp = datetime.now(self.cst_tz).strftime("%Y-%m-%d %H:%M:%S CST")
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"APPOINTMENT AVAILABLE DETECTED - {timestamp}\n")
            f.write(f"{'='*80}\n")
            
            # Group changes by doctor
            changes_by_doctor = {}
            for change in changes:
                doctor_name = change.get("doctor_name", "Unknown")
                if doctor_name not in changes_by_doctor:
                    changes_by_doctor[doctor_name] = []
                changes_by_doctor[doctor_name].append(change)
            
            for doctor_name, doctor_changes in changes_by_doctor.items():
                f.write(f"\n--- {doctor_name} ---\n")
                for change in doctor_changes:
                    f.write(f"\nSlot Available:\n")
                    f.write(f"  Schedule ID: {change['id']}\n")
                    f.write(f"  Date: {change['scheduleDate']} {change['timePeriod']} ({change['dayDesc']})\n")
                    f.write(f"  Department: {change['deptName']}\n")
                    f.write(f"  Location: {change['admLocation']}\n")
                    f.write(f"  Hospital Area: {change['hospitalAreaName']}\n")
                    f.write(f"  Changes: {change['changes_summary']}\n")
                    f.write(f"  Schedule Range: {change['scheduleRange']}\n")
            
            f.write(f"\n{'='*80}\n")
    
    def notify_user(self, changes: List[Dict[str, Any]]):
        """Notify user about available appointments"""
        print(f"\n🎉 APPOINTMENT SLOTS AVAILABLE! 🎉")
        print(f"Time: {datetime.now(self.cst_tz).strftime('%Y-%m-%d %H:%M:%S CST')}")
        print(f"Found {len(changes)} new available slot(s):")
        
        # Group by doctor for display
        changes_by_doctor = {}
        for change in changes:
            doctor_name = change.get("doctor_name", "Unknown")
            if doctor_name not in changes_by_doctor:
                changes_by_doctor[doctor_name] = []
            changes_by_doctor[doctor_name].append(change)
        
        slot_counter = 1
        for doctor_name, doctor_changes in changes_by_doctor.items():
            print(f"\n  👨‍⚕️ {doctor_name}:")
            for change in doctor_changes:
                print(f"    Slot {slot_counter}:")
                print(f"      📅 Date: {change['scheduleDate']} {change['timePeriod']} ({change['dayDesc']})")
                print(f"      🏥 Department: {change['deptName']}")
                print(f"      📍 Location: {change['admLocation']}")
                print(f"      🏢 Hospital Area: {change['hospitalAreaName']}")
                print(f"      🔄 Changes: {change['changes_summary']}")
                slot_counter += 1
        
        print(f"\n📋 Details logged to: {self.log_file}")
        print("="*60)
        
        # Send Server酱 WeChat notification
        self.send_serverchan_notification(changes)
        
        # Try to send system notification (if available)
        try:
            doctors_list = ", ".join(set(c.get("doctor_name", "Unknown") for c in changes))
            os.system(f'notify-send "Appointment Available" "{len(changes)} new slot(s) found for {doctors_list}"')
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
            
            # Group changes by doctor
            changes_by_doctor = {}
            for change in changes:
                doctor_name = change.get("doctor_name", "Unknown")
                if doctor_name not in changes_by_doctor:
                    changes_by_doctor[doctor_name] = []
                changes_by_doctor[doctor_name].append(change)
            
            doctors_list = ", ".join(changes_by_doctor.keys())
            
            # Build detailed message content in Markdown
            desp_lines = [
                f"## 📅 预约信息",
                f"**医生**: {doctors_list}",
                f"**时间**: {datetime.now(self.cst_tz).strftime('%Y-%m-%d %H:%M:%S CST')}",
                f"**发现**: {len(changes)} 个可预约时段",
                "",
                "### 📋 可预约时段详情:"
            ]
            
            slot_counter = 1
            for doctor_name, doctor_changes in changes_by_doctor.items():
                desp_lines.extend([
                    f"",
                    f"### 👨‍⚕️ {doctor_name}"
                ])
                
                for change in doctor_changes:
                    # Determine fee based on doctor
                    if "李正勇" in doctor_name:
                        fee_info = "挂号费90元 + 服务费2元"
                    elif "王茹" in doctor_name or "伍俊良" in doctor_name:
                        fee_info = "挂号费20元 + 服务费2元"
                    else:
                        fee_info = "挂号费17元 + 服务费2元"
                    
                    desp_lines.extend([
                        f"",
                        f"**时段 {slot_counter}:**",
                        f"- 📅 日期: {change['scheduleDate']} {change['timePeriod']} ({change['dayDesc']})",
                        f"- 🏥 科室: {change['deptName']}",
                        f"- 📍 地点: {change['admLocation']}",
                        f"- 🏢 院区: {change['hospitalAreaName']}",
                        f"- 🔄 变化: {change['changes_summary']}",
                        f"- 💰 费用: {fee_info}"
                    ])
                    slot_counter += 1
            
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
                "short": f"发现{len(changes)}个预约时段 - {changes[0]['scheduleDate']} {changes[0]['timePeriod']}",
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
        print(f"⏰ Normal: 15-25s intervals | Peak: 5s intervals (7:59-8:04 AM/PM 中国时间)")
        print(f"🎯 Monitoring {len(self.doctors)} doctors:")
        for i, doctor in enumerate(self.doctors, 1):
            print(f"   {i}. {doctor['name']}")
        print(f"🛡️ Anti-detection: Dynamic timestamps, randomized intervals, rotating User-Agents")
        print(f"📱 WeChat notifications: Enabled via Server酱")
        print(f"🔍 Monitoring: availableCount (0→positive), status (2→any), time periods (上午/下午)")
        print(f"🏥 李正勇: Only monitoring 华西坝院区 (HID0101)")
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
                
                print(f"[{timestamp}] Check #{iteration} - Checking {len(self.doctors)} doctors...")
                
                all_changes = []
                all_entries = []
                
                # Check each doctor
                for doctor in self.doctors:
                    doctor_name = doctor["name"]
                    doctor_payload = doctor["payload"]
                    
                    print(f"[{timestamp}] Checking {doctor_name}...")
                    
                    # Send request for this doctor
                    response_data = self.send_request(doctor_payload, doctor_name)
                    
                    if response_data:
                        # Extract remaining numbers for this doctor
                        current_entries = self.extract_remaining_numbers(response_data, doctor_name)
                        
                        if current_entries:
                            # Add doctor name to entries for logging
                            for entry in current_entries:
                                entry["doctor_name"] = doctor_name
                            all_entries.extend(current_entries)
                            
                            # Check for changes for this doctor
                            changes = self.check_for_changes(current_entries, doctor_name)
                            if changes:
                                # Add doctor name to changes
                                for change in changes:
                                    change["doctor_name"] = doctor_name
                                all_changes.extend(changes)
                                
                            # Show summary for this doctor
                            total_available = sum(e["availableCount"] for e in current_entries)
                            total_active_status = sum(1 for e in current_entries if e["status"] == 1)
                            print(f"[{timestamp}] {doctor_name}: {total_available} available, {total_active_status} active")
                        else:
                            print(f"[{timestamp}] {doctor_name}: No appointment data found")
                    else:
                        print(f"[{timestamp}] {doctor_name}: Failed to get response")
                    
                    # Small delay between doctors
                    time.sleep(random.uniform(1, 3))
                
                # Log and notify if any changes found
                if all_entries:
                    # Log regular check for all doctors
                    self.log_regular_check(all_entries, timestamp, iteration)
                    
                if all_changes:
                    # Log and notify about all changes
                    self.log_success(all_changes, {"combined_changes": True})
                    self.notify_user(all_changes)
                else:
                    # Show overall summary
                    total_available = sum(e["availableCount"] for e in all_entries)
                    total_active_status = sum(1 for e in all_entries if e["status"] == 1)
                    print(f"[{timestamp}] Overall: No new slots. Total available: {total_available}, active status: {total_active_status}")
                    
                if not all_entries:
                    print(f"[{timestamp}] No appointment data found for any doctor")
                
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