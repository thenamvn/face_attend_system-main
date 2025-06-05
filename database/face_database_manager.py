import os
import cv2
import pickle
import numpy as np
import requests
from normalizer.image_preprocess import normalize_face
import time
import traceback
class FaceDatabaseManager:
    def __init__(self, image_dir, backup_path, detector, aligner, embedder, api_url="https://attendance-api-dm9x.onrender.com/api/faces"):
        self.image_dir = image_dir
        self.backup_path = backup_path
        self.detector = detector
        self.aligner = aligner
        self.embedder = embedder
        self.api_url = api_url

        # Initialize cache parameters BEFORE first call to _load_face_database
        self.cache_time = 300  # 5 minutes
        self.last_cache_update = 0
        
        # Load database and check for updates
        self.face_db = {}

        self._load_face_database()
        self._update_from_image_files()

    def _load_face_database(self):
        """Load face database with caching"""
        now = time.time()
        if now - self.last_cache_update < self.cache_time and self.face_db:
            print("✅ Using cached face data")
            return
        """Load face database from API or use backup file if API fails"""
        try:
            response = requests.get(self.api_url)
            
            if response.status_code == 200:
                data = response.json()
                
                if data["success"]:              
                    for key, face_data in data["data"].items():
                        try:
                            # Convert JSON array to numpy array - no decoding needed
                            embedding = np.array(face_data["embedding"], dtype=np.float32)
                            
                            self.face_db[key] = {
                                "id_real": face_data["id_real"],
                                "full_name": face_data["full_name"],
                                "embedding": embedding
                            }
                        except Exception as e:
                            print(f"❌ Error processing face data for {key}: {e}")
                            continue
                    
                    print(f"✅ Loaded {len(self.face_db)} face entries from API")
                    self.last_cache_update = now
                    return
                
        except Exception as e:
            print(f"❌ Error loading faces from API: {e}")
            print("⚠️ Trying to load from backup file...")
        
        # Fallback to loading from pickle file
        if os.path.exists(self.backup_path):
            try:
                with open(self.backup_path, 'rb') as f:
                    self.face_db = pickle.load(f)
                print(f"✅ Loaded {len(self.face_db)} face entries from backup file")
            except Exception as e:
                print(f"❌ Error loading from backup file: {e}")
                print("🆕 Starting with empty face database")
        else:
            print("🆕 No backup file found. Starting with empty face database.")
    

    # def _save_face_database(self):
    #     with open(self.backup_path, 'wb') as f:
    #         pickle.dump(self.face_db, f)
    #     print("💾 Saved updated face database.")
    def _save_backup(self):
        """Save current face database to backup file"""
        with open(self.backup_path, 'wb') as f:
            pickle.dump(self.face_db, f)
        print("💾 Saved backup of face database")


    def _update_from_image_files(self):
        """Update database by reading image files directly from the image_dir.
        Assumes filenames are in 'ID_FullName.extension' format.
        """
        updated = False
        processed_ids = set()  # Track processed IDs to avoid duplicates
        
        # Create debug directory for visualization if needed
        debug_dir = os.path.join(self.image_dir, "debug_processing")
        os.makedirs(debug_dir, exist_ok=True)

        print(f"🔄 Checking for image files directly in: {self.image_dir}")

        # Check if directory exists
        if not os.path.isdir(self.image_dir):
            print(f"❌ Error: Image directory '{self.image_dir}' not found.")
            return

        # Get list of IDs already in database
        existing_ids_in_db = {data.get("id_real") for data in self.face_db.values() if data.get("id_real")}
        print(f"ℹ️ IDs already in loaded database: {existing_ids_in_db if existing_ids_in_db else 'None'}")

        for filename in os.listdir(self.image_dir):
            file_path = os.path.join(self.image_dir, filename)

            # Only process valid image files
            if os.path.isfile(file_path) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                print(f"\nProcessing potential image file: {filename}")

                # Split filename and extension
                base_name, _ = os.path.splitext(filename)

                # Split ID and Name from filename (e.g., "1_Nhì")
                parts = base_name.split('_', 1)

                # Check if filename format is correct
                if len(parts) == 2 and parts[0].isalnum():
                    id_real = parts[0]
                    full_name = parts[1]
                    print(f"  -> Parsed from Filename: ID={id_real}, Name={full_name}")

                    # --- IMPORTANT CHECKS ---
                    # 1. Skip if this ID has already been processed in this run
                    if id_real in processed_ids:
                        print(f"  ℹ️ Skipping: ID '{id_real}' already processed from another file in this run.")
                        continue

                    # 2. Skip if ID already exists in database loaded from API/backup
                    if id_real in existing_ids_in_db:
                        print(f"  ℹ️ Skipping: ID '{id_real}' already exists in the database loaded from API/backup.")
                        processed_ids.add(id_real)  # Mark as processed to avoid duplicates
                        continue

                    # Process new IDs
                    print(f"  -> Processing new face: ID={id_real}")

                    img = cv2.imread(file_path)
                    if img is None:
                        print(f"    ❌ Failed to read image: {filename}")
                        continue
                    else:
                        print(f"    ✅ Image loaded successfully: {filename} (shape: {img.shape})")

                    try:
                        # --- FACE PROCESSING (FOLLOWS process_image PIPELINE) ---
                        # 1. Detect faces
                        boxes, scores = self.detector.detect_faces(img)
                        print(f"    🔎 Detected {len(boxes)} face(s) in {filename}")
                        if len(boxes) == 0:
                            continue  # Skip if no faces detected
                        
                        # Apply non-maximum suppression
                        if len(boxes) > 1:
                            indices = cv2.dnn.NMSBoxes(
                                boxes.tolist(),
                                scores.tolist(),
                                score_threshold=0.5,
                                nms_threshold=0.3
                            )
                            
                            if len(indices) > 0:
                                # Handle different return types based on OpenCV version
                                if isinstance(indices, tuple):  # OpenCV > 4.5.4
                                    indices = indices[0]
                                    
                                boxes = boxes[indices]
                                scores = scores[indices]
                        
                        # Find largest face if multiple are detected
                        if len(boxes) > 1:
                            face_areas = [(box[2]-box[0])*(box[3]-box[1]) for box in boxes]
                            largest_face_idx = face_areas.index(max(face_areas))
                            box = boxes[largest_face_idx]
                            print(f"    📏 Multiple faces detected, using largest face (area: {max(face_areas)} pixels)")
                        else:
                            box = boxes[0]
                        
                        # Format box coordinates
                        x1, y1, x2, y2 = map(int, box)
                        
                        # Make sure box coordinates are valid
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
                        
                        if x2 <= x1 or y2 <= y1:
                            print(f"    ❌ Invalid face box detected")
                            continue
                        
                        # First crop the face - IMPORTANT CHANGE
                        face_crop = img[y1:y2, x1:x2]
                        
                        # # Save original crop for debugging
                        # debug_path = os.path.join(debug_dir, f"{id_real}_1_original.jpg")
                        # cv2.imwrite(debug_path, face_crop)
                        
                        # 2. Get landmarks for alignment from cropped face
                        landmarks = self.aligner.get_five_landmarks(face_crop, (0, 0, face_crop.shape[1], face_crop.shape[0]))
                        if landmarks is None:
                            print(f"    ❌ Failed to get landmarks for face in {filename}")
                            continue
                        else:
                            print(f"    ✅ Got landmarks")
                        
                        # 3. Align face using cropped face
                        aligned_face = self.aligner.align_face(face_crop, landmarks)
                        if aligned_face is None:
                            print(f"    ❌ Failed to align face in {filename}")
                            continue
                        else:
                            print(f"    ✅ Face aligned")
                            
                        # # Save aligned face for debugging
                        # debug_path = os.path.join(debug_dir, f"{id_real}_2_aligned.jpg")
                        # cv2.imwrite(debug_path, aligned_face)
                        
                        # 4. Normalize face
                        norm_face = normalize_face(aligned_face)
                        print(f"    ✅ Face normalized")
                        
                        # # Save normalized face for debugging
                        # debug_path = os.path.join(debug_dir, f"{id_real}_3_normalized.jpg")
                        # cv2.imwrite(debug_path, norm_face)
                        
                        # # Create side-by-side comparison
                        # h_max = max(face_crop.shape[0], aligned_face.shape[0], norm_face.shape[0])
                        # face_crop_resized = cv2.resize(face_crop, (int(face_crop.shape[1] * h_max / face_crop.shape[0]), h_max))
                        # aligned_face_resized = cv2.resize(aligned_face, (int(aligned_face.shape[1] * h_max / aligned_face.shape[0]), h_max))
                        # norm_face_resized = cv2.resize(norm_face, (int(norm_face.shape[1] * h_max / norm_face.shape[0]), h_max))
                        
                        # total_width = face_crop_resized.shape[1] + aligned_face_resized.shape[1] + norm_face_resized.shape[1]
                        # combined_img = np.zeros((h_max, total_width, 3), dtype=np.uint8)
                        
                        # x_offset = 0
                        # combined_img[:, x_offset:x_offset+face_crop_resized.shape[1]] = face_crop_resized
                        # x_offset += face_crop_resized.shape[1]
                        # combined_img[:, x_offset:x_offset+aligned_face_resized.shape[1]] = aligned_face_resized
                        # x_offset += aligned_face_resized.shape[1]
                        # combined_img[:, x_offset:x_offset+norm_face_resized.shape[1]] = norm_face_resized
                        
                        # # Add labels
                        # font = cv2.FONT_HERSHEY_SIMPLEX
                        # cv2.putText(combined_img, "Original", (10, 20), font, 0.5, (0, 255, 0), 1)
                        # cv2.putText(combined_img, "Aligned", (face_crop_resized.shape[1] + 10, 20), font, 0.5, (0, 255, 0), 1)
                        # cv2.putText(combined_img, "Normalized", (face_crop_resized.shape[1] + aligned_face_resized.shape[1] + 10, 20), font, 0.5, (0, 255, 0), 1)
                        
                        # comparison_path = os.path.join(debug_dir, f"{id_real}_comparison.jpg")
                        # cv2.imwrite(comparison_path, combined_img)
                        
                        # 5. Generate embedding
                        embedding = self.embedder.get_embedding(norm_face)
                        print(f"    ✅ Embedding generated (shape: {embedding.shape})")
                        # --- END OF FACE PROCESSING ---

                        # Create database key
                        db_key = f"{id_real}_{full_name}"

                        # Save to local database (in memory)
                        self.face_db[db_key] = {
                            "id_real": id_real,
                            "full_name": full_name,
                            "embedding": embedding
                        }
                        print(f"    ➕ Added '{db_key}' to local face_db")

                        # Save to API
                        print(f"    🚀 Attempting to save '{db_key}' to API...")
                        api_success = self._save_face_to_api(id_real, full_name, embedding)

                        if api_success:
                            print(f"    ✔️ API Save successful for '{db_key}'")
                            updated = True  # Mark that changes need backup
                            processed_ids.add(id_real)  # Mark this ID as successfully processed
                        else:
                            print(f"    ❌ API Save failed for '{db_key}'. Face remains in local DB for now.")
                            processed_ids.add(id_real)  # Still mark as processed to avoid retrying

                    except Exception as e:
                        print(f"    ❌❌❌ Unexpected Error processing {filename}: {e}")
                        traceback.print_exc()  # Print detailed error
                        continue  # Skip this file

                else:
                    # Notify if filename format is incorrect
                    print(f"  ⚠️ Skipping file '{filename}'. Name doesn't match 'ID_FullName.extension' format.")

        if updated:
            print("\n💾 Saving backup due to new faces added from files.")
            self._save_backup()
        else:
            print("\n✅ No new faces from files were added to the API or required backup.")

    def _save_face_to_api(self, id_real, full_name, embedding):
        """Save face embedding to API"""
        try:
            # Convert numpy array to a regular Python list
            embedding_list = embedding.tolist()
            # Debug print
            print(f"Attempting to send face data to API: {self.api_url}")
            print(f"- ID: {id_real}")
            print(f"- Name: {full_name}")
            print(f"- Embedding as array of {len(embedding_list)} values")
            
            # Send to API
            response = requests.post(
                self.api_url,
                json={
                    "id_real": id_real,
                    "full_name": full_name,
                    "embedding": embedding_list
                }
            )
            
            # Debug print
            print(f"API Response Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print(f"✅ Face saved to API: {id_real}_{full_name}")
                return True
            else:
                print(f"❌ API error when saving face: {response.status_code}")
                # Print more detailed error info
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error text: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Network error when saving face: {e}")
            return False
    
    def save_face_augmentation(self, id_real, full_name, pose_type, embedding):
        """Save face augmentation to API"""
        try:
            # Convert numpy array to a regular Python list
            embedding_list = embedding.tolist()
            # Add to local database first
            db_key = f"{id_real}_{full_name}_{pose_type}"
            self.face_db[db_key] = {
                "id_real": id_real,
                "full_name": f"{full_name} ({pose_type})",
                "embedding": embedding
            }
            
            # Send to API
            response = requests.post(
                f"{self.api_url}/augmentation",
                json={
                    "id_real": id_real,
                    "pose_type": pose_type,
                    "embedding": embedding_list
                }
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Face augmentation saved to API: {id_real}_{pose_type}")
                return True
            else:
                print(f"❌ API error when saving augmentation: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Network error when saving augmentation: {e}")
            return False
    
    def add_face(self, name, id_real, full_name, embedding):
        """Add a face to the database via API"""
        # Update in-memory database
        self.face_db[name] = {
            "id_real": id_real,
            "full_name": full_name,
            "embedding": embedding
        }
        
        # Save to API
        success = self._save_face_to_api(id_real, full_name, embedding)
        
        # Backup to file
        self._save_backup()
        
        return success
    
    def delete_face(self, id_real):
        """Delete a face from the database"""
        try:
            # First remove from in-memory database
            to_remove = []
            for name, data in self.face_db.items():
                if data.get("id_real") == id_real:
                    to_remove.append(name)
            
            for name in to_remove:
                del self.face_db[name]
                
            # Then remove from API
            response = requests.delete(f"{self.api_url}/{id_real}")
            
            if response.status_code == 200:
                print(f"✅ Face deleted from API: {id_real}")
                # Backup to file
                self._save_backup()
                return True
            else:
                print(f"❌ API error when deleting face: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Network error when deleting face: {e}")
            return False