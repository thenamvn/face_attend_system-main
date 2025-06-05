import cv2
import os
from detector.ultralight import FaceDetector
from aligner.mediapipe_aligner import FaceAligner
from normalizer.image_preprocess import normalize_face
from embedder.mobilefacenet_embedder import FaceEmbedder
from verifier.face_verifier import FaceVerifier
from database.face_database_manager import FaceDatabaseManager
from antispoof.Fasnet import Fasnet
from thread.thread import VideoCaptureThread
from ui.ui import FaceRecognitionUI
import pygame
import numpy as np
import time
import threading

# Import GPIO for Raspberry Pi motion detection
try:
    from gpiozero import MotionSensor
    from signal import pause
    GPIO_AVAILABLE = True
    print("✅ Motion sensor support available")
except ImportError:
    print("⚠️ gpiozero module not found. Motion detection will be simulated.")
    GPIO_AVAILABLE = False

class FaceRecognitionSystem:
    def __init__(self, models_dir="model"):
        # Initialize components with correct model paths
        detector_model = os.path.join(models_dir, "version-RFB-320_without_postprocessing.tflite")
        embedder_model = os.path.join(models_dir, "mobilefacenet.tflite")
        self.db_path = "./face_db.pkl"

        # Initialize Fastnet
        first_model = os.path.join(models_dir, "2.7_80x80_MiniFASNetV2.pth")
        second_model = os.path.join(models_dir, "4_0_0_80x80_MiniFASNetV1SE.pth")
        self.fasnet = Fasnet(first_model, second_model)
        # Increase confidence threshold to reduce false positives
        self.detector = FaceDetector(detector_model, conf_threshold=0.7)
        self.aligner = FaceAligner()
        self.embedder = FaceEmbedder(embedder_model)
        self.db_manager = FaceDatabaseManager(
            image_dir="./face_database",
            backup_path= self.db_path,
            detector=self.detector,
            aligner=self.aligner,
            embedder=self.embedder
        )
        
        # Load face database if exists
        self.face_db = self.db_manager.face_db
        print(f"Face database loaded with {len(self.face_db)} entries.")
        self.verifier = FaceVerifier(self.face_db)
    
    
    def process_image(self, image):
        # 1. Detect faces
        boxes, scores = self.detector.detect_faces(image)
        
        # Apply non-maximum suppression
        if len(boxes) > 0:
            indices = cv2.dnn.NMSBoxes( 
                boxes.tolist(), 
                scores.tolist(), 
                score_threshold=0.5, 
                nms_threshold=0.3
            )
            
            if len(indices) > 0:
                # Handle the different return types based on OpenCV version
                if isinstance(indices, tuple):  # OpenCV > 4.5.4
                    indices = indices[0]
                    
                boxes = boxes[indices]
                scores = scores[indices]
        
        results = []
        for i, (box, score) in enumerate(zip(boxes, scores)):
            # Format box to x1, y1, x2, y2
            x1, y1, x2, y2 = map(int, box)
            
            # Make sure box coordinates are valid
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                continue  # Skip invalid boxes
            
            # 2. Get landmarks for alignment
            landmarks = self.aligner.get_five_landmarks(image, (x1, y1, x2, y2))
            if landmarks is None:
                continue
                
            # Align face
            aligned_face = self.aligner.align_face(image, landmarks)
            if aligned_face is None:
                continue
            
            # 3. Normalize face
            normalized_face = normalize_face(aligned_face)
            
            # 4. Generate embedding
            embedding = self.embedder.get_embedding(normalized_face)
            
            # 5. Verify face against database
            name, confidence = self.verifier.find_best_match(embedding, threshold=0.67)
            
            # --- Tối ưu hóa Anti-spoofing ---
            is_real = True  # Default to real for known faces initially
            spoof_score = 0.0 # Default score
            original_name = name # Lưu tên gốc trước khi kiểm tra fake

            if name != "Unknown": # Chỉ kiểm tra real/fake nếu khuôn mặt được nhận diện
                # 6. Anti spoofing for KNOWN faces
                w, h = x2 - x1, y2 - y1
                margin_x, margin_y = int(w * 0.1), int(h * 0.1)
                face_x = max(0, x1 - margin_x)
                face_y = max(0, y1 - margin_y)
                face_w = min(image.shape[1] - face_x, w + 2 * margin_x)
                face_h = min(image.shape[0] - face_y, h + 2 * margin_y)
                facial_area = (face_x, face_y, face_w, face_h)
                
                try:
                    is_real, spoof_score = self.fasnet.analyze(image, facial_area)
                except Exception as e:
                    print(f"Anti-spoofing error: {str(e)}")
                    is_real = False # Mặc định là FAKE nếu có lỗi khi kiểm tra người đã biết
                    spoof_score = -1.0 # Giá trị đặc biệt cho lỗi

                # Mark fake faces only if they were initially recognized
                if not is_real:
                    name = f"FAKE: {original_name}" 
            # else: # Khuôn mặt là "Unknown", không cần chạy anti-spoofing
                # is_real vẫn là True (hoặc bạn có thể đặt là None/False tùy logic mong muốn)
                # spoof_score vẫn là 0.0
                # name vẫn là "Unknown"

            results.append({
                "box": (x1, y1, x2, y2),
                "name": name, # Tên đã có thể bị sửa thành "FAKE: ..."
                "confidence": confidence,
                "embedding": embedding,
                "is_real": is_real, # Chỉ có ý nghĩa nếu name != "Unknown" trong logic mới này
                "spoof_score": spoof_score # Chỉ có ý nghĩa nếu name != "Unknown"
            })
            
        return results

    def add_face_with_augmentation(self, image, name):
        """Thêm khuôn mặt vào cơ sở dữ liệu với các phiên bản tăng cường"""
        results = self.process_image(image)
        if not results:
            print("❌ Không phát hiện được khuôn mặt")
            return False
        
        # Lấy embedding ban đầu
        embedding = results[0]["embedding"]
        self.face_db[name] = embedding
        
        # Trích xuất khuôn mặt
        x1, y1, x2, y2 = results[0]["box"]
        face = image[y1:y2, x1:x2]
        
        # Tạo các phiên bản tăng cường mô phỏng các góc nghiêng khác nhau
        augmented_images = []
        
        # Mô phỏng nhìn xuống bằng cách dịch hộp vùng cắt lên trên
        shift_down = int((y2 - y1) * 0.15)  # Dịch 15%
        if y1 - shift_down >= 0:
            down_face = image[y1-shift_down:y2-shift_down, x1:x2]
            augmented_images.append(("down", down_face))
        
        # Mô phỏng nhìn lên bằng cách dịch hộp vùng cắt xuống dưới
        shift_up = int((y2 - y1) * 0.15)
        if y2 + shift_up < image.shape[0]:
            up_face = image[y1+shift_up:y2+shift_up, x1:x2]
            augmented_images.append(("up", up_face))
        
        # Xử lý các hình ảnh đã tăng cường
        for pose_type, aug_face in augmented_images:
            # Thay đổi kích thước nếu cần
            if aug_face.shape[:2] != (y2-y1, x2-x1):
                aug_face = cv2.resize(aug_face, (x2-x1, y2-y1))
                
            # Xử lý khuôn mặt tăng cường này
            try:
                # Phát hiện landmarks
                landmarks = self.aligner.get_five_landmarks(aug_face, (0, 0, aug_face.shape[1], aug_face.shape[0]))
                if landmarks is None:
                    continue
                    
                # Căn chỉnh và xử lý
                aligned_face = self.aligner.align_face(aug_face, landmarks)
                if aligned_face is None:
                    continue
                    
                # Chuẩn hóa và tạo embedding
                norm_face = normalize_face(aligned_face)
                aug_embedding = self.embedder.get_embedding(norm_face)
                
                # Thêm vào cơ sở dữ liệu
                aug_name = f"{name}_{pose_type}"
                self.face_db[aug_name] = aug_embedding
                print(f"✅ Đã thêm phiên bản {pose_type} cho '{name}'")
            except Exception as e:
                print(f"⚠️ Lỗi khi xử lý biến thể {pose_type}: {str(e)}")
        
        # Lưu cơ sở dữ liệu đã cập nhật
        self.db_manager.face_db = self.face_db
        self.db_manager._save_backup()
        print(f"✅ Đã thêm khuôn mặt '{name}' vào cơ sở dữ liệu với các biến thể góc nhìn")
        return True

    def add_face_to_database(self, image, name):
        results = self.process_image(image)
        if results:
            # Parse ID and name
            parts = name.split('_', 1)
            if len(parts) > 1 and parts[0].isalnum():
                id_real = parts[0]
                full_name = parts[1]
            else:
                # If no ID format provided, use name as both ID and name
                id_real = name
                full_name = name
                
                # Inform user about expected format
                print(f"ℹ️ Tip: Use format 'ID_NAME' (e.g. '123_John Smith') for better organization")
                
            # Get the embedding
            embedding = results[0]["embedding"]
            
            # Use db_manager.add_face instead of directly updating self.face_db
            success = self.db_manager.add_face(name, id_real, full_name, embedding)
            
            if success:
                print(f"✅ Added face for '{name}' (ID: {id_real}) to database via API")
            else:
                print(f"⚠️ Face was added to local database but API save failed")
                
            return success
        return False

