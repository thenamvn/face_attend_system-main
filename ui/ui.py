import cv2
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import threading
import time
import numpy as np
from queue import Queue, Empty
from api.AttendanceAPIClient import AttendanceAPIClient

class FaceRecognitionTkinterUI:
    def __init__(self, width=752, height=433):
        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.width = width
        self.height = height
        
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("Face Recognition")
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        
        # Thread-safe queues for UI updates
        self.frame_queue = Queue(maxsize=2)
        
        # UI state variables
        self.current_frame = None
        self.recognition_results = []
        self.user_cooldowns = {}
        self.cooldown_period = 30
        
        # SIMPLIFIED: Card tracking variables
        self.active_face_card = None
        self.current_face_id = None
        self.card_display_time = 5.0  # 3 seconds display time
        self.card_creation_lock = threading.Lock()
        
        # Attendance tracking
        self.attendance_sent = {}
        self.attendance_reset_time = 300  # 5 minutes
        
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
        """Setup UI matching PyQt design"""
        # Configure main grid
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Camera frame (left side)
        self.camera_frame = ctk.CTkFrame(
            self.root, 
            fg_color="#1a1a1a",
            corner_radius=20
        )
        self.camera_frame.grid(row=0, column=0, padx=16, pady=32, sticky="nsew")
        self.camera_frame.grid_columnconfigure(0, weight=1)
        self.camera_frame.grid_rowconfigure(0, weight=1)
        
        # Camera display
        self.camera_label = ctk.CTkLabel(
            self.camera_frame,
            text="Waiting for camera...",
            font=ctk.CTkFont(size=16),
            text_color="white"
        )
        self.camera_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # ID GroupBox (right side)
        self.id_group = ctk.CTkFrame(
            self.root,
            fg_color="#2b2b2b",
            corner_radius=10,
            width=211,
            height=361
        )
        self.id_group.grid(row=0, column=1, padx=(0, 16), pady=32, sticky="nsew")
        self.id_group.grid_propagate(False)
        
        # ID title
        self.id_title = ctk.CTkLabel(
            self.id_group,
            text="ID",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        self.id_title.place(x=10, y=5)
        
        # Avatar image area
        self.avatar_frame = ctk.CTkFrame(
            self.id_group,
            fg_color="#3a3a3a",
            corner_radius=20,
            width=131,
            height=141
        )
        self.avatar_frame.place(x=40, y=30)
        self.avatar_frame.pack_propagate(False)
        
        # Avatar image label
        self.avatar_label = ctk.CTkLabel(
            self.avatar_frame,
            text="👤",
            font=ctk.CTkFont(size=40),
            text_color="#888888",
            width=131,
            height=141
        )
        self.avatar_label.pack(expand=True, fill="both")
        
        # Name field
        self.name_entry = ctk.CTkEntry(
            self.id_group,
            placeholder_text="Họ và tên",
            font=ctk.CTkFont(size=12),
            corner_radius=10,
            width=171,
            height=31,
            justify="center",
            state="readonly"
        )
        self.name_entry.place(x=20, y=199)
        
        # ID field
        self.id_entry = ctk.CTkEntry(
            self.id_group,
            placeholder_text="Mã sinh viên",
            font=ctk.CTkFont(size=12),
            corner_radius=10,
            width=171,
            height=31,
            justify="center",
            state="readonly"
        )
        self.id_entry.place(x=20, y=259)
        
        # Status label
        self.status_display = ctk.CTkLabel(
            self.id_group,
            text="Spoof Status",
            font=ctk.CTkFont(size=10),
            text_color="white",
            fg_color="#3a3a3a",
            width=81,
            height=41,
            corner_radius=5
        )
        self.status_display.place(x=70, y=300)
        
        # Add Face button
        self.add_face_button = ctk.CTkButton(
            self.root,
            text="Add Face (A)",
            command=self._add_face_dialog,
            font=ctk.CTkFont(size=12),
            width=100,
            height=30
        )
        self.add_face_button.place(x=10, y=10)
        
    def _create_id_card(self, person_name, face_data, face_image=None):
        """Create/Update ID card with attendance status logic"""
        with self.card_creation_lock:
            try:
                # Extract info
                parts = person_name.split('_', 1)
                if len(parts) > 1:
                    id_real = parts[0]
                    full_name = parts[1]
                else:
                    id_real = person_name
                    full_name = face_data.get("full_name", person_name)
                
                # Update avatar image
                if face_image is not None:
                    self._update_avatar_image(face_image)
                
                # Update text fields
                self.name_entry.configure(state="normal")
                self.name_entry.delete(0, "end")
                self.name_entry.insert(0, full_name)
                self.name_entry.configure(state="readonly")
                
                self.id_entry.configure(state="normal")
                self.id_entry.delete(0, "end")
                self.id_entry.insert(0, id_real)
                self.id_entry.configure(state="readonly")
                
                # CHECK ATTENDANCE STATUS và set status accordingly
                current_time = time.time()
                if id_real in self.attendance_sent:
                    time_since_sent = current_time - self.attendance_sent[id_real]
                    if time_since_sent < self.attendance_reset_time:
                        # Attendance đã được gửi trong 5 phút qua
                        self.status_display.configure(
                            text="✅ Đã điểm danh",
                            text_color="green"
                        )
                    else:
                        # Attendance cũ, có thể điểm danh lại
                        self.status_display.configure(
                            text="Đang xử lý...",
                            text_color="orange"
                        )
                else:
                    # Chưa điểm danh
                    self.status_display.configure(
                        text="Đang xử lý...",
                        text_color="orange"
                    )
                
                # Store card data with creation time
                self.active_face_card = {
                    "person_name": person_name,
                    "face_data": face_data,
                    "created_time": time.time(),
                    "id_real": id_real,
                    "full_name": full_name
                }
                
                # Schedule card removal after display time
                def clear_after_timeout():
                    time.sleep(self.card_display_time)
                    self.root.after(0, self._clear_id_card)
                
                threading.Thread(target=clear_after_timeout, daemon=True).start()
                
                print(f"✅ Created ID card for {person_name} (will clear in {self.card_display_time}s)")
                
            except Exception as e:
                print(f"Error creating card: {e}")
    
    def _update_avatar_image(self, face_image):
        """Update avatar image"""
        try:
            face_resized = cv2.resize(face_image, (131, 141))
            face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(face_rgb)
            photo = ImageTk.PhotoImage(pil_image)
            
            self.avatar_label.configure(image=photo, text="")
            self.avatar_label.image = photo
            
        except Exception as e:
            print(f"Error updating avatar: {e}")
    
    def _clear_id_card(self):
        """Clear ID card"""
        try:
            # Reset avatar
            self.avatar_label.configure(image="", text="👤")
            self.avatar_label.image = None
            
            # Clear text fields
            self.name_entry.configure(state="normal")
            self.name_entry.delete(0, "end")
            self.name_entry.configure(state="readonly")
            
            self.id_entry.configure(state="normal")
            self.id_entry.delete(0, "end")
            self.id_entry.configure(state="readonly")
            
            # Reset status
            self.status_display.configure(
                text="Spoof Status",
                text_color="white"
            )
            
            # Clear card data
            self.active_face_card = None
            self.current_face_id = None
            
            print("🗑️ Cleared ID card")
            
        except Exception as e:
            print(f"Error clearing card: {e}")
    
    def _extract_face_from_frame(self, frame, box):
        """Extract face region from frame"""
        try:
            x1, y1, x2, y2 = box
            padding = 20
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(frame.shape[1], x2 + padding)
            y2 = min(frame.shape[0], y2 + padding)
            
            face_crop = frame[y1:y2, x1:x2]
            return face_crop
        except Exception as e:
            print(f"Error extracting face: {e}")
            return None
    
    def _ui_update_loop(self):
        """Simplified UI update loop"""
        while self.ui_thread_running:
            try:
                # Update camera frame
                try:
                    frame = self.frame_queue.get_nowait()
                    self._update_camera_display(frame)
                except Empty:
                    pass
                
                # Clean up old attendance records
                self._cleanup_attendance_tracking()
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"UI update error: {e}")
                time.sleep(0.1)
    
    def _cleanup_attendance_tracking(self):
        """Clean up old attendance tracking"""
        current_time = time.time()
        expired_ids = []
        
        for face_id, sent_time in self.attendance_sent.items():
            if current_time - sent_time > self.attendance_reset_time:
                expired_ids.append(face_id)
        
        for face_id in expired_ids:
            del self.attendance_sent[face_id]
    
    def _update_camera_display(self, frame):
        """Update camera display"""
        def update_display():
            try:
                target_width = 471
                target_height = 361
                
                h, w = frame.shape[:2]
                aspect_ratio = w / h
                
                if aspect_ratio > target_width / target_height:
                    display_width = target_width
                    display_height = int(target_width / aspect_ratio)
                else:
                    display_height = target_height
                    display_width = int(target_height * aspect_ratio)
                
                display_frame = cv2.resize(frame, (display_width, display_height))
                display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(display_frame)
                photo = ImageTk.PhotoImage(pil_image)
                
                self.camera_label.configure(image=photo, text="")
                self.camera_label.image = photo
                
            except Exception as e:
                print(f"Camera display error: {e}")
        
        self.root.after(0, update_display)
    
    def _add_face_dialog(self):
        """Dialog to add new face"""
        if self.current_frame is None:
            print("⚠️ No camera frame available")
            return
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Add New Face")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 100,
            self.root.winfo_rooty() + 100
        ))
        
        name_label = ctk.CTkLabel(dialog, text="Enter name (format: ID_FullName):")
        name_label.pack(pady=10)
        
        name_entry = ctk.CTkEntry(dialog, width=300, placeholder_text="e.g., 22110158_Nguyen Van Nam")
        name_entry.pack(pady=10)
        name_entry.focus()
        
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=20)
        
        def add_face():
            name = name_entry.get().strip()
            if name and self.face_recognition_system:
                dialog.destroy()
                threading.Thread(
                    target=self._add_face_worker,
                    args=(self.current_frame.copy(), name),
                    daemon=True
                ).start()
            else:
                print("⚠️ Please enter a valid name")
        
        add_button = ctk.CTkButton(button_frame, text="Add Face", command=add_face)
        add_button.pack(side=tk.LEFT, padx=10)
        
        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)
        
        name_entry.bind("<Return>", lambda e: add_face())
    
    def _add_face_worker(self, frame, name):
        """Worker thread for adding face"""
        try:
            success = self.face_recognition_system.add_face_to_database(frame, name)
            status = f"✅ Successfully added {name}" if success else f"❌ Failed to add {name}"
            print(status)
        except Exception as e:
            print(f"❌ Error adding {name}: {str(e)}")
    
    # Thread-safe methods for external updates
    def update_frame(self, frame):
        """Update camera frame (thread-safe)"""
        self.current_frame = frame
        if not self.frame_queue.full():
            try:
                self.frame_queue.put(frame)
            except:
                pass
    
    def update_recognition_results(self, results):
        """IMPROVED: Update recognition results with proper face image capture"""
        # Find the best real face
        best_face = None
        for result in results:
            name = result.get("name", "Unknown")
            is_real = result.get("is_real", True)
            
            if is_real and name != "Unknown" and "FAKE" not in name:
                best_face = result
                break
        
        if best_face:
            name = best_face.get("name")
            box = best_face.get("box")
            
            # Extract face ID
            parts = name.split('_', 1)
            face_id = parts[0] if len(parts) > 1 else name
            
            # ALWAYS extract face image when detected
            face_image = None
            if box and self.current_frame is not None:
                face_image = self._extract_face_from_frame(self.current_frame, box)
            
            # ONLY CREATE CARD IF IT'S A DIFFERENT FACE
            if self.current_face_id != face_id:
                self.current_face_id = face_id
                
                # Get face data from database
                face_data = {}
                if hasattr(self, 'face_recognition_system') and self.face_recognition_system:
                    face_db = getattr(self.face_recognition_system, 'face_db', {})
                    if name in face_db:
                        face_data = face_db[name]
                
                # Create card in main thread với face image
                def create_card():
                    self._create_id_card(name, face_data, face_image)
                
                self.root.after(0, create_card)
    
    def add_event(self, name, is_real):
        """Add recognition event with IMPROVED attendance tracking"""
        current_time = time.time()
        
        # Extract ID for tracking
        parts = name.split('_', 1)
        face_id = parts[0] if len(parts) > 1 else name
        
        # CHECK IF ATTENDANCE ALREADY SENT
        if face_id in self.attendance_sent:
            time_since_sent = current_time - self.attendance_sent[face_id]
            if time_since_sent < self.attendance_reset_time:
                print(f"⏰ Attendance already sent for {face_id}, skipping (sent {time_since_sent:.0f}s ago)")
                return
        
        # CHECK USER COOLDOWN (chỉ cho việc gửi attendance, không ảnh hưởng card)
        if name in self.user_cooldowns:
            if current_time - self.user_cooldowns[name] < self.cooldown_period:
                print(f"⏰ User cooldown active for {name}, skipping")
                return
        
        # UPDATE COOLDOWN
        self.user_cooldowns[name] = current_time
        
        # PROCESS ATTENDANCE FOR REAL FACES
        if is_real and "FAKE" not in name and name != "Unknown":
            if len(parts) > 1 and parts[0].isalnum():
                id_real = parts[0]
                full_name = parts[1]
            else:
                id_real = name
                full_name = name
            
            # MARK AS SENT TRƯỚC KHI GỬI
            self.attendance_sent[face_id] = current_time
            
            print(f"✅ Sending attendance for ID: {id_real}, Name: {full_name}")
            self.api_client.mark_attendance(id_real, full_name)
            
            # UPDATE STATUS if card is currently showing this person
            if (self.active_face_card and 
                self.active_face_card.get("id_real") == id_real):
                def update_status():
                    if self.active_face_card and self.active_face_card.get("id_real") == id_real:
                        self.status_display.configure(
                            text="⏳ Đang gửi...",
                            text_color="yellow"
                        )
                self.root.after(0, update_status)
    
    def on_attendance_success(self, attendance_data, response_data):
        """Handle successful attendance"""
        def update_status():
            # Chỉ update nếu card hiện tại là của người này
            person_id = attendance_data.get('id_real', 'Unknown')
            if (self.active_face_card and 
                self.active_face_card.get("id_real") == person_id):
                
                api_message = response_data.get('message', 'Thành công')
                if 'First attendance' in api_message:
                    status_text = "✅ Điểm danh đầu"
                elif 'updated' in api_message:
                    status_text = "✅ Cập nhật"
                else:
                    status_text = "✅ Thành công"
                    
                self.status_display.configure(
                    text=status_text,
                    text_color="green"
                )
        
        self.root.after(0, update_status)
        
        person_name = attendance_data.get('name', 'Unknown')
        person_id = attendance_data.get('id_real', 'Unknown')
        api_message = response_data.get('message', 'Success')
        
        print(f"✅ Attendance success for {person_name} (ID: {person_id}) - {api_message}")

    def on_attendance_error(self, attendance_data, error_msg):
        """Handle attendance error"""
        def update_status():
            # Chỉ update nếu card hiện tại là của người này
            person_id = attendance_data.get('id_real', 'Unknown')
            if (self.active_face_card and 
                self.active_face_card.get("id_real") == person_id):
                
                self.status_display.configure(
                    text="❌ Thất bại",
                    text_color="red"
                )
        
        self.root.after(0, update_status)
        
        # Remove from sent tracking on error so it can be retried
        face_id = attendance_data.get('id_real')
        if face_id and face_id in self.attendance_sent:
            del self.attendance_sent[face_id]
        
        person_name = attendance_data.get('name', 'Unknown')
        person_id = attendance_data.get('id_real', 'Unknown')
        
        print(f"❌ Attendance failed for {person_name} (ID: {person_id}): {error_msg}")
    
    def should_quit(self):
        return self.quit_requested
    
    def _on_closing(self):
        print("🔄 Closing application...")
        self.quit_requested = True
        self.ui_thread_running = False
        
        if hasattr(self, 'api_client'):
            try:
                self.api_client.stop()
            except Exception as e:
                print(f"Error stopping API client: {e}")
        
        time.sleep(0.5)
        
        try:
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Error during window cleanup: {e}")
    
    def run(self):
        self.root.mainloop()
    
    def close(self):
        self._on_closing()