#!/allah/freqtrade/.venv/bin/python3.11

import logging
import queue
import sys
import threading
import time
from typing import Optional

# Create a queue for log messages
log_queue = queue.Queue()

# Custom handler that puts messages in queue instead of directly to console
class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.put(msg)
        except Exception:
            self.handleError(record)

# Configure logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("trading_assistant.log"),
            QueueHandler()  # Use our custom handler for console output
        ]
    )
    logger = logging.getLogger("BinanceAssistant")
    
    # Start log printer thread
    log_thread = threading.Thread(target=log_printer, daemon=True)
    log_thread.start()
    
    return logger

# Function to print logs in a separate thread
def log_printer():
    while True:
        try:
            # Print logs from the queue
            while not log_queue.empty():
                # Get log message
                log_message = log_queue.get()
                
                # Print the log with a trailing newline to ensure prompt stays clean
                sys.stdout.write(f"{log_message}\n")
                sys.stdout.flush()
                
            time.sleep(0.1)
        except Exception as e:
            print(f"Error in log printer: {e}")
            time.sleep(1)

# Custom print function that won't interfere with input prompt
def safe_print(message: str):
    """Print a message that won't be overwritten by logs."""
    sys.stdout.write(f"\n{message}")
    sys.stdout.flush()

# Initialize logger
logger = setup_logging() 