class MotionController:
    """Motion controller using gpiozero's event-driven approach"""
    def __init__(self, pin=14, cooldown=5):
        """
        Initialize motion controller
        
        Args:
            pin: GPIO pin for PIR sensor
            cooldown: Seconds to wait after motion before going to standby
        """
        self.motion_active = False
        self.callback_fn = None
        self.cooldown_timer = None
        self.pin = pin
        self.cooldown = cooldown
        global GPIO_AVAILABLE
        
        if GPIO_AVAILABLE:
            try:
                self.pir = MotionSensor(self.pin)
                print(f"✅ PIR sensor initialized on GPIO pin {self.pin}")
                
                # Set up event handlers
                self.pir.when_motion = self._on_motion
                self.pir.when_no_motion = self._on_no_motion
                
                # Initial state
                if self.pir.motion_detected:
                    self.motion_active = True
            except Exception as e:
                print(f"❌ Failed to initialize PIR sensor: {str(e)}")
                self.pir = None
                GPIO_AVAILABLE = False
        else:
            self.pir = None
            self.motion_active = True  # Always active without PIR
    
    def register_callback(self, callback_fn):
        """Register callback function to be called when motion state changes"""
        self.callback_fn = callback_fn
    
    def _on_motion(self):
        """Called when motion is detected"""
        print("🔍 Motion detected!")
        
        # Cancel any pending cooldown timer
        if self.cooldown_timer:
            self.cooldown_timer.cancel()
            self.cooldown_timer = None
        
        # Only notify if state changes
        if not self.motion_active:
            self.motion_active = True
            if self.callback_fn:
                self.callback_fn(True)
    
    def _on_no_motion(self):
        """Called when motion stops"""
        print(f"⏳ No motion detected - waiting {self.cooldown}s before standby")
        
        # Start cooldown timer
        if self.cooldown_timer:
            self.cooldown_timer.cancel()
        
        self.cooldown_timer = threading.Timer(self.cooldown, self._enter_standby)
        self.cooldown_timer.daemon = True
        self.cooldown_timer.start()
    
    def _enter_standby(self):
        """Enter standby mode after cooldown period"""
        print("💤 Entering standby mode")
        self.motion_active = False
        if self.callback_fn:
            self.callback_fn(False)
    
    def is_active(self):
        """Return current motion status"""
        if not GPIO_AVAILABLE:
            return True
        return self.motion_active
    
    def force_active(self, state):
        """Force motion active state (for manual override)"""
        if state != self.motion_active:
            self.motion_active = state
            if self.callback_fn:
                self.callback_fn(state)
            
            # Cancel any pending cooldown timer
            if state and self.cooldown_timer:
                self.cooldown_timer.cancel()
                self.cooldown_timer = None
    
    def cleanup(self):
        """Clean up resources"""
        if self.cooldown_timer:
            self.cooldown_timer.cancel()
            
