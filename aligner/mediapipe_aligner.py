import cv2
import numpy as np
import mediapipe as mp
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
class FaceAligner:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,  # giúp chính xác hơn ở mắt và miệng
            min_detection_confidence=0.5
        )
        # Landmark chuẩn của MobileFaceNet (corresponding to left eye, right eye, nose, mouth left, mouth right)
        self.dst_landmarks = np.array([
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041]
        ], dtype=np.float32)

    def get_five_landmarks(self, image, bbox):
        x1, y1, x2, y2 = map(int, bbox)
        roi = image[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        result = self.face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            return None

        face_landmarks = result.multi_face_landmarks[0]
        
        # Enhanced landmark selection - added forehead point and chin
        # [left eye, right eye, nose tip, mouth left, mouth right, forehead, chin]
        idxs = [33, 263, 1, 61, 291, 10, 152]  # Added forehead (10) and chin (152)
        
        landmarks = []
        for idx in idxs:
            lm = face_landmarks.landmark[idx]
            x = x1 + lm.x * (x2 - x1)
            y = y1 + lm.y * (y2 - y1)
            landmarks.append([x, y])

        return np.array(landmarks, dtype=np.float32)

    def align_face(self, image, landmarks):
        if landmarks is None:
            return None
            
        # Get 3D head pose estimation
        if len(landmarks) >= 7:  # Check if we have the enhanced landmarks
            # Calculate vertical tilt based on forehead-nose-chin angle
            forehead = landmarks[5]
            nose = landmarks[2]
            chin = landmarks[6]
            
            # Calculate angle of tilt
            vertical_angle = np.arctan2(chin[1] - forehead[1], 
                                    chin[0] - forehead[0]) * 180 / np.pi
                                    
            # Adjust transformation based on tilt angle
            if abs(vertical_angle) > 30:  # If significant downward/upward tilt
                # Use an adjusted set of target landmarks
                adjusted_dst = self.dst_landmarks.copy()
                # Shift target points to compensate for tilt
                tilt_factor = abs(vertical_angle) / 90.0  # Normalized 0-1
                adjustment = tilt_factor * 10  # Pixels to adjust
                
                # Adjust nose and mouth positions based on tilt direction
                if vertical_angle < 0:  # Looking down
                    adjusted_dst[2][1] += adjustment  # Move nose down
                    adjusted_dst[3][1] += adjustment * 2  # Move mouth down more
                    adjusted_dst[4][1] += adjustment * 2  # Move mouth down more
                else:  # Looking up
                    adjusted_dst[2][1] -= adjustment  # Move nose up
                    
                # Use adjusted landmarks for alignment
                M, _ = cv2.estimateAffinePartial2D(landmarks[:5], adjusted_dst, method=cv2.LMEDS)
            else:
                # Standard alignment for normal poses
                M, _ = cv2.estimateAffinePartial2D(landmarks[:5], self.dst_landmarks, method=cv2.LMEDS)
        else:
            # Fallback to standard alignment
            M, _ = cv2.estimateAffinePartial2D(landmarks, self.dst_landmarks, method=cv2.LMEDS)
        
        if M is None:
            return None
            
        aligned = cv2.warpAffine(image, M, (112, 112))
        return aligned

    def align_face_multi(self, image, landmarks):
        if landmarks is None or len(landmarks) < 5:
            return None
        
        # Try various transformation parameters
        alignments = []
        confidence_scores = []
        
        # Standard alignment
        M1, _ = cv2.estimateAffinePartial2D(landmarks[:5], self.dst_landmarks, method=cv2.LMEDS)
        if M1 is not None:
            aligned1 = cv2.warpAffine(image, M1, (112, 112))
            alignments.append(aligned1)
            confidence_scores.append(1.0)  # Base confidence
        
        # Try with different subset of landmarks
        if len(landmarks) >= 5:
            # Use only eyes and nose
            eye_nose = np.vstack([landmarks[0:3]])
            dst_eye_nose = np.vstack([self.dst_landmarks[0:3]])
            M2, _ = cv2.estimateAffinePartial2D(eye_nose, dst_eye_nose, method=cv2.LMEDS)
            if M2 is not None:
                aligned2 = cv2.warpAffine(image, M2, (112, 112))
                alignments.append(aligned2)
                confidence_scores.append(0.8)  # Lower confidence for partial alignment
        
        # Return best alignment
        if alignments:
            return alignments[np.argmax(confidence_scores)]
        return None
    
