import os
import faiss
import numpy as np
import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Using scikit-learn's TfidfVectorizer as a lightweight, local alternative to heavy Transformer models
# for semantic vectorization, avoiding the massive VRAM overhead of loading SentenceTransformers locally.
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

class VectorMemoryManager:
    """
    FAISS-powered Vector Memory System.
    Provides fast, long-term semantic search across thousands of past interactions and facts.
    Uses TF-IDF for lightweight, local vector embeddings to allow it to run perfectly on CPU.
    """
    def __init__(self, memory_dir: str = ".memory_store", max_memories: int = 10000):
        self.memory_dir = memory_dir
        self.max_memories = max_memories

        # We use a relatively small fixed dimension for TF-IDF (e.g., 5000) to keep FAISS fast
        self.vector_dim = 5000

        # IndexFlatL2 is an exact search index using L2 distance (Euclidean)
        self.index = faiss.IndexFlatL2(self.vector_dim)

        self.vectorizer = TfidfVectorizer(max_features=self.vector_dim, stop_words='english')

        # In-memory maps mapping FAISS IDs (integers) to actual memory data
        self.id_to_memory: Dict[int, Dict[str, Any]] = {}
        self.current_id = 0

        # Training corpus to fit the TF-IDF vectorizer initially (prevents vocabulary errors)
        self.corpus = ["Initial training document to seed vocabulary.", "Artificial general intelligence.", "Swarm memory architectures."]
        self.is_vectorizer_fitted = False

        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir)

        self.load_index()

    def _fit_vectorizer(self):
        if not self.is_vectorizer_fitted:
            self.vectorizer.fit(self.corpus)
            self.is_vectorizer_fitted = True

    def _get_embedding(self, text: str) -> np.ndarray:
        """Converts text into a fixed-length vector."""
        self._fit_vectorizer()

        # Transform returns a sparse matrix, we convert it to a dense array and force float32 for FAISS
        vector = self.vectorizer.transform([text]).toarray()[0].astype(np.float32)

        # If the vocabulary is smaller than vector_dim, we must pad the vector with zeros so FAISS accepts it
        if len(vector) < self.vector_dim:
            padded_vector = np.zeros(self.vector_dim, dtype=np.float32)
            padded_vector[:len(vector)] = vector
            return padded_vector

        return vector

    def remember(self, text: str, tags: Optional[List[str]] = None, importance: float = 0.5):
        """
        Stores a piece of information into long-term vector memory.
        """
        if self.index.ntotal >= self.max_memories:
            logger.warning("Max memories reached. In a future update, implement memory decay/consolidation here.")
            return

        # Add to corpus to dynamically adjust vocabulary on next fit (if needed)
        self.corpus.append(text)

        # Ensure we refit if we've added substantial data (simplified for this implementation)
        self.vectorizer.fit(self.corpus)
        self.is_vectorizer_fitted = True

        vector = self._get_embedding(text)

        # FAISS expects a 2D array (n_samples, dimensions)
        self.index.add(np.array([vector]))

        memory_obj = {
            "id": self.current_id,
            "text": text,
            "tags": tags or [],
            "importance": importance,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.id_to_memory[self.current_id] = memory_obj
        self.current_id += 1

        self.save_index()
        logger.info(f"Stored memory: '{text[:50]}...' (ID: {memory_obj['id']})")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves the most semantically relevant memories using fast FAISS vector search.
        """
        if self.index.ntotal == 0:
            return []

        vector = self._get_embedding(query)

        # search returns distances and indices
        distances, indices = self.index.search(np.array([vector]), min(top_k, self.index.ntotal))

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx in self.id_to_memory:
                # Lower L2 distance means higher similarity
                memory = self.id_to_memory[idx].copy()
                memory["distance"] = float(distances[0][i])
                results.append(memory)

        return results

    def save_index(self):
        """Saves the FAISS index and metadata to disk."""
        try:
            faiss.write_index(self.index, os.path.join(self.memory_dir, "faiss.index"))
            with open(os.path.join(self.memory_dir, "metadata.json"), "w") as f:
                json.dump({
                    "current_id": self.current_id,
                    "id_to_memory": self.id_to_memory,
                    "corpus": self.corpus
                }, f)
        except Exception as e:
            logger.error(f"Failed to save FAISS memory index: {e}")

    def load_index(self):
        """Loads the FAISS index and metadata from disk if they exist."""
        index_path = os.path.join(self.memory_dir, "faiss.index")
        meta_path = os.path.join(self.memory_dir, "metadata.json")

        if os.path.exists(index_path) and os.path.exists(meta_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(meta_path, "r") as f:
                    data = json.load(f)
                    self.current_id = data.get("current_id", 0)
                    # JSON keys are always strings, need to convert back to int
                    self.id_to_memory = {int(k): v for k, v in data.get("id_to_memory", {}).items()}
                    self.corpus = data.get("corpus", self.corpus)
                logger.info(f"Loaded FAISS memory index with {self.index.ntotal} records.")
                self.is_vectorizer_fitted = False # Force refit on loaded corpus
            except Exception as e:
                logger.error(f"Failed to load FAISS memory index: {e}")
                # Reset if corrupted
                self.index = faiss.IndexFlatL2(self.vector_dim)
                self.id_to_memory = {}
                self.current_id = 0