# def enhance_lighting(image):
#     """Enhance image for better face recognition in poor lighting conditions"""
#     # Convert to LAB color space
#     lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    
#     # Split channels
#     l, a, b = cv2.split(lab)
    
#     # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     enhanced_l = clahe.apply(l)
    
#     # Merge enhanced L with original A and B
#     enhanced_lab = cv2.merge((enhanced_l, a, b))
    
#     # Convert back to BGR
#     enhanced_image = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
#     return enhanced_image

# def auto_brightness_adjustment(image):
#     """Automatically adjust brightness based on scene conditions"""
#     # Calculate average brightness
#     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#     avg_brightness = cv2.mean(gray)[0]
    
#     # If too dark (adjust threshold as needed)
#     if avg_brightness < 80:  
#         # Increase brightness
#         alpha = 1.5  # Contrast control
#         beta = 30    # Brightness control
#         adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
#         return adjusted
    
#     # If too bright
#     elif avg_brightness > 220:
#         # Decrease brightness
#         alpha = 0.8  # Contrast control
#         beta = -10   # Brightness control
#         adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
#         return adjusted
    
#     # If normal brightness
#     else:
#         return image

# def assess_lighting_quality(image):
#     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

#     # Cắt vùng trung tâm ảnh (ví dụ 50% giữa ảnh)
#     h, w = gray.shape
#     cx1, cx2 = int(w*0.25), int(w*0.75)
#     cy1, cy2 = int(h*0.25), int(h*0.75)
#     center_region = gray[cy1:cy2, cx1:cx2]

