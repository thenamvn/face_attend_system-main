import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import time
import threading
from queue import Queue, Empty
from api.AttendanceAPIClient import AttendanceAPIClient


class FaceRecognitionTkinterUI:
    def __init__(self, width=1280, height=720):
        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.width = width
        self.height = height
        
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("Face Recognition System - Hệ thống nhận diện khuôn mặt")
        self.root.geometry(f"{width}x{height}")
        self.root.state('zoomed')  # Fullscreen on Windows
        
        # Thread-safe queues for UI updates
        self.frame_queue = Queue(maxsize=2)
        self.event_queue = Queue(maxsize=20)  # Chỉ queue events thôi, không queue results
        self.status_queue = Queue(maxsize=20)
        
        # UI state variables
        self.current_frame = None
        self.recognition_results = []
        self.event_log = []
        self.attendance_status = {}
        self.user_cooldowns = {}
        self.display_time = 10
        self.cooldown_period = 10
        
        # Event widgets cache để tránh recreate
        self.event_widgets = {}
        self.last_event_update = 0
        self.event_update_interval = 1.0  # Chỉ update events mỗi 1 giây
        
        # Face recognition system reference
        self.face_recognition_system = None
        self.quit_requested = False
        
        # Initialize API client
        self.api_client = AttendanceAPIClient()
        self.api_client.register_callbacks(
            success_callback=self.on_attendance_success,
            error_callback=self.on_attendance_error
        )
        self.api_client.start()
        
        # Setup UI
        self._setup_ui()
        
        # Start UI update thread
        self.ui_thread_running = True
        self.ui_update_thread = threading.Thread(target=self._ui_update_loop, daemon=True)
        self.ui_update_thread.start()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _setup_ui(self):
        """Setup the main UI layout"""
        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=2)  # Camera frame
        self.root.grid_columnconfigure(1, weight=1)  # Right panel
        self.root.grid_rowconfigure(0, weight=1)
        
        # Left frame for camera
        self.camera_frame = ctk.CTkFrame(self.root)
        self.camera_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.camera_frame.grid_rowconfigure(0, weight=1)
        self.camera_frame.grid_columnconfigure(0, weight=1)
        
        # Camera display label
        self.camera_label = ctk.CTkLabel(
            self.camera_frame, 
            text="Waiting for camera...",
            font=ctk.CTkFont(size=20)
        )
        self.camera_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Right frame for recognition results
        self.right_frame = ctk.CTkFrame(self.root)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        
        # Title for recognition panel
        self.recognition_title = ctk.CTkLabel(
            self.right_frame,
            text="Recent Recognitions",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.recognition_title.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Scrollable frame for recognition events
        self.scrollable_frame = ctk.CTkScrollableFrame(self.right_frame)
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        
        # Control buttons frame
        self.control_frame = ctk.CTkFrame(self.right_frame)
        self.control_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        # Add face button
        self.add_face_btn = ctk.CTkButton(
            self.control_frame,
            text="Add Face (A)",
            command=self._add_face_dialog,
            font=ctk.CTkFont(size=14)
        )
        self.add_face_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.control_frame,
            text="System Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Configure control frame
        self.control_frame.grid_columnconfigure(0, weight=1)
        
        # Bind keyboard events
        self.root.bind('<KeyPress-a>', lambda e: self._add_face_dialog())
        self.root.bind('<KeyPress-A>', lambda e: self._add_face_dialog())
        self.root.bind('<Escape>', lambda e: self._on_closing())
        self.root.focus_set()  # Enable keyboard focus
        
    def _ui_update_loop(self):
        """Main UI update loop running in separate thread"""
        while self.ui_thread_running:
            try:
                # Update frame
                try:
                    frame_data = self.frame_queue.get_nowait()
                    self._update_camera_display(frame_data)
                except Empty:
                    pass
                
                # Update events (chỉ khi có event mới)
                has_new_events = False
                try:
                    while True:  # Process all pending events
                        event_data = self.event_queue.get_nowait()
                        has_new_events = True
                except Empty:
                    pass
                
                # Chỉ update display khi có events mới HOẶC đã qua interval
                current_time = time.time()
                if has_new_events or (current_time - self.last_event_update) > self.event_update_interval:
                    self._update_recognition_display()
                    self.last_event_update = current_time
                
                # Update status messages
                try:
                    status_data = self.status_queue.get_nowait()
                    self._update_status_display(status_data)
                except Empty:
                    pass
                
                # Schedule next update
                time.sleep(0.1)  # Giảm tần suất update từ 0.033 xuống 0.1
                
            except Exception as e:
                print(f"UI update error: {e}")
                time.sleep(0.1)
    
    def _update_camera_display(self, frame):
        """Update camera display with new frame"""
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame to fit display
            display_height = 480
            aspect_ratio = frame.shape[1] / frame.shape[0]
            display_width = int(display_height * aspect_ratio)
            
            frame_resized = cv2.resize(frame_rgb, (display_width, display_height))
            
            # Convert to PIL Image and then to PhotoImage
            pil_image = Image.fromarray(frame_resized)
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update label (must be done in main thread)
            def update_label():
                self.camera_label.configure(image=photo, text="")
                self.camera_label.image = photo  # Keep a reference
            
            self.root.after(0, update_label)
            
        except Exception as e:
            print(f"Camera display update error: {e}")
    
    def _update_recognition_display(self):
        """Update recognition results display - CHỈ KHI CẦN THIẾT"""
        def update_display():
            # Lấy danh sách events hiện tại cần hiển thị
            current_time = time.time()
            visible_events = []
            
            for event in self.event_log[:20]:  # Chỉ lấy 20 events gần nhất
                if current_time - event["timestamp"] <= self.display_time:
                    visible_events.append(event)
            
            # So sánh với events hiện tại để tránh recreate không cần thiết
            existing_widgets = list(self.scrollable_frame.winfo_children())
            
            # Nếu số lượng events khác nhau thì mới recreate
            if len(visible_events) != len(existing_widgets):
                # Clear existing widgets
                for widget in existing_widgets:
                    widget.destroy()
                
                # Create new widgets
                for i, event in enumerate(visible_events):
                    self._create_event_widget(event, i)
            else:
                # Chỉ update text của widgets hiện có
                for i, (event, widget) in enumerate(zip(visible_events, existing_widgets)):
                    self._update_event_widget(widget, event)
        
        self.root.after(0, update_display)
    
    def _create_event_widget(self, event, index):
        """Create widget for recognition event"""
        # Event frame
        event_frame = ctk.CTkFrame(self.scrollable_frame)
        event_frame.grid(row=index, column=0, padx=5, pady=2, sticky="ew")
        event_frame.grid_columnconfigure(0, weight=1)
        
        # Name label
        name_color = "green" if event["status"] == "REAL" else "red"
        name_label = ctk.CTkLabel(
            event_frame,
            text=event["label"],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=name_color
        )
        name_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Status and time
        time_str = time.strftime("%H:%M:%S", time.localtime(event["timestamp"]))
        status_text = f"{event['status']} - {time_str}"
        
        status_label = ctk.CTkLabel(
            event_frame,
            text=status_text,
            font=ctk.CTkFont(size=10)
        )
        status_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")
        
        # Attendance status if available
        parts = event["label"].split('_', 1)
        entry_id = parts[0] if len(parts) > 1 else event["label"]
        
        attendance_label = ctk.CTkLabel(
            event_frame,
            text="",
            font=ctk.CTkFont(size=10)
        )
        attendance_label.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")
        
        # Update attendance status
        self._update_attendance_status(attendance_label, entry_id, event)
        
        # Store references for later updates
        event_frame.name_label = name_label
        event_frame.status_label = status_label
        event_frame.attendance_label = attendance_label
        event_frame.event_data = event
    
    def _update_event_widget(self, widget, event):
        """Update existing event widget with new data"""
        try:
            if hasattr(widget, 'event_data') and widget.event_data != event:
                # Update name label
                name_color = "green" if event["status"] == "REAL" else "red"
                widget.name_label.configure(text=event["label"], text_color=name_color)
                
                # Update status and time
                time_str = time.strftime("%H:%M:%S", time.localtime(event["timestamp"]))
                status_text = f"{event['status']} - {time_str}"
                widget.status_label.configure(text=status_text)
                
                # Update attendance status
                parts = event["label"].split('_', 1)
                entry_id = parts[0] if len(parts) > 1 else event["label"]
                self._update_attendance_status(widget.attendance_label, entry_id, event)
                
                # Store new event data
                widget.event_data = event
        except Exception as e:
            print(f"Error updating event widget: {e}")
    
    def _update_attendance_status(self, attendance_label, entry_id, event):
        """Update attendance status for an event"""
        if entry_id in self.attendance_status:
            status_info = self.attendance_status[entry_id]
            attendance_label.configure(
                text=status_info["message"],
                text_color="green" if status_info["status"] == "success" else "red"
            )
        elif event["status"] == "REAL" and event["label"] != "Unknown":
            attendance_label.configure(
                text="Đang xử lý...",
                text_color="gray"
            )
        else:
            attendance_label.configure(text="")
    
    def _update_status_display(self, status_text):
        """Update status label"""
        def update_status():
            self.status_label.configure(text=status_text)
        
        self.root.after(0, update_status)
    
    def _add_face_dialog(self):
        """Show dialog to add new face"""
        if not self.current_frame is None and self.face_recognition_system:
            dialog = ctk.CTkInputDialog(
                text="Enter name for the face (format: ID_Name):",
                title="Add Face"
            )
            name = dialog.get_input()
            
            if name and name.strip():
                # Add face in background thread
                threading.Thread(
                    target=self._add_face_worker,
                    args=(self.current_frame.copy(), name.strip()),
                    daemon=True
                ).start()
    
    def _add_face_worker(self, frame, name):
        """Worker thread for adding face"""
        try:
            if self.face_recognition_system:
                success = self.face_recognition_system.add_face_to_database(frame, name)
                message = f"✅ Added face: {name}" if success else f"❌ Failed to add: {name}"
                
                # Update status
                if not self.status_queue.full():
                    self.status_queue.put(message)
                
                print(message)
        except Exception as e:
            error_msg = f"❌ Error adding face: {str(e)}"
            if not self.status_queue.full():
                self.status_queue.put(error_msg)
            print(error_msg)
    
    # Thread-safe methods for external updates
    def update_frame(self, frame):
        """Update camera frame (thread-safe)"""
        self.current_frame = frame
        if not self.frame_queue.full():
            try:
                # Remove old frame if queue is full
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    pass
                self.frame_queue.put(frame)
            except:
                pass
    
    def update_recognition_results(self, results):
        """Update recognition results (thread-safe) - KHÔNG LÀM GÌ CẢ"""
        # Chỉ lưu results, không trigger UI update
        self.recognition_results = results
    
    def add_event(self, name, is_real):
        """Add recognition event (thread-safe)"""
        current_time = time.time()
        
        # Check cooldown
        if name in self.user_cooldowns:
            if current_time - self.user_cooldowns[name] < self.cooldown_period:
                return
        
        self.user_cooldowns[name] = current_time
        
        # Add to event log
        event = {
            "label": name,
            "status": "REAL" if is_real else "FAKE",
            "timestamp": current_time
        }
        
        self.event_log.insert(0, event)
        
        # Limit event log size
        if len(self.event_log) > 100:
            self.event_log = self.event_log[:100]
        
        # Process attendance for real faces
        if is_real and "FAKE" not in name and name != "Unknown":
            parts = name.split('_', 1)
            if len(parts) > 1 and parts[0].isalnum():
                id_real = parts[0]
                full_name = parts[1]
            else:
                id_real = name
                full_name = name
            
            print(f"✅ Sending attendance for ID: {id_real}, Name: {full_name}")
            self.api_client.mark_attendance(id_real, full_name)
        
        # Trigger UI update bằng cách gửi signal qua queue
        if not self.event_queue.full():
            try:
                self.event_queue.put("new_event")
            except:
                pass
    
    # API callbacks
    def on_attendance_success(self, attendance_data, response_data):
        """Callback for successful attendance recording"""
        id_real = attendance_data['id_real']
        name = attendance_data['name']
        
        self.attendance_status[id_real] = {
            "status": "success",
            "message": f"✅ Recorded: {name}",
            "timestamp": time.time(),
            "name": name
        }
        
        if not self.status_queue.full():
            self.status_queue.put(f"✅ Attendance recorded: {name}")
        
        # Trigger UI update
        if not self.event_queue.full():
            try:
                self.event_queue.put("attendance_update")
            except:
                pass
    
    def on_attendance_error(self, attendance_data, error_msg):
        """Callback for attendance recording error"""
        id_real = attendance_data['id_real']
        name = attendance_data['name']
        
        self.attendance_status[id_real] = {
            "status": "error",
            "message": f"❌ Failed: {name}",
            "timestamp": time.time(),
            "name": name
        }
        
        if not self.status_queue.full():
            self.status_queue.put(f"❌ Attendance failed: {name}")
        
        # Trigger UI update
        if not self.event_queue.full():
            try:
                self.event_queue.put("attendance_update")
            except:
                pass
    
    def should_quit(self):
        """Check if quit was requested"""
        return self.quit_requested
    
    def _on_closing(self):
        """Handle window closing"""
        self.quit_requested = True
        self.ui_thread_running = False
        
        # Stop API client
        if self.api_client:
            self.api_client.stop()
        
        # Wait for UI thread to finish
        if self.ui_update_thread.is_alive():
            self.ui_update_thread.join(timeout=1.0)
        
        # Destroy window
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the UI main loop"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"UI error: {e}")
            self._on_closing()
    
    def close(self):
        """Close the UI"""
        self._on_closing()