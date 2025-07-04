import cv2
import os
from dotenv import load_dotenv
load_dotenv()
from detector.ultralight import FaceDetector
from aligner.mediapipe_aligner import FaceAligner
from normalizer.image_preprocess import normalize_face
from embedder.mobilefacenet_embedder import FaceEmbedder
from verifier.face_verifier import FaceVerifier
from database.face_database_manager import FaceDatabaseManager
from antispoof.Fasnet import Fasnet
from thread.thread import VideoCaptureThread
from ui.ui import FaceRecognitionTkinterUI
from mail.SpoofAlertManager import SpoofAlertManager
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

        #variables
        self.spoof_score_threshold = 0.6
    
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
            # Format box to x1, y1, x2, y2 and validate
            box = np.clip(box.astype(int), [0, 0, 0, 0], [image.shape[1], image.shape[0], image.shape[1], image.shape[0]])
            x1, y1, x2, y2 = box
            if x2 <= x1 or y2 <= y1:
                continue  # Skip invalid boxes
            
            face_crop = image[y1:y2, x1:x2]
            # 2. Get landmarks for alignment
            landmarks = self.aligner.get_five_landmarks(face_crop, (0, 0, face_crop.shape[1], face_crop.shape[0]))
            if landmarks is None:
                continue
                
            # Align face
            aligned_face = self.aligner.align_face(face_crop, landmarks)
            if aligned_face is None:
                continue
            # 3. Normalize face
            normalized_face = normalize_face(aligned_face)
            
            # 4. Generate embedding
            embedding = self.embedder.get_embedding(normalized_face)
            
            # 5. Verify face against database
            name, confidence = self.verifier.find_best_match(embedding, threshold=0.68)
            # --- Tối ưu hóa Anti-spoofing ---
            is_real = True  # Default to real for known faces initially
            spoof_score = 0.0 # Default score
            original_name = name # Lưu tên gốc trước khi kiểm tra fake

            if name != "Unknown": # Chỉ kiểm tra real/fake nếu khuôn mặt được nhận diện
                # 6. Anti spoofing for KNOWN face
                spoofing_start = time.time()
                # Calculate the expanded facial area with margin (10%)
                margin = 0.1
                x1_exp = max(0, x1 - int((x2-x1) * margin))
                y1_exp = max(0, y1 - int((y2-y1) * margin))
                x2_exp = min(image.shape[1], x2 + int((x2-x1) * margin))
                y2_exp = min(image.shape[0], y2 + int((y2-y1) * margin))
                facial_area = (x1_exp, y1_exp, x2_exp - x1_exp, y2_exp - y1_exp)
                
                try:
                    is_real_result, spoof_score = self.fasnet.analyze(image, facial_area)

                    if is_real_result and spoof_score > self.spoof_score_threshold:
                        is_real = True
                    else:
                        is_real = False
                except Exception as e:
                    print(f"Anti-spoofing error: {str(e)}")
                    is_real = False # Mặc định là FAKE nếu có lỗi khi kiểm tra người đã biết
                    spoof_score = -1.0 # Giá trị đặc biệt cho lỗi

                # Mark fake faces only if they were initially recognized
                if not is_real:
                    name = f"FAKE: {original_name}" 

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
                self.face_db = self.db_manager.face_db
                self.verifier.update_database(self.face_db)  # Rebuild FAISS index
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

def draw_results_on_frame(image, results):
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

def webcam_demo():
    """Demo face recognition using webcam with customtkinter UI"""
    print("Initializing face recognition system...")
    face_system = FaceRecognitionSystem()
    print("System initialized! Opening webcam...")
    
    # Initialize UI
    ui = FaceRecognitionTkinterUI()
    ui.face_recognition_system = face_system
    
    # Open webcam
    cap = VideoCaptureThread().start()
    print("Webcam opened successfully!")
    
    # Initialize variables
    last_frame = None
    
    # Create standby frame
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank_frame, "Waiting for faces...", (80, 240), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Initialize motion controller
    motion_controller = MotionController(pin=14, cooldown=0)

    # Initialize mail alert system
    spoof_alert = SpoofAlertManager(
        email_sender=os.getenv("EMAIL_SENDER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_recipients=os.getenv("EMAIL_RECIPIENT"),
        min_duration=1.5,
        cooldown_period=60
    )
    
    # Motion callback function
    def on_motion_change(is_active):
        nonlocal last_frame
        if is_active:
            print("🔄 System resuming active processing")
        else:
            print("🛑 System entering low-power standby")
            # Save the last good frame when entering standby
            if cap is not None:
                frame = cap.read()
                if frame is not None:  # Add this null check
                    last_frame = frame.copy()
                else:
                    print("⚠️ Could not capture frame for standby")
            # Clear recognition results when entering standby
            ui.update_recognition_results([])
    
    # Register callback
    motion_controller.register_callback(on_motion_change)
    
    # Main processing loop in separate thread
    def processing_loop():
        while not ui.should_quit():
            try:
                # Check motion state
                active_mode = motion_controller.is_active()
                
                # If standby, display standby screen and skip heavy processing
                if not active_mode:
                    # KHÔNG gọi update_recognition_results ở đây nữa
                    ui.update_frame(blank_frame)
                    time.sleep(0.1)  # Longer delay in standby
                    continue
                
                # Get current frame from camera
                frame = cap.read()
                if frame is None:
                    time.sleep(0.033)
                    continue
                
                # Save frame for other processing
                last_frame = frame.copy()
                
                # Process frame with face recognition system
                results = face_system.process_image(frame)
                
                # Update spoof alert system
                spoof_alert.update(results, frame)

                # CHỈ update recognition results khi có kết quả mới
                if results:
                    ui.update_recognition_results(results)
                
                # Process face recognition events - CHỈ KHI CÓ FACES THẬT
                for res in results:
                    is_real = res.get("is_real", True)
                    name = res["name"]
                    if name != "Unknown" and is_real:
                        ui.add_event(name, is_real)
                
                # Draw results on frame
                display_frame = draw_results_on_frame(frame.copy(), results)
                
                # Update frame in UI
                ui.update_frame(display_frame)
                
                # Small delay to prevent CPU hogging
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Processing loop error: {e}")
                time.sleep(0.1)
    
    # Start processing thread
    processing_thread = threading.Thread(target=processing_loop, daemon=True)
    processing_thread.start()
    
    # Print instructions
    print("\n--- CONTROLS ---")
    print("Press 'A' key or click button to add a face to the database")
    print("Close window to exit")
    print("--------------\n")
    
    try:
        # Run UI main loop
        ui.run()
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        print("Cleaning up...")
        motion_controller.cleanup()
        cap.stop()
        ui.close()
        spoof_alert.stop()

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
    display_image = draw_results_on_frame(image.copy(), results)
    
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
        import traceback
        traceback.print_exc()