#     avg_brightness = cv2.mean(center_region)[0]
#     std_dev = cv2.meanStdDev(center_region)[1][0][0]

#     if avg_brightness < 50:
#         return "Too Dark"
#     elif avg_brightness > 200:
#         return "Too Bright"
#     elif std_dev < 25:
#         return "Low Contrast"
#     else:
#         return "Good"

# def get_lighting_color(status):
#     """Get color for displaying lighting status"""
#     if status == "Good":
#         return (0, 255, 0)  # Green
#     elif status in ["Low Contrast"]:
#         return (0, 165, 255)  # Orange
#     else:
#         return (0, 0, 255)  # Red

def enhance_frame_for_detection(frame):
    """
    Cải thiện ánh sáng trên frame để tối ưu khả năng phát hiện khuôn mặt
    Tập trung vào làm nổi bật đường viền và cấu trúc để phát hiện
    
    Args:
        frame: Khung hình đầu vào (BGR)
        
    Returns:
        Tuple (enhanced_frame, lighting_status)
    """
    # Đánh giá điều kiện ánh sáng
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = cv2.mean(gray)[0]
    std_dev = np.std(gray)
    
    # Phân loại điều kiện ánh sáng
    if avg_brightness < 40:  # Quá tối
        lighting_status = "Very Dark"
    elif avg_brightness < 80:
        lighting_status = "Too Dark"
    elif avg_brightness > 220:
        lighting_status = "Too Bright"
    elif std_dev < 30:
        lighting_status = "Low Contrast"
    else:
        # Nếu ánh sáng tốt, không cần xử lý
        return frame, "Good"
    
    # Xử lý tùy thuộc vào điều kiện ánh sáng
    if lighting_status in ["Very Dark", "Too Dark"]:
        # Trường hợp quá tối: Tăng độ sáng và độ tương phản
        # Tính toán mức độ điều chỉnh dựa trên độ tối
        darkness_ratio = 1.0 - (avg_brightness / 120.0)  
        darkness_ratio = min(max(darkness_ratio, 0), 1)  # Giới hạn trong [0,1]
        
        # Điều chỉnh alpha, beta dựa trên mức độ tối
        alpha = 1.0 + darkness_ratio  # Từ 1.0 đến 2.0
        beta = int(30 * darkness_ratio)  # Từ 0 đến 30
        
        # Áp dụng điều chỉnh trực tiếp
        enhanced = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
        
        # Cho trường hợp cực kỳ tối, thêm bước cân bằng histogram đơn giản
        if lighting_status == "Very Dark":
            # Chỉ áp dụng CLAHE cho trường hợp rất tối
            # Sử dụng LAB để bảo tồn thông tin màu
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            
        return enhanced, lighting_status
        
    elif lighting_status == "Too Bright":
        # Trường hợp quá sáng: Giảm độ sáng
        brightness_ratio = (avg_brightness - 180) / 75.0  # Từ 0 đến 1
        brightness_ratio = min(max(brightness_ratio, 0), 1)
        
        # Giảm độ tương phản và độ sáng
        alpha = 1.0 - (0.3 * brightness_ratio)  # Từ 1.0 đến 0.7
        beta = int(-20 * brightness_ratio)  # Từ 0 đến -20
        
        enhanced = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
        return enhanced, lighting_status
        
    elif lighting_status == "Low Contrast":
        # Trường hợp độ tương phản thấp: Tăng độ tương phản
        # Sử dụng CLAHE nhẹ trong không gian LAB
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Áp dụng CLAHE cho kênh L
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        
        # Kết hợp và chuyển về BGR
        enhanced_lab = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        
        return enhanced, lighting_status
    
    # Trường hợp mặc định nếu không khớp với các điều kiện trên
    return frame, "No Enhancement"
  
