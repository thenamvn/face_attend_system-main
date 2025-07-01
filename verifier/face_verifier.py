import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
    print("✅ FAISS available for fast face matching")
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️ FAISS not available, using standard cosine similarity")

class FaceVerifier:
    def __init__(self, db_embeddings=None):
        self.db = db_embeddings or {}
        
        if FAISS_AVAILABLE:
            self.index = None
            self.names = []
            self.embeddings_array = None
            self._is_built = False
            
            # Build index immediately if database provided
            if self.db:
                self.build_index(self.db)
        else:
            # Fallback to original implementation
            pass

    def build_index(self, db_embeddings):
        """Build FAISS index from database embeddings"""
        if not FAISS_AVAILABLE:
            print("⚠️ FAISS not available, skipping index build")
            return
            
        if not db_embeddings:
            print("⚠️ Empty database, skipping FAISS index build")
            return
            
        # Extract embeddings and names
        embeddings = []
        names = []
        
        for name, face_data in db_embeddings.items():
            # Get embedding from database format
            if isinstance(face_data, dict) and "embedding" in face_data:
                embedding = face_data["embedding"]
            else:
                embedding = face_data
                
            embeddings.append(embedding)
            names.append(name)
        
        if not embeddings:
            print("⚠️ No valid embeddings found")
            return
            
        # Convert to numpy array
        self.embeddings_array = np.array(embeddings, dtype=np.float32)
        self.names = names
        
        # Create FAISS index - using cosine similarity (Inner Product after normalization)
        faiss.normalize_L2(self.embeddings_array)
        
        dimension = self.embeddings_array.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity
        self.index.add(self.embeddings_array)
        
        self._is_built = True
        print(f"✅ Built FAISS index with {len(embeddings)} faces")

    def cosine_similarity(self, vec1, vec2):
        """Original cosine similarity function for fallback"""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot / (norm1 * norm2 + 1e-10)

    def find_best_match(self, embedding, threshold=0.5):
        """Find best match using FAISS if available, otherwise fallback to original method"""
        
        if FAISS_AVAILABLE and self._is_built and self.index is not None:
            # Use FAISS for fast search
            return self._find_best_match_faiss(embedding, threshold)
        else:
            # Fallback to original method
            return self._find_best_match_original(embedding, threshold)

    def _find_best_match_faiss(self, embedding, threshold=0.5):
        """FAISS-based search"""
        # Normalize query embedding
        query_embedding = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(query_embedding)
        
        # Search for best match
        scores, indices = self.index.search(query_embedding, 1)
        
        best_score = scores[0][0]
        best_idx = indices[0][0]
        
        if best_score > threshold:
            return (self.names[best_idx], float(best_score))
        else:
            return ("Unknown", float(best_score))

    def _find_best_match_original(self, embedding, threshold=0.5):
        """Original search method for fallback"""
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
    
    def update_database(self, new_db_embeddings):
        """Update the database and rebuild FAISS index"""
        self.db = new_db_embeddings
        
        if FAISS_AVAILABLE:
            self.build_index(new_db_embeddings)
        
        print(f"✅ Updated database with {len(new_db_embeddings)} faces")
    
    def rebuild_index(self):
        """Rebuild FAISS index"""
        if FAISS_AVAILABLE:
            self.build_index(self.db)
    
    def clear_cache(self):
        """Clear FAISS cache to save RAM"""
        if FAISS_AVAILABLE:
            self.index = None
            self.embeddings_array = None
            self.names = []
            self._is_built = False
            print("🧹 Cleared FAISS cache")