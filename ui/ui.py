import pygame
import time
import cv2
from api.AttendanceAPIClient import AttendanceAPIClient
import os  # Import os for path operations


class FaceRecognitionUI:
    def __init__(self, width=1280, height=720, hide_cursor=True):
        pygame.init()
        # It's good practice to initialize the font module explicitly,
        # though pygame.init() usually does it.
        pygame.font.init()

        self.width = width
        self.height = height
        self.window = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        if hide_cursor:
            pygame.mouse.set_visible(False)
        pygame.display.set_caption(
            "Face Recognition System - Hệ thống nhận diện khuôn mặt")  # Example UTF-8 in title

        # --- Font Loading for UTF-8 Support ---
        font_size = 24
        small_font_size = 18
        # Define path relative to the script location
        # Assumes 'fonts' directory is in the same place as the script
        try:
            # Construct the path to the font file
            # Use os.path.join for cross-platform compatibility
            # Gets the directory where the script is located
            base_path = os.path.dirname(__file__)
            # Adjust filename if needed
            font_path = os.path.join(
                base_path, "fonts", "NotoSans-Regular.ttf")

            if not os.path.exists(font_path):
                # If not found relative to script, maybe it's relative to CWD?
                font_path = os.path.join("fonts", "NotoSans-Regular.ttf")
                if not os.path.exists(font_path):
                    raise FileNotFoundError(
                        f"Font file not found at expected paths.")

            print(f"Loading font: {font_path}")  # Debug print
            self.font = pygame.font.Font(font_path, font_size)
            self.small_font = pygame.font.Font(font_path, small_font_size)
            print("Custom font loaded successfully.")
        except (FileNotFoundError, pygame.error) as e:
            print(
                f"Warning: Could not load custom font ('{font_path}'). Error: {e}")
            print(
                "Falling back to default system font. Unicode characters might not display correctly.")
            # Fallback to a system font (less reliable for specific Unicode)
            self.font = pygame.font.SysFont("Arial", font_size)
            self.small_font = pygame.font.SysFont("Arial", small_font_size)
        # --- End Font Loading ---

        self.bg_color = (30, 30, 30)
        self.frame_surface = None
        self.event_log = []
        self.recognition_results = []

        # For UI feedback on attendance status
        # key: id_real, value: {"status": "success/error", "message": str, "timestamp": float}
        self.attendance_status = {}

        self.original_frame_width = 640
        self.original_frame_height = 480

        self.user_cooldowns = {}
        self.display_time = 10  # seconds
        self.cooldown_period = 10
        self.current_time = time.time()

        self.key_handlers = {}
        self.quit_requested = False

        # Text input state for adding faces
        self.input_active = False
        self.input_text = ""
        self.input_purpose = None  # What the input is for (e.g., "add_face")
        self.captured_frame = None  # Store the frame where the face was detected

        #style input
        self.input_color_active = (75, 0, 130)
        self.input_color_inactive = (100, 100, 100)
        self.input_rect = pygame.Rect(self.width // 4, self.height // 2 - 20, self.width // 2, 40)

        self.face_recognition_system = None
        
        # Initialize the API client with callbacks
        self.api_client = AttendanceAPIClient()
        self.api_client.register_callbacks(
            success_callback=self.on_attendance_success,
            error_callback=self.on_attendance_error
        )
        self.api_client.start()

    def on_attendance_success(self, attendance_data, response_data):
        """Callback for successful attendance recording"""
        id_real = attendance_data['id_real']
        name = attendance_data['name']

        # Update status with success message
        self.attendance_status[id_real] = {
            "status": "success",
            "message": f"✅ Recorded: {name}",
            "timestamp": time.time(),
            "name": name
        }

    def on_attendance_error(self, attendance_data, error_msg):
        """Callback for attendance recording error"""
        id_real = attendance_data['id_real']
        name = attendance_data['name']

        # Update status with error message
        self.attendance_status[id_real] = {
            "status": "error",
            "message": f"❌ Failed: {name}",
            "timestamp": time.time(),
            "name": name
        }
    def draw_attendance_status(self):
        """Draw attendance status notifications on the UI"""
        now = time.time()
        
        # Remove old status messages (keep for longer - 60 seconds instead of 10)
        expired_ids = []
        attendance_display_time = 60  # Show attendance status for 60 seconds
        
        for id_real, status_data in self.attendance_status.items():
            if now - status_data["timestamp"] > attendance_display_time:
                expired_ids.append(id_real)
        
        for id_real in expired_ids:
            del self.attendance_status[id_real]
        
        # Update the status_messages dictionary for draw_ui to use
        self.status_messages = {}
        for id_real, status_data in self.attendance_status.items():
            message_prefix = "✅ Điểm danh: " if status_data["status"] == "success" else "❌ Lỗi: "
            self.status_messages[id_real] = {
                "color": (0, 255, 0) if status_data["status"] == "success" else (255, 0, 0),
                "message": status_data["message"]
            }
    def register_key_handler(self, key, handler_function):
        """Register a function to be called when a specific key is pressed"""
        self.key_handlers[key] = handler_function

    def handle_events(self):
        """Handle all pygame events in one place"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_requested = True
                return
            elif event.type == pygame.KEYDOWN:
                if self.input_active:
                    # Let the process_event method handle the input
                    self.process_event(event)
                else:
                    if event.key == pygame.K_ESCAPE:
                        self.quit_requested = True
                        return
                    elif event.key == pygame.K_a:
                        # Start adding face - store the current frame later
                        self.input_active = True
                        self.input_text = ""
                        self.input_purpose = "add_face"
                        # The frame will be captured when the UI is updated next
                    elif event.key in self.key_handlers:
                        # Call the registered handler
                        self.key_handlers[event.key]()

    def should_quit(self):
        """Check if quit was requested"""
        return self.quit_requested

    # Removed redundant handle_quit method - use should_quit() and handle_events()

    def update_frame(self, frame):
        """Cập nhật khung hình mới từ OpenCV (BGR numpy)"""
        self.original_frame_height, self.original_frame_width = frame.shape[:2]
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        display_width = int(self.width * 0.65)
        # Maintain aspect ratio for scaling
        original_aspect = self.original_frame_width / self.original_frame_height
        display_height = int(display_width / original_aspect)
        # Ensure scaled height doesn't exceed window height
        if display_height > self.height:
            display_height = self.height
            display_width = int(display_height * original_aspect)

        # frame_surface = pygame.transform.scale(frame_surface, (display_width, display_height))
        frame_surface = pygame.transform.smoothscale(frame_surface, (display_width, display_height))
        self.frame_surface = frame_surface

    def update_recognition_results(self, results):
        """Cập nhật kết quả nhận diện khuôn mặt"""
        self.recognition_results = results

    def add_event(self, name, is_real):
        """Add recognition event with cooldown check and grid positioning"""
        self.current_time = time.time()

        if name in self.user_cooldowns:
            last_time = self.user_cooldowns[name]
            time_elapsed = self.current_time - last_time
            if time_elapsed < self.cooldown_period:
                return  # Cooldown active, skip
        
        self.user_cooldowns[name] = self.current_time

        label = name
        status = "REAL" if is_real else "FAKE"
        timestamp = self.current_time
        
        # Add the event to the beginning of the log
        # This maintains most recent first order
        self.event_log.insert(0, {"label": label, "status": status, "timestamp": timestamp})
        
        # Limit event log size to prevent memory growth over time
        max_events = 100  # Reasonable upper bound
        if len(self.event_log) > max_events:
            self.event_log = self.event_log[:max_events]
        
        # Process real faces for attendance
        if is_real and "FAKE" not in name and name != "Unknown":
            parts = name.split('_', 1)
            # Check if first part is alphanumeric ID
            if len(parts) > 1 and parts[0].isalnum():
                id_real = parts[0]
                full_name = parts[1]
            else:
                id_real = name
                full_name = name
                
            print(f"✅ Sending attendance for ID: {id_real}, Name: {full_name}")
            self.api_client.mark_attendance(id_real, full_name)

    def draw_recognition_results(self):
        """Vẽ kết quả nhận diện khuôn mặt trên Pygame Surface"""
        if not self.frame_surface or not self.recognition_results:
            return

        # Ensure frame surface exists before getting dimensions
        if not self.frame_surface:
            return
        surface_width = self.frame_surface.get_width()
        surface_height = self.frame_surface.get_height()

        # Check for division by zero if original dimensions are somehow zero
        if self.original_frame_width == 0 or self.original_frame_height == 0:
            return

        scale_x = surface_width / self.original_frame_width
        scale_y = surface_height / self.original_frame_height

        for result in self.recognition_results:
            x1, y1, x2, y2 = result["box"]
            # Ensure name is a string
            # Use get with default, ensure string
            name = str(result.get("name", "Unknown"))
            confidence = result.get("confidence", 0.0)  # Use get with default
            # Default to True if key missing
            is_real = result.get("is_real", True)

            x1_scaled = int(x1 * scale_x)
            y1_scaled = int(y1 * scale_y)
            x2_scaled = int(x2 * scale_x)
            y2_scaled = int(y2 * scale_y)

            color = (0, 255, 0) if is_real else (255, 0, 0)

            pygame.draw.rect(self.frame_surface, color, (x1_scaled,
                             y1_scaled, x2_scaled-x1_scaled, y2_scaled-y1_scaled), 2)

            # Render text using the loaded (hopefully UTF-8) font
            # Python 3 strings are unicode, just pass them to render
            label = f"{name}: {confidence:.2f}"
            text_surface = self.small_font.render(
                label, True, color)  # Antialias = True
            # Position text above the box, ensure it stays within bounds
            # Small gap
            text_y = max(0, y1_scaled - text_surface.get_height() - 2)
            self.frame_surface.blit(text_surface, (x1_scaled, text_y))

            if "spoof_score" in result:
                score = result["spoof_score"]
                spoof_label = f"Real: {score:.2f}" if is_real else f"FAKE: {score:.2f}"
                spoof_text = self.small_font.render(spoof_label, True, color)
                # Position below the box
                text_y_spoof = min(
                    surface_height - spoof_text.get_height(), y2_scaled + 5)
                self.frame_surface.blit(spoof_text, (x1_scaled, text_y_spoof))

    def draw_ui(self):
        """Draw the complete user interface with grid layout for recognition events"""
        # Make sure attendance status is processed before drawing UI
        self.draw_attendance_status()  # <-- Add this line to update status_messages
        
        self.window.fill(self.bg_color)
        
        # Draw camera frame on the left with proper alignment
        if self.frame_surface:
            # Draw recognition results on frame
            self.draw_recognition_results() #Bỏ đi nếu cần
            
            # Calculate position to center the frame vertically
            frame_width = self.frame_surface.get_width()
            frame_height = self.frame_surface.get_height()
            
            x_pos = 10  # Left padding
            y_pos = (self.height - frame_height) // 2  # Vertical centering
            
            # Draw background for the camera frame
            pygame.draw.rect(self.window, (40, 40, 40), 
                            (x_pos - 10, y_pos - 10, 
                            frame_width + 20, frame_height + 20))
            
            # Display the frame at calculated position
            self.window.blit(self.frame_surface, (x_pos, y_pos))
        
        # Draw the right panel with grid layout
        panel_x = int(self.width * 0.68)
        panel_y = 20
        panel_width = self.width - panel_x - 20
        panel_height = self.height - 40
        
        # Draw background for the right panel
        pygame.draw.rect(self.window, (50, 50, 50), (panel_x - 20, panel_y, panel_width, panel_height))
        
        # Draw panel title
        title = self.render_text("Recent Recognitions", self.font, (255, 255, 255))
        self.window.blit(title, (panel_x, panel_y + 5))
        
        # Grid configuration
        now = time.time()
        grid_start_y = panel_y + 50
        cell_width = panel_width // 2 - 10
        cell_height = 75
        max_rows = (panel_height - 50) // (cell_height + 5)
        
        # Filter event log to only show recent events
        recent_events = [e for e in self.event_log if now - e["timestamp"] <= self.display_time]
        
        # Arrange events in a grid (2 columns)
        for i, entry in enumerate(recent_events[:max_rows * 2]):  # Limit to what can fit
            row = i // 2
            col = i % 2
            
            # Calculate cell position
            cell_x = panel_x + col * (cell_width + 10)
            cell_y = grid_start_y + row * (cell_height + 5)
            
            # Draw cell background
            status_color = (0, 100, 0) if entry["status"] == "REAL" else (100, 0, 0)
            pygame.draw.rect(self.window, status_color, (cell_x, cell_y, cell_width, cell_height), border_radius=5)
            pygame.draw.rect(self.window, (70, 70, 70), (cell_x, cell_y, cell_width, cell_height), 2, border_radius=5)
            
            # Draw person name
            text_color = (255, 255, 255)
            name_text = self.render_text(entry["label"], self.font, text_color)
            self.window.blit(name_text, (cell_x + 10, cell_y + 10))
            
            # Draw recognition status
            # status_text = self.render_text(entry["status"], self.small_font, text_color)
            # self.window.blit(status_text, (cell_x + 10, cell_y + 40))
            
            # Get ID from label
            parts = entry["label"].split('_', 1)
            entry_id = parts[0] if len(parts) > 1 else entry["label"]
            
            # Draw attendance status if available
            if hasattr(self, 'status_messages') and entry_id in self.status_messages:
                status_info = self.status_messages[entry_id]
                status_text = self.render_text(status_info["message"], self.small_font, text_color)
                self.window.blit(status_text, (cell_x + 10, cell_y + cell_height - 25))
            else:
                # Show "Pending..." if real face but no attendance status yet
                if entry["status"] == "REAL" and entry["label"] != "Unknown":
                    pending_text = self.render_text("Đang xử lý...", self.small_font, (200, 200, 200))
                    self.window.blit(pending_text, (cell_x + 10, cell_y + cell_height - 25))
        
        # Draw input interface if active
        if self.input_active:
            self.draw_text_input()
        
        # Update the display
        pygame.display.update()

    # handle_quit is integrated into handle_events now
    def render_text(self, text, font, color):
        """Safely render text with fallback for Vietnamese characters"""
        try:
            # Try to render with the current font
            return font.render(text, True, color)
        except Exception as e:
            print(f"Error rendering text '{text}': {e}")
            try:
                # Try transliteration as fallback
                ascii_text = self.transliterate_vietnamese(text)
                return font.render(ascii_text, True, color)
            except Exception as e2:
                print(f"Fallback rendering also failed: {e2}")
                # Last resort: return a minimal surface with basic text
                return font.render("???", True, color)

    def transliterate_vietnamese(self, text):
        """Convert Vietnamese characters to ASCII equivalents"""
        vietnamese_chars = 'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰự'
        ascii_chars = 'AAAAEEEIIOOOOUUYaaaaeeeiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUu'
        
        result = ''
        for char in text:
            if char in vietnamese_chars:
                idx = vietnamese_chars.index(char)
                result += ascii_chars[idx]
            else:
                result += char
        return result
    def close(self):
        """Close pygame and any resources"""
        print("Closing UI and stopping API client...")
        if self.api_client:
            self.api_client.stop()
        pygame.quit()
    
    def process_event(self, event):
        """Process pygame events specifically for the UI"""
        if self.input_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # Submit the text input
                    if self.input_purpose == "add_face" and self.captured_frame is not None:
                        # Pass reference to the face system
                        self.finish_add_face()
                    self.input_active = False
                    self.input_text = ""
                    self.input_purpose = None
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif event.key == pygame.K_ESCAPE:
                    # Cancel input
                    self.input_active = False
                    self.input_text = ""
                    self.input_purpose = None
                    self.captured_frame = None
                else:
                    # Add character to input text - proper UTF-8 handling
                    if event.unicode:  # This handles unicode properly
                        self.input_text += event.unicode
            return True  # Event was handled by this method
        return False  # Event was not handled by this method

    def finish_add_face(self):
        """Complete the face addition process"""
        name = self.input_text.strip()
        if name and self.captured_frame is not None:
            if hasattr(self, 'face_recognition_system') and self.face_recognition_system:
                print(f"Adding face: {name}")
                success = self.face_recognition_system.add_face_to_database(self.captured_frame, name)
                if success:
                    self.add_status_message(name, "Face added successfully!")
                else:
                    self.add_status_message(name, "Failed to add face")
            else:
                print("Error: No face_recognition_system reference available")
                self.add_status_message(name, "System error: Cannot add face")
        self.captured_frame = None

    def add_status_message(self, name, message):
        """Add a status message to the UI"""
        # Extract ID from name if possible
        parts = name.split('_', 1)
        if len(parts) > 1 and parts[0].isalnum():
            id_real = parts[0]
        else:
            id_real = name
            
        self.attendance_status[id_real] = {
            "status": "success" if "success" in message.lower() else "error",
            "message": message,
            "timestamp": time.time(),
            "name": name
        }

    def start_face_input(self, frame):
        """Initialize the text input for adding a face"""
        self.input_active = True
        self.input_text = ""
        self.input_purpose = "add_face"
        self.captured_frame = frame.copy()
    def draw_text_input(self):
        """Draw the text input interface"""
        if not self.input_active:
            return
            
        # Dim background
        dim_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        dim_surface.fill((0, 0, 0, 180))  # Semi-transparent black
        self.window.blit(dim_surface, (0, 0))
        
        # Draw input box
        pygame.draw.rect(self.window, self.input_color_active if self.input_active else self.input_color_inactive, self.input_rect, 2)
        
        # Draw input text
        input_surface = self.font.render(self.input_text, True, (255, 255, 255))
        self.window.blit(input_surface, (self.input_rect.x + 5, self.input_rect.y + 5))
        
        # Draw purpose text
        if self.input_purpose == "add_face":
            purpose_text = self.font.render("Enter name for the face (format: ID_Name):", True, (255, 255, 255))
            self.window.blit(purpose_text, (self.input_rect.x, self.input_rect.y - 40))
            
            # Draw instruction text
            instruction_text = self.font.render("Press ENTER to confirm, ESC to cancel", True, (200, 200, 200))
            self.window.blit(instruction_text, (self.input_rect.x, self.input_rect.y + 50))
            
            # Show preview of captured face if available
            if self.captured_frame is not None and hasattr(self, 'face_recognition_system'):
                # Process the frame to show the detected face
                results = self.face_recognition_system.process_image(self.captured_frame)
                if results:
                    # Extract and display the face
                    x1, y1, x2, y2 = results[0]["box"]
                    face_img = self.captured_frame[y1:y2, x1:x2]
                    face_img = cv2.resize(face_img, (120, 120))
                    face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                    face_surface = pygame.surfarray.make_surface(face_rgb.swapaxes(0, 1))
                    self.window.blit(face_surface, (self.input_rect.x - 140, self.input_rect.y - 40))