def draw_results(image, results):
    """Draw bounding boxes and names on the image"""
    for result in results:
        x1, y1, x2, y2 = result["box"]
        name = result["name"]
        confidence = result["confidence"]
        is_real = result.get("is_real", True)  # Default to True if not available
        
        # Choose color based on whether face is real or spoofed
        color = (0, 255, 0) if is_real else (0, 0, 255)  # Green for real, Red for fake
        
        # Draw rectangle around face
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        
        # Display name and confidence
        label = f"{name}: {confidence:.2f}"
        cv2.putText(image, label, (x1, y1-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Display anti-spoofing result if available
        if "spoof_score" in result:
            spoof_label = f"Real: {result['spoof_score']:.2f}" if is_real else f"FAKE: {result['spoof_score']:.2f}"
            cv2.putText(image, spoof_label, (x1, y2+20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return image

# Modify add_face_handler to work with the new motion controller
def add_face_handler(ui, cap, face_system, motion_controller):
    """
    Handler for adding faces to the database
    
    Works with both active and standby modes by:
    1. Using the last frame if in standby
    2. Temporarily forcing active mode
    """
    was_standby = not motion_controller.is_active()
    
    # Force active mode if needed
    if was_standby:
        motion_controller.force_active(True)
        # Small delay to get a good frame
        time.sleep(0.5)
    
    # Get the current frame
    frozen_frame = cap.read().copy()
    
    # Draw message on frame
    message_frame = frozen_frame.copy()
    cv2.putText(message_frame, "Enter name in terminal...", (10, 60), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    ui.update_frame(message_frame)
    ui.draw_ui()
    
    # Get name from terminal
    name = input("Enter name for the face: ")
    success = face_system.add_face_to_database(frozen_frame, name)
    print(f"{'✅ Successfully added' if success else '❌ Failed to add'} {name} to database")
    
    # Return to standby if we were in standby before
    if was_standby:
        # Give user time to see result before returning to standby
        time.sleep(3)
        motion_controller.force_active(False)

def webcam_demo():
    """Demo face recognition using webcam with motion-based power saving"""
    print("Initializing face recognition system...")
    face_system = FaceRecognitionSystem()
    print("System initialized! Opening webcam...")
    ui = FaceRecognitionUI()
    ui.face_recognition_system = face_system
    
    # Open webcam
    cap = VideoCaptureThread().start()
    print("Webcam opened successfully!")
    
    # Initialize variables
    use_enhancement = True
    last_frame = None
    
    # Create standby frame
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank_frame, "Waiting for faces...", (80, 240), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Initialize motion controller
    motion_controller = MotionController(pin=14, cooldown=0)
    
    # Motion callback function
    def on_motion_change(is_active):
        nonlocal last_frame
        if is_active:
            print("🔄 System resuming active processing")
        else:
            print("🛑 System entering low-power standby")
            # Save the last good frame when entering standby
            if cap is not None:
                last_frame = cap.read().copy()
            # Clear recognition results when entering standby
            ui.update_recognition_results([])
    
    # Register callback
    motion_controller.register_callback(on_motion_change)
    
    # Register key handlers with motion controller
    def toggle_enhancement_handler():
        nonlocal use_enhancement
        use_enhancement = not use_enhancement
        print(f"Lighting enhancement: {'ON' if use_enhancement else 'OFF'}")
    
    def toggle_motion_handler():
        # Toggle motion detection override
        motion_controller.force_active(not motion_controller.is_active())
        print(f"Motion detection: {'OVERRIDDEN' if motion_controller.is_active() else 'ENABLED'}")
    
    # Register the handlers
    ui.register_key_handler(pygame.K_a, 
                           lambda: add_face_handler(ui, cap, face_system, motion_controller))
    ui.register_key_handler(pygame.K_e, toggle_enhancement_handler)
    ui.register_key_handler(pygame.K_m, toggle_motion_handler)
    
    # Print instructions
    print("\n--- CONTROLS ---")
    print("Press 'a' to add a face to the database")
    print("Press 'e' to toggle lighting enhancement")
    print("Press 'm' to toggle motion detection")
    print("Press ESC to exit")
    print("--------------\n")
    
    while True:
        # Handle all events (keyboard, quit, etc.)
        ui.handle_events()
        
        # Check if user wants to quit
        if ui.should_quit():
            break
        
        # Check motion state
        active_mode = motion_controller.is_active()
        
        # If standby, display standby screen and skip heavy processing
        if not active_mode:
            ui.update_recognition_results([])
            ui.update_frame(blank_frame)
            ui.draw_ui()
            pygame.time.delay(100)  # Longer delay in standby
            continue
        
        # Get current frame from camera
        frame = cap.read()
        if frame is None:
            continue
        
        # Process current frame (active mode)
        # Store the frame for potential face registration
        last_frame = frame.copy()
        
        # If a key was pressed to start adding a face, capture the current frame
        if ui.input_active and ui.input_purpose == "add_face" and ui.captured_frame is None:
            ui.captured_frame = frame.copy()
        
        # Apply lighting enhancements if enabled
        if use_enhancement:
            processed_frame, lighting_status = enhance_frame_for_detection(frame)
            
            # Hiển thị trạng thái ánh sáng
            if lighting_status == "Good":
                status_color = (0, 255, 0)  # Xanh lá
            elif lighting_status in ["Low Contrast"]:
                status_color = (0, 165, 255)  # Cam
            else:
                status_color = (0, 0, 255)  # Đỏ
                
            cv2.putText(processed_frame, f"Lighting: {lighting_status}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        else:
            processed_frame = frame
            cv2.putText(processed_frame, "Enhancement OFF", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Process frame with face recognition system
        results = face_system.process_image(processed_frame)
        
        # Update UI with recognition results
        ui.update_recognition_results(results)
        
        # Process face recognition events
        for res in results:
            is_real = res.get("is_real", True)
            name = res["name"]
            if name != "Unknown" and is_real:
                ui.add_event(name, is_real)
                # When a face is recognized, reset the motion timeout
                # No need to explicitly reset with event-based approach
        
        # Update frame and draw UI 
        ui.update_frame(processed_frame)
        ui.draw_ui()
        
        # Small delay to prevent CPU hogging
        pygame.time.delay(10)
    
    # Clean up
    motion_controller.cleanup()
    cap.stop()
    ui.close()
    cv2.destroyAllWindows()


def image_demo(image_path):
    """Demo face recognition on a single image"""
    print(f"Processing image: {image_path}")
    face_system = FaceRecognitionSystem()
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load image: {image_path}")
        return
    
    print("Processing image...")
    results = face_system.process_image(image)
    print(f"Found {len(results)} faces")
    
    # Draw results
    display_image = draw_results(image.copy(), results)
    
    # Display results
    cv2.imshow('Face Recognition', display_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    
    try:
        if len(sys.argv) > 1:
            # Process image file provided as argument
            image_demo(sys.argv[1])
        else:
            # Run webcam demo
            webcam_demo()
    except Exception as e:
        print(f"Error: {str(e)}")