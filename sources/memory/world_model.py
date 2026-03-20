import numpy as np
import logging
from typing import Dict, Any, Tuple
from sources.llm_provider import Provider

logger = logging.getLogger(__name__)

class WorldModelActiveInference:
    """
    World Model & Active Inference Engine (Dreamer / JEPD style).
    Simulates a predictive internal simulation of the environment.
    Calculates Free Energy / Prediction Error ("Surprise") to drive curiosity and attention.
    """
    def __init__(self, llm_provider: Provider, vector_dim: int = 5000):
        self.llm = llm_provider
        self.vector_dim = vector_dim
        # A dictionary holding predictions keyed by session or context ID
        self.predictions: Dict[str, str] = {}

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def generate_prediction(self, context_id: str, current_state: str, action: str) -> str:
        """
        Uses the LLM to build a continuous, predictive simulation of what will happen next
        given the current state and a planned action.
        """
        prompt = f"""You are the World Model (JEPD). Predict the immediate next state of the environment.
Current State: {current_state}
Planned Action: {action}
What will likely happen next? Provide a concise prediction.
"""
        prediction = self.llm.respond([{'role': 'user', 'content': prompt}], verbose=False)
        self.predictions[context_id] = prediction
        logger.info(f"[World Model] Predicted state for {context_id}: {prediction[:100]}...")
        return prediction

    def calculate_surprise(self, context_id: str, actual_outcome: str, vectorizer) -> float:
        """
        Active Inference (Free Energy Principle).
        Calculates the prediction error ('Surprise') between the expected world state and the actual outcome.
        High surprise indicates the agent encountered something novel and must update its beliefs.
        """
        prediction = self.predictions.get(context_id)
        if not prediction:
            # If we didn't predict this, it's 100% surprising
            return 1.0

        # We use the TF-IDF vectorizer (from VectorMemoryManager) to embed both states into latent space
        # Transform returns a sparse matrix; convert to dense
        try:
             vec_pred = vectorizer.transform([prediction]).toarray()[0].astype(np.float32)
             vec_actual = vectorizer.transform([actual_outcome]).toarray()[0].astype(np.float32)

             similarity = self._cosine_similarity(vec_pred, vec_actual)

             # Surprise is the inverse of similarity (1 - sim).
             # 0 means perfect prediction (no surprise), 1 means complete mismatch (max surprise).
             surprise = 1.0 - max(0.0, similarity)
             logger.info(f"[Active Inference] Surprise factor: {surprise:.4f} (Similarity: {similarity:.4f})")
             return surprise
        except Exception as e:
            logger.error(f"[Active Inference] Failed to calculate surprise: {e}")
            return 1.0

    def should_retain_memory(self, surprise_score: float, threshold: float = 0.6) -> bool:
        """
        Determines if a memory is important enough to consolidate based on how surprising it was.
        """
        return surprise_score > threshold
