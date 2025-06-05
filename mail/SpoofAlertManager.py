import os
import time
import smtplib
import threading
import cv2
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

class SpoofAlertManager:
    def __init__(self, 
                 email_sender="your-email@gmail.com", 
                 email_password="your-app-password",
                 email_recipients=["admin@example.com"],
                 min_duration=2.0,
                 cooldown_period=60):
        """
        Initialize the spoof alert manager
        
        Args:
            email_sender: Sender email address
            email_password: Sender email password or app password
            email_recipients: List of email addresses to send alerts to
            min_duration: Minimum duration (seconds) before sending alert
            cooldown_period: Minimum time (seconds) between alerts for the same person
        """
        self.email_sender = email_sender
        self.email_password = email_password
        self.email_recipients = email_recipients
        self.min_duration = min_duration
        self.cooldown_period = cooldown_period
        self.device_location = os.getenv("DEVICE_LOCATION")
        
        # Track detected spoofs: {name: {'first_seen': timestamp, 'last_alert': timestamp}}
        self.tracked_spoofs = {}
        
        # Queue for sending emails in background
        self.email_queue = []
        self.queue_lock = threading.Lock()
        
        # Start background thread for sending emails
        self.running = True
        self.email_thread = threading.Thread(target=self._email_worker, daemon=True)
        self.email_thread.start()
        
    def update(self, results, frame):
        """
        Update spoof tracking based on new face recognition results
        
        Args:
            results: List of face recognition results
            frame: Current video frame
        """
        current_time = time.time()
        
        # Find fake faces in results
        fake_faces = [r for r in results if not r.get("is_real", True) and r["name"].startswith("FAKE:")]
        
        # Process each fake face
        for face in fake_faces:
            # Extract original name from "FAKE: Name"
            original_name = face["name"].replace("FAKE: ", "")
            
            # If this is a new fake face, start tracking it
            if original_name not in self.tracked_spoofs:
                self.tracked_spoofs[original_name] = {
                    'first_seen': current_time,
                    'last_alert': 0,
                    'box': face["box"]
                }
            else:
                # Update tracking information
                self.tracked_spoofs[original_name]['box'] = face["box"]
            
            # Check if we should send an alert
            spoof_info = self.tracked_spoofs[original_name]
            duration = current_time - spoof_info['first_seen']
            time_since_last_alert = current_time - spoof_info['last_alert']
            
            if (duration >= self.min_duration and 
                (spoof_info['last_alert'] == 0 or time_since_last_alert >= self.cooldown_period)):
                # Capture face region for the alert
                x1, y1, x2, y2 = face["box"]
                face_img = frame[y1:y2, x1:x2].copy()
                
                # Queue email to be sent in background thread
                self._queue_email(original_name, face_img, frame.copy())
                
                # Update last alert time
                self.tracked_spoofs[original_name]['last_alert'] = current_time
                
        # Remove tracked spoofs that are no longer detected (reset tracking)
        current_fakes = [r["name"].replace("FAKE: ", "") for r in fake_faces]
        names_to_remove = []
        
        for name in self.tracked_spoofs:
            if name not in current_fakes:
                names_to_remove.append(name)
                
        for name in names_to_remove:
            del self.tracked_spoofs[name]
    
    def _queue_email(self, name, face_img, full_frame):
        """Queue an email to be sent by the background thread"""
        with self.queue_lock:
            self.email_queue.append((name, face_img, full_frame))
    
    def _email_worker(self):
        """Background thread for sending emails"""
        while self.running:
            # Check if there are emails to send
            with self.queue_lock:
                if self.email_queue:
                    name, face_img, full_frame = self.email_queue.pop(0)
                else:
                    name = None
            
            # If we have an email to send
            if name:
                try:
                    self._send_spoof_alert(name, face_img, full_frame)
                except Exception as e:
                    print(f"⚠️ Failed to send spoof alert email: {str(e)}")
            
            # Sleep briefly to avoid using too much CPU
            time.sleep(0.1)
    
    def _send_spoof_alert(self, name, face_img, full_frame):
        """Send spoof alert email with face image"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.email_sender
        msg['To'] = ', '.join(self.email_recipients)
        msg['Subject'] = f"⚠️ SECURITY ALERT: Spoof Detection for {name}"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>⚠️ Face Authentication Security Alert</h2>
            <p>A spoofing attempt has been detected in your face recognition system.</p>
            <p><b>Details:</b></p>
            <ul>
                <li><b>Person:</b> {name}</li>
                <li><b>Time:</b> {timestamp}</li>
                <li><b>Location:</b> Main entrance camera</li>
            </ul>
            <p>Please review the attached images and take appropriate action if necessary.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach face image
        if face_img is not None:
            face_path = f"temp_face_{int(time.time())}.jpg"
            cv2.imwrite(face_path, face_img)
            
            with open(face_path, 'rb') as f:
                face_attachment = MIMEImage(f.read())
                face_attachment.add_header('Content-Disposition', 'attachment', 
                                          filename=f"spoof_face_{timestamp.replace(' ', '_')}.jpg")
                msg.attach(face_attachment)
            
            # Clean up temp file
            os.remove(face_path)
        
        # Attach full frame 
        if full_frame is not None:
            frame_path = f"temp_frame_{int(time.time())}.jpg"
            cv2.imwrite(frame_path, full_frame)
            
            with open(frame_path, 'rb') as f:
                frame_attachment = MIMEImage(f.read())
                frame_attachment.add_header('Content-Disposition', 'attachment',
                                           filename=f"full_scene_{timestamp.replace(' ', '_')}.jpg")
                msg.attach(frame_attachment)
            
            # Clean up temp file
            os.remove(frame_path)
        
        # Send email
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            print(f"✅ Sent spoof alert email for {name}")
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
    
    def stop(self):
        """Stop the background thread"""
        self.running = False
        if self.email_thread and self.email_thread.is_alive():
            self.email_thread.join(timeout=1.0)