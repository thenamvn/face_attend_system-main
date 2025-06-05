import os
import cv2
import numpy as np
from tqdm import tqdm
from collections import defaultdict

# Import your face recognition components
from detector.ultralight import FaceDetector
from aligner.mediapipe_aligner import FaceAligner
from normalizer.image_preprocess import normalize_face
from embedder.mobilefacenet_embedder import FaceEmbedder
from verifier.face_verifier import FaceVerifier

class FaceRecognitionTester:
    def __init__(self, models_dir="model", threshold=0.65):
        """Initialize components for face recognition testing"""
        print("Initializing face recognition components...")
        
        # Initialize models
        detector_model = os.path.join(models_dir, "version-RFB-320_without_postprocessing.tflite")
        embedder_model = os.path.join(models_dir, "mobilefacenet.tflite")
        
        # Initialize components
        self.detector = FaceDetector(detector_model, conf_threshold=0.65)
        self.aligner = FaceAligner()
        self.embedder = FaceEmbedder(embedder_model)
        self.threshold = threshold
        
        # Initialize empty database
        self.face_db = {}
        self.face_images = {}  # Store processed face images
        
        # Create debug directories
        os.makedirs("debug_db", exist_ok=True)
        os.makedirs("debug_test", exist_ok=True)
        
        print("✅ Face recognition components initialized")
    
    def process_image(self, image, save_path=None):
        """Process an image to extract face embedding"""
        # 1. Detect faces
        boxes, scores = self.detector.detect_faces(image)
        
        if len(boxes) == 0:
            return None
        
        # If multiple faces, use the one with highest confidence
        if len(boxes) > 1:
            best_idx = np.argmax(scores)
            box = boxes[best_idx]
        else:
            box = boxes[0]
        
        # Format box to x1, y1, x2, y2
        x1, y1, x2, y2 = map(int, box)
        
        # Make sure box coordinates are valid
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            return None  # Skip invalid boxes
        
        # Create a debug image with face box
        debug_image = image.copy()
        cv2.rectangle(debug_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # First crop the face (IMPORTANT CHANGE)
        face_crop = image[y1:y2, x1:x2]
        
        # 2. Get landmarks for alignment from cropped face
        landmarks = self.aligner.get_five_landmarks(face_crop, (0, 0, face_crop.shape[1], face_crop.shape[0]))
        if landmarks is None:
            return None
        
        # Draw landmarks on debug image (convert back to original image coordinates)
        for point in landmarks:
            # Adjust landmark coordinates back to original image
            orig_x = int(point[0] + x1)
            orig_y = int(point[1] + y1)
            cv2.circle(debug_image, (orig_x, orig_y), 2, (0, 0, 255), -1)
        
        # 3. Align face using cropped face
        aligned_face = self.aligner.align_face(face_crop, landmarks)
        if aligned_face is None:
            return None
        
        # 4. Normalize face
        normalized_face = normalize_face(aligned_face)
        
        # 5. Generate embedding
        embedding = self.embedder.get_embedding(normalized_face)
        
        # Save processed images if path is provided
        if save_path:
            # Create a visualization image showing steps
            h, w = normalized_face.shape[:2]
            vis_image = np.zeros((h, w*3, 3), dtype=np.uint8)
            
            # Original crop (already cropped)
            face_crop_resized = cv2.resize(face_crop, (w, h))
            vis_image[0:h, 0:w] = face_crop_resized
            
            # Aligned face
            aligned_resized = cv2.resize(aligned_face, (w, h))
            vis_image[0:h, w:2*w] = aligned_resized
            
            # Normalized face
            vis_image[0:h, 2*w:3*w] = normalized_face
            
            # Add labels
            cv2.putText(vis_image, "Original", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(vis_image, "Aligned", (w+10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(vis_image, "Normalized", (2*w+10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imwrite(save_path, vis_image)
            
            # Also save debug image with face box and landmarks
            debug_path = os.path.splitext(save_path)[0] + "_detection.jpg"
            cv2.imwrite(debug_path, debug_image)
        
        return {
            "box": (x1, y1, x2, y2),
            "embedding": embedding,
            "normalized_face": normalized_face
        }
    
    def build_database(self, database_dir="face_database"):
        """Build face database from images in face_database directory"""
        print(f"Building face database from {database_dir}...")
        
        # Check if directory exists
        if not os.path.isdir(database_dir):
            print(f"❌ Error: Directory {database_dir} not found")
            return False
        
        # Process each image in the directory
        image_files = [f for f in os.listdir(database_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        for filename in tqdm(image_files, desc="Processing reference faces"):
            # Extract ID from filename (remove extension)
            person_id = os.path.splitext(filename)[0]
            
            # Load and process image
            image_path = os.path.join(database_dir, filename)
            image = cv2.imread(image_path)
            
            if image is None:
                print(f"⚠️ Warning: Could not load image {filename}")
                continue
            
            # Process image to get embedding and save visualization
            save_path = os.path.join("debug_db", f"{person_id}_processed.jpg")
            result = self.process_image(image, save_path)
            
            if result is None:
                print(f"⚠️ Warning: No face detected in {filename}")
                continue
            
            # Add to database
            self.face_db[person_id] = result["embedding"]
            self.face_images[person_id] = result["normalized_face"]
        
        print(f"✅ Database built with {len(self.face_db)} face entries")
        print(f"✅ Processed database faces saved to 'debug_db' folder")
        return True
    
    def test_recognition(self, test_dir="face_test"):
        """Test face recognition accuracy using test images"""
        if len(self.face_db) == 0:
            print("❌ Error: Face database is empty. Run build_database first.")
            return
        
        print(f"Testing face recognition using images from {test_dir}...")
        
        # Initialize verifier with our database
        verifier = FaceVerifier(self.face_db)
        
        # Statistics
        stats = {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "not_detected": 0,
            "person_stats": defaultdict(lambda: {"total": 0, "correct": 0})
        }
        
        # Iterate through directories in test_dir (each directory should be a person ID)
        for person_id in os.listdir(test_dir):
            person_dir = os.path.join(test_dir, person_id)
            
            if not os.path.isdir(person_dir):
                continue
            
            # Process each image in the person's directory
            image_files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            for filename in image_files:
                stats["total"] += 1
                stats["person_stats"][person_id]["total"] += 1
                
                # Load and process image
                image_path = os.path.join(person_dir, filename)
                image = cv2.imread(image_path)
                
                if image is None:
                    print(f"⚠️ Warning: Could not load test image {image_path}")
                    stats["not_detected"] += 1
                    continue
                
                # Process image to get embedding
                save_path = os.path.join("debug_test", f"{person_id}_{filename}")
                result = self.process_image(image, save_path)
                
                if result is None:
                    print(f"⚠️ No face detected in test image {image_path}")
                    stats["not_detected"] += 1
                    continue
                
                # Match against database
                best_match, confidence = verifier.find_best_match(result["embedding"], threshold=self.threshold)
                
                # Extract ID from best_match (could include additional info after underscore)
                matched_id = best_match.split('_')[0] if best_match != "Unknown" else "Unknown"
                
                # Check if correct
                is_correct = (matched_id == person_id)
                
                if is_correct:
                    stats["correct"] += 1
                    stats["person_stats"][person_id]["correct"] += 1
                else:
                    stats["incorrect"] += 1
                
                # Create comparison visualization for test and matched face
                if matched_id != "Unknown" and matched_id in self.face_images:
                    # Get processed test face and matched face from database
                    test_face = result["normalized_face"]
                    db_face = self.face_images[matched_id]
                    
                    # Create side-by-side comparison
                    h, w = test_face.shape[:2]
                    comparison = np.zeros((h, 2*w + 100, 3), dtype=np.uint8)
                    
                    # Place test and matched faces
                    comparison[0:h, 0:w] = test_face
                    comparison[0:h, w+100:2*w+100] = db_face
                    
                    # Add labels and match info
                    cv2.putText(comparison, "Test Face", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(comparison, f"DB Face: {matched_id}", (w+110, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(comparison, f"Confidence: {confidence:.3f}", (w//2 - 50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if is_correct else (0, 0, 255), 1)
                    
                    # Add a check or cross mark
                    mark_text = "✓" if is_correct else "✗"
                    mark_color = (0, 255, 0) if is_correct else (0, 0, 255)
                    cv2.putText(comparison, mark_text, (w + 40, h//2), cv2.FONT_HERSHEY_SIMPLEX, 2, mark_color, 2)
                    
                    # Save comparison image
                    comparison_path = os.path.join("debug_test", f"{person_id}_{filename}_comparison.jpg")
                    cv2.imwrite(comparison_path, comparison)
                
                # Print result for this image
                status = "✅" if is_correct else "❌"
                print(f"{status} {image_path}: Recognized as {matched_id} with confidence {confidence:.3f}")
        
        # Calculate and print statistics
        accuracy = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        
        print("\n=== Recognition Results ===")
        print(f"Total test images: {stats['total']}")
        print(f"Correctly identified: {stats['correct']} ({accuracy:.2f}%)")
        print(f"Incorrectly identified: {stats['incorrect']}")
        print(f"Faces not detected: {stats['not_detected']}")
        
        print("\n=== Per-Person Accuracy ===")
        for person_id, person_data in stats["person_stats"].items():
            person_accuracy = person_data["correct"] / person_data["total"] * 100 if person_data["total"] > 0 else 0
            print(f"{person_id}: {person_data['correct']}/{person_data['total']} ({person_accuracy:.2f}%)")
        
        print(f"\n✅ Processed test faces and comparisons saved to 'debug_test' folder")
        return stats

def main():
    # Initialize tester with threshold
    tester = FaceRecognitionTester(threshold=0.67)
    
    # Build database from reference images
    database_built = tester.build_database()
    if not database_built:
        return
    
    # Test recognition
    tester.test_recognition()

if __name__ == "__main__":
    main()