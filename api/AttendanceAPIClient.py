import requests
from datetime import datetime
import time
import threading
import queue

class AttendanceAPIClient:
    def __init__(self, api_url="https://render-face-system-api.onrender.com/api/attendance", retry_interval=5, max_retries=1):
        """
        Initialize the Attendance API Client
        
        Args:
            api_url (str): Base URL of the attendance API
            retry_interval (int): Seconds to wait between retries
            max_retries (int): Maximum number of retry attempts
        """
        self.api_url = api_url
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.queue = queue.Queue()
        self.running = False
        self.thread = None
        self.success_callback = None
        self.error_callback = None
        
    def register_callbacks(self, success_callback=None, error_callback=None):
        """Register callback functions for success and error events
        
        Args:
            success_callback: Function to call when attendance is successfully recorded
            error_callback: Function to call when attendance recording fails
        """
        self.success_callback = success_callback
        self.error_callback = error_callback
        
    def start(self):
        """Start the background thread for processing attendance records"""
        if self.thread is not None and self.thread.is_alive():
            print("Attendance API client is already running")
            return self
            
        self.running = True
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        print("Attendance API client started")
        return self
        
    def stop(self):
        """Stop the background thread"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        print("Attendance API client stopped")
    
    def _process_queue(self):
        """Background thread for processing the attendance queue"""
        while self.running:
            try:
                # Get attendance data from queue with timeout
                attendance_data = self.queue.get(timeout=1.0)
                self._send_attendance_with_retry(attendance_data)
                self.queue.task_done()
            except queue.Empty:
                # No data in queue, continue waiting
                continue
            except Exception as e:
                print(f"Error in attendance processing thread: {e}")
                time.sleep(1)  # Sleep to avoid tight loop in case of repeated errors
    
    def _send_attendance_with_retry(self, attendance_data):
        """Send attendance data with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url, 
                    json=attendance_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in [200, 201]:
                    print(f"✅ Attendance recorded for {attendance_data['name']}")
                    response_data = response.json()
                    
                    # Call success callback if registered
                    if self.success_callback:
                        self.success_callback(attendance_data, response_data)
                        
                    return response_data
                else:
                    error_msg = f"❌ Failed to record attendance: {response.status_code}, {response.text}"
                    print(error_msg)
                    
                    # Call error callback if registered
                    if self.error_callback and attempt == self.max_retries - 1:
                        self.error_callback(attendance_data, error_msg)
                    
            except requests.RequestException as e:
                error_msg = f"⚠️ Network error (attempt {attempt+1}/{self.max_retries}): {str(e)}"
                print(error_msg)
                
                # Call error callback if registered and on last attempt
                if self.error_callback and attempt == self.max_retries - 1:
                    self.error_callback(attendance_data, error_msg)
                
            # Wait before retry if not the last attempt
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_interval)
                
        print(f"❌ Failed to record attendance after {self.max_retries} attempts")
        return None
    
    def mark_attendance(self, id_real, name):
        """
        Queue an attendance record to be sent to the API
        
        Args:
            id_real (str): ID or identifier of the person
            name (str): Full name of the person
        """
        current_time = datetime.now().isoformat()
        
        # Prepare attendance data
        attendance_data = {
            "id_real": id_real,
            "name": name,
            "time": current_time
        }
        
        # Add to queue for background processing
        self.queue.put(attendance_data)
        print(f"➕ Queued attendance for {name} ({id_real})")