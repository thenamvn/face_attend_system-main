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
from ui.ui_timecard import TimeCardUI
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

def draw_results_on_frame(image, results):
    """Draw bounding boxes and names on the image"""
    for result in results:
        x1, y1, x2, y2 = result["box"]
        name = result["name"]
        confidence = result["confidence"]
        is_real = result.get("is_real", True)
        
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

def timecard_demo():
    """Time card style demo with fullscreen UI"""
    print("Initializing face recognition time card system...")
    face_system = FaceRecognitionSystem()
    print("System initialized!")
    
    # Initialize UI - giống máy chấm công
    ui = TimeCardUI()
    ui.face_recognition_system = face_system
    
    # Open webcam
    cap = VideoCaptureThread().start()
    print("Camera started successfully!")
    
    # Initialize spoof alert
    spoof_alert = SpoofAlertManager(
        email_sender=os.getenv("EMAIL_SENDER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_recipients=os.getenv("EMAIL_RECIPIENT"),
        min_duration=1.5,
        cooldown_period=60
    )
    
    # Face recognition cooldown
    face_cooldowns = {}
    cooldown_period = 5  # seconds between recognitions for same person
    
    # Processing loop
    def processing_loop():
        while not ui.should_quit():
            try:
                frame = cap.read()
                if frame is None:
                    time.sleep(0.033)
                    continue
                
                # Process frame
                results = face_system.process_image(frame)
                
                # Update spoof alert
                spoof_alert.update(results, frame)
                
                # Process recognition events
                current_time = time.time()
                for res in results:
                    name = res["name"]
                    is_real = res.get("is_real", True)
                    
                    # Only process real, known faces
                    if is_real and name != "Unknown" and "FAKE" not in name:
                        # Check cooldown
                        if name in face_cooldowns:
                            if current_time - face_cooldowns[name] < cooldown_period:
                                continue
                        
                        face_cooldowns[name] = current_time
                        
                        # Add event to UI (will trigger info screen)
                        ui.add_event(name, is_real)
                
                # Draw recognition results on frame
                display_frame = draw_results_on_frame(frame.copy(), results)
                
                # Update camera display
                ui.update_frame(display_frame)
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"Processing error: {e}")
                time.sleep(0.1)
    
    # Start processing thread
    processing_thread = threading.Thread(target=processing_loop, daemon=True)
    processing_thread.start()
    
    print("\n--- TIME CARD SYSTEM STARTED ---")
    print("Press 'A' to add a face")
    print("Press 'Escape' to exit")
    print("Look at the camera to check in/out")
    print("--------------------------------\n")
    
    try:
        # Run UI
        ui.run()
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        print("Cleaning up...")
        cap.stop()
        ui.close()
        spoof_alert.stop()

if __name__ == "__main__":
    timecard_demo()