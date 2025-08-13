#!/usr/bin/env python3
import requests
import json

def send_request():
    # URL
    url = "https://hytapiv2.cd120.com/cloud/appointment/doctorListModel/selDoctorDetailsTwo"
    
    # Headers
    headers = {
        "Host": "hytapiv2.cd120.com",
        "UUID": "25FEFB37-9D3D-4FA1-B7E8-81F7FB0A2FAD",
        "Mac": "Not Found",
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
    
    # JSON payload
    payload = {
        "hospitalCode": "HID0101",
        "timestamp": "1749446842",
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
    
    try:
        # Send the request
        print("Sending request...")
        print(f"URL: {url}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print("-" * 50)
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # Print response details
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        # Return response for further processing if needed
        return response
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")
        return None

if __name__ == "__main__":
    send_request() 