# 🦷 Hospital Appointment Monitor - 牙周病科

A continuous monitoring system for hospital appointment availability, specifically focused on the **牙周病科 (Periodontal Department)**.

## ✨ Features

- 🦷 **Focused monitoring** on 牙周病科 department
- ⏰ **30-second check intervals** for real-time monitoring  
- 📱 **WeChat notifications** via Server酱 when appointments become available
- 🛡️ **24/7 continuous monitoring** with automatic daily restarts
- 📊 **Comprehensive logging** with regular and success logs
- 🔄 **Easy tmux management** with start/stop/restart scripts
- 📅 **Dynamic date scanning** (automatically scans next 8 days from today)
- 🔄 **Never stops monitoring** - auto-restarts every 24h for maintenance

## 🚀 Quick Start

### Start the Monitor
```bash
./start.sh
```

### Stop the Monitor
```bash
./stop.sh
```

### Restart the Monitor
```bash
./restart.sh
```

### View Live Logs
```bash
# Regular monitoring logs
tail -f reg.log

# Success/notification logs  
tail -f success.log

# Attach to tmux session
tmux attach-session -t hospital_monitor
```

## 📋 System Details

### Target Department
- **Department**: 牙周病科 (Periodontal Department)
- **Department ID**: `086028000A000011`
- **Monitoring Range**: Next 8 days from today
- **Check Interval**: 30 seconds

### Safety & Continuous Operation
- **Continuous monitoring**: 24/7 operation, never stops
- **Auto-restart**: Every 24 hours (clears logs, fresh start)
- **Max CPU**: 30%
- **Max Memory**: 200MB
- **Max Log Size**: 50MB per file
- **Safety Check Interval**: 60 seconds

### Notification System
- **WeChat notifications** via Server酱
- **Cooldown period**: 5 minutes between notifications
- **System notifications** (if available)

## 📁 File Structure

```
├── hospital_monitor.py     # Main monitoring script
├── start.sh               # Start tmux session with safety monitoring
├── stop.sh                # Stop all monitoring processes
├── restart.sh             # Restart the entire system
├── requirements.txt       # Python dependencies
├── reg.log               # Regular monitoring logs
├── success.log           # Success/notification logs
└── .monitor_safety.pid   # Safety monitor process ID (auto-created)
```

## 🔧 Configuration

Key settings in `hospital_monitor.py`:

```python
# Department to monitor
TARGET_DEPARTMENT = {
    "name": "牙周病科",
    "id": "086028000A000011"
}

# Monitoring settings  
SCAN_DAYS = 8                 # Days to scan ahead
CHECK_INTERVAL = 30           # Seconds between checks
NOTIFICATION_COOLDOWN = 300   # Seconds between notifications
```

## 📱 Notifications

When new appointments are found, you'll receive:

1. **Console output** with appointment details
2. **WeChat notification** via Server酱 with:
   - 📅 Appointment dates and times
   - 👨‍⚕️ Doctor names
   - 🏥 Department information
   - 💰 Fee information
3. **System notification** (if desktop notifications available)
4. **Log entries** in success.log

## 🛡️ Safety & Continuous Operation

The system includes comprehensive safety monitoring for 24/7 operation:

- **Automatic restart** every 24 hours (never stops monitoring)
- **Resource monitoring** with automatic restart if limits exceeded
- **Log clearing** on each restart for fresh maintenance
- **Process cleanup** and fresh session creation
- **Health checks** every minute
- **Graceful error handling** and recovery
- **Continuous monitoring** - system never truly stops

## 📊 Monitoring Status

Check if the monitor is running:

```bash
# Check tmux session
tmux list-sessions | grep hospital_monitor

# Check processes
ps aux | grep hospital_monitor

# View recent logs
tail -20 reg.log
```

## 🔄 Troubleshooting

### Monitor won't start
1. Check Python path: `/allah/freqtrade/.venv/bin/python3`
2. Ensure tmux is installed: `sudo apt-get install tmux`
3. Check script permissions: `chmod +x *.sh`

### No notifications received
1. Verify Server酱 URL in `hospital_monitor.py`
2. Check notification cooldown (5 minutes)
3. Review success.log for notification attempts

### High resource usage
- Safety monitor will automatically shutdown if limits exceeded
- Adjust limits in `start.sh` if needed
- Check for multiple running instances

## ⚡ Performance

- **Lightweight**: ~10-20MB RAM usage typical
- **Efficient**: HTTP session reuse and minimal processing
- **Reliable**: Automatic error recovery and safety monitoring
- **Fast**: 30-second response time for new appointments

---

**🦷 Focus**: This system is specifically optimized for monitoring 牙周病科 appointments with immediate notifications when slots become available. 