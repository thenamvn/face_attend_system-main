import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import time
import threading
from queue import Queue, Empty
from api.AttendanceAPIClient import AttendanceAPIClient
import platform

class TimeCardUI:
    def __init__(self):
        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("Face Recognition Time Card")
        
        # Auto detect screen size and go fullscreen
        self._setup_fullscreen()
        
        # Get actual screen dimensions after fullscreen
        self.root.update_idletasks()
        self.screen_width = self.root.winfo_width()
        self.screen_height = self.root.winfo_height()
        
        print(f"Screen resolution: {self.screen_width}x{self.screen_height}")
        
        # Thread-safe queues
        self.frame_queue = Queue(maxsize=2)
        self.event_queue = Queue(maxsize=10)
        self.status_queue = Queue(maxsize=10)
        
        # UI state variables
        self.current_frame = None
        self.current_mode = "camera"  # "camera" or "info"
        self.info_display_time = 5  # seconds to show info
        self.info_timer = None
        self.current_user_info = None
        
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
        
        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind('<Escape>', lambda e: self._on_closing())
        self.root.bind('<KeyPress-a>', lambda e: self._add_face_dialog())
        self.root.bind('<KeyPress-A>', lambda e: self._add_face_dialog())
        self.root.focus_set()
        
    def _setup_fullscreen(self):
        """Setup fullscreen based on platform"""
        try:
            if platform.system() == "Windows":
                self.root.state('zoomed')
            else:
                # Linux/Raspberry Pi
                self.root.attributes('-fullscreen', True)
                # Alternative for some systems
                # self.root.attributes('-zoomed', True)
        except Exception as e:
            print(f"Fullscreen setup failed: {e}")
            # Fallback to maximized window
            self.root.geometry("800x480")  # Common small screen size
    
    def _setup_ui(self):
        """Setup responsive UI layout"""
        # Configure main grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Main container frame
        self.main_frame = ctk.CTkFrame(self.root, fg_color="black")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create camera view
        self._create_camera_view()
        
        # Create info view (initially hidden)
        self._create_info_view()
        
        # Show camera view initially
        self._show_camera_view()
    
    def _create_camera_view(self):
        """Create camera display view"""
        self.camera_frame = ctk.CTkFrame(self.main_frame, fg_color="black")
        self.camera_frame.grid_columnconfigure(0, weight=1)
        self.camera_frame.grid_rowconfigure(1, weight=1)  # Camera takes most space
        
        # Title bar
        title_height = max(60, self.screen_height // 12)
        self.camera_title = ctk.CTkLabel(
            self.camera_frame,
            text="📹 FACE RECOGNITION SYSTEM",
            font=self._get_responsive_font(size_ratio=0.03, weight="bold"),
            height=title_height,
            fg_color=("gray20", "gray20")
        )
        self.camera_title.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Camera display
        self.camera_label = ctk.CTkLabel(
            self.camera_frame,
            text="📷 Waiting for camera...",
            font=self._get_responsive_font(size_ratio=0.025),
            fg_color="black"
        )
        self.camera_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Status bar
        status_height = max(40, self.screen_height // 18)
        self.camera_status = ctk.CTkLabel(
            self.camera_frame,
            text="✅ System Ready - Please look at the camera",
            font=self._get_responsive_font(size_ratio=0.02),
            height=status_height,
            fg_color=("gray30", "gray30")
        )
        self.camera_status.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
    
    def _create_info_view(self):
        """Create user info display view"""
        self.info_frame = ctk.CTkFrame(self.main_frame, fg_color="black")
        self.info_frame.grid_columnconfigure(0, weight=1)
        
        # Configure rows for info layout
        for i in range(6):
            self.info_frame.grid_rowconfigure(i, weight=1)
        
        # Success icon and title
        self.info_icon = ctk.CTkLabel(
            self.info_frame,
            text="✅",
            font=self._get_responsive_font(size_ratio=0.08),
            text_color="green"
        )
        self.info_icon.grid(row=0, column=0, pady=20)
        
        # User name
        self.info_name = ctk.CTkLabel(
            self.info_frame,
            text="John Doe",
            font=self._get_responsive_font(size_ratio=0.05, weight="bold"),
            text_color="white"
        )
        self.info_name.grid(row=1, column=0, pady=10)
        
        # User ID
        self.info_id = ctk.CTkLabel(
            self.info_frame,
            text="ID: 12345",
            font=self._get_responsive_font(size_ratio=0.03),
            text_color="lightgray"
        )
        self.info_id.grid(row=2, column=0, pady=5)
        
        # Time
        self.info_time = ctk.CTkLabel(
            self.info_frame,
            text="15:30:45",
            font=self._get_responsive_font(size_ratio=0.04, family="monospace"),
            text_color="cyan"
        )
        self.info_time.grid(row=3, column=0, pady=10)
        
        # Status message
        self.info_status = ctk.CTkLabel(
            self.info_frame,
            text="Attendance Recorded Successfully",
            font=self._get_responsive_font(size_ratio=0.025),
            text_color="green"
        )
        self.info_status.grid(row=4, column=0, pady=10)
        
        # Countdown
        self.info_countdown = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=self._get_responsive_font(size_ratio=0.02),
            text_color="gray"
        )
        self.info_countdown.grid(row=5, column=0, pady=10)
    
    def _get_responsive_font(self, size_ratio=0.03, weight="normal", family="default"):
        """Get responsive font size based on screen size"""
        base_size = min(self.screen_width, self.screen_height)
        font_size = max(12, int(base_size * size_ratio))
        
        if family == "monospace":
            return ctk.CTkFont(family="Courier", size=font_size, weight=weight)
        else:
            return ctk.CTkFont(size=font_size, weight=weight)
    
    def _show_camera_view(self):
        """Show camera view and hide info view"""
        self.info_frame.grid_remove()
        self.camera_frame.grid(row=0, column=0, sticky="nsew")
        self.current_mode = "camera"
    
    def _show_info_view(self):
        """Show info view and hide camera view"""
        self.camera_frame.grid_remove()
        self.info_frame.grid(row=0, column=0, sticky="nsew")
        self.current_mode = "info"
    
    def _ui_update_loop(self):
        """Main UI update loop"""
        while self.ui_thread_running:
            try:
                # Update frame
                try:
                    frame_data = self.frame_queue.get_nowait()
                    if self.current_mode == "camera":
                        self._update_camera_display(frame_data)
                except Empty:
                    pass
                
                # Process events
                try:
                    event_data = self.event_queue.get_nowait()
                    self._process_event(event_data)
                except Empty:
                    pass
                
                # Update status
                try:
                    status_data = self.status_queue.get_nowait()
                    self._update_status_display(status_data)
                except Empty:
                    pass
                
                # Update countdown if in info mode
                if self.current_mode == "info" and self.info_timer:
                    remaining = max(0, self.info_display_time - (time.time() - self.info_start_time))
                    if remaining > 0:
                        def update_countdown():
                            self.info_countdown.configure(text=f"Returning to camera in {remaining:.0f}s")
                        self.root.after(0, update_countdown)
                    else:
                        self._return_to_camera()
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"UI update error: {e}")
                time.sleep(0.1)
    
    def _update_camera_display(self, frame):
        """Update camera display with new frame"""
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Calculate responsive size maintaining aspect ratio
            frame_h, frame_w = frame.shape[:2]
            aspect_ratio = frame_w / frame_h
            
            # Use most of screen space for camera
            max_width = int(self.screen_width * 0.9)
            max_height = int(self.screen_height * 0.7)  # Leave space for title and status
            
            if aspect_ratio > max_width / max_height:
                # Limited by width
                display_width = max_width
                display_height = int(max_width / aspect_ratio)
            else:
                # Limited by height
                display_height = max_height
                display_width = int(max_height * aspect_ratio)
            
            # Resize frame
            frame_resized = cv2.resize(frame_rgb, (display_width, display_height))
            
            # Convert to PhotoImage
            pil_image = Image.fromarray(frame_resized)
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update display
            def update_label():
                self.camera_label.configure(image=photo, text="")
                self.camera_label.image = photo
            
            self.root.after(0, update_label)
            
        except Exception as e:
            print(f"Camera display error: {e}")
    
    def _process_event(self, event_data):
        """Process recognition event and potentially show info view"""
        name = event_data.get("name", "Unknown")
        is_real = event_data.get("is_real", False)
        
        # Only show info for real, recognized faces
        if is_real and name != "Unknown" and "FAKE" not in name:
            # Parse name and ID
            parts = name.split('_', 1)
            if len(parts) > 1:
                user_id = parts[0]
                user_name = parts[1]
            else:
                user_id = name
                user_name = name
            
            # Show user info
            self._show_user_info(user_id, user_name, "Processing...")
    
    def _show_user_info(self, user_id, user_name, status="Attendance Recorded"):
        """Show user information screen"""
        def update_info():
            # Update info display
            self.info_name.configure(text=user_name)
            self.info_id.configure(text=f"ID: {user_id}")
            
            # Current time
            current_time = time.strftime("%H:%M:%S")
            self.info_time.configure(text=current_time)
            
            # Status
            if "Processing" in status:
                self.info_status.configure(text="⏳ Processing attendance...", text_color="orange")
                self.info_icon.configure(text="⏳", text_color="orange")
            elif "success" in status.lower() or "recorded" in status.lower():
                self.info_status.configure(text="✅ Attendance Recorded Successfully", text_color="green")
                self.info_icon.configure(text="✅", text_color="green")
            else:
                self.info_status.configure(text="❌ Attendance Failed", text_color="red")
                self.info_icon.configure(text="❌", text_color="red")
            
            # Show info view
            self._show_info_view()
            
            # Start countdown
            self.info_start_time = time.time()
            
            # Cancel any existing timer
            if self.info_timer:
                self.info_timer.cancel()
            
            # Set timer to return to camera
            self.info_timer = threading.Timer(self.info_display_time, self._return_to_camera)
            self.info_timer.daemon = True
            self.info_timer.start()
        
        self.root.after(0, update_info)
    
    def _return_to_camera(self):
        """Return to camera view"""
        def return_to_cam():
            self._show_camera_view()
            self.info_timer = None
        
        self.root.after(0, return_to_cam)
    
    def _update_status_display(self, status_text):
        """Update status display"""
        def update_status():
            if self.current_mode == "camera":
                self.camera_status.configure(text=status_text)
        
        self.root.after(0, update_status)
    
    def _add_face_dialog(self):
        """Show dialog to add new face"""
        if self.current_frame is not None and self.face_recognition_system:
            dialog = ctk.CTkInputDialog(
                text="Enter name (format: ID_Name):",
                title="Add Face"
            )
            name = dialog.get_input()
            
            if name and name.strip():
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
                message = f"✅ Added: {name}" if success else f"❌ Failed to add: {name}"
                
                if not self.status_queue.full():
                    self.status_queue.put(message)
        except Exception as e:
            if not self.status_queue.full():
                self.status_queue.put(f"❌ Error: {str(e)}")
    
    # API Callbacks
    def on_attendance_success(self, attendance_data, response_data):
        """Handle successful attendance"""
        user_id = attendance_data['id_real']
        user_name = attendance_data['name']
        
        # Update info screen if currently showing this user
        if self.current_mode == "info":
            def update_success():
                self.info_status.configure(text="✅ Attendance Recorded Successfully", text_color="green")
                self.info_icon.configure(text="✅", text_color="green")
            self.root.after(0, update_success)
        
        # Update status
        if not self.status_queue.full():
            self.status_queue.put(f"✅ Recorded: {user_name}")
    
    def on_attendance_error(self, attendance_data, error_msg):
        """Handle attendance error"""
        user_id = attendance_data['id_real']
        user_name = attendance_data['name']
        
        # Update info screen if currently showing this user
        if self.current_mode == "info":
            def update_error():
                self.info_status.configure(text="❌ Attendance Recording Failed", text_color="red")
                self.info_icon.configure(text="❌", text_color="red")
            self.root.after(0, update_error)
        
        # Update status
        if not self.status_queue.full():
            self.status_queue.put(f"❌ Failed: {user_name}")
    
    # Thread-safe update methods
    def update_frame(self, frame):
        """Update camera frame"""
        self.current_frame = frame
        if not self.frame_queue.full():
            try:
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    pass
                self.frame_queue.put(frame)
            except:
                pass
    
    def add_event(self, name, is_real):
        """Add recognition event"""
        event = {
            "name": name,
            "is_real": is_real,
            "timestamp": time.time()
        }
        
        if not self.event_queue.full():
            try:
                self.event_queue.put(event)
            except:
                pass
    
    def should_quit(self):
        """Check if quit was requested"""
        return self.quit_requested
    
    def _on_closing(self):
        """Handle window closing"""
        self.quit_requested = True
        self.ui_thread_running = False
        
        # Cancel timers
        if self.info_timer:
            self.info_timer.cancel()
        
        # Stop API client
        if self.api_client:
            self.api_client.stop()
        
        # Wait for UI thread
        if self.ui_update_thread.is_alive():
            self.ui_update_thread.join(timeout=1.0)
        
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the UI"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"UI error: {e}")
            self._on_closing()
    
    def close(self):
        """Close the UI"""
        self._on_closing()

# Alias để tương thích với code cũ
FaceRecognitionTkinterUI = TimeCardUI