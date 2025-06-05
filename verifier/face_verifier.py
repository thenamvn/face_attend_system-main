import numpy as np

class FaceVerifier:
    def __init__(self, db_embeddings):
        self.db = db_embeddings

    def cosine_similarity(self, vec1, vec2):
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot / (norm1 * norm2 + 1e-10)

    def find_best_match(self, embedding, threshold=0.5):
        best_score = -1
        best_name = "Unknown"
        
        for name, face_data in self.db.items():
            # Get the embedding vector from either format (old or new)
            if isinstance(face_data, dict) and "embedding" in face_data:
                # New structured format
                db_vec = face_data["embedding"]
            else:
                # Old format - just the embedding vector
                db_vec = face_data
                
            score = self.cosine_similarity(embedding, db_vec)
            if score > best_score:
                best_score = score
                best_name = name
                
        if best_score > threshold:
            return (best_name, best_score)
        else:
            return ("Unknown", best_score)