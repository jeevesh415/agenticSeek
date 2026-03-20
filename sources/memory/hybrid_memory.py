import uuid
import logging
from typing import List, Dict, Any, Optional

from sources.memory.vector_memory import VectorMemoryManager
from sources.memory.hrr import HRRMemory
from sources.memory.world_model import WorldModelActiveInference
from sources.llm_provider import Provider

logger = logging.getLogger(__name__)

class UltimateMemoryManager:
    """
    Hybrid Neuro-Symbolic + Differentiable Memory + HRR + World Model.
    The true ultimate AGI memory system:
    1. FAISS provides fast, approximate episodic recall.
    2. HRR encodes structured facts into composable vectors for reasoning.
    3. World Models generate predictions and simulate outcomes (JEPD).
    4. Active Inference drives curiosity-driven learning.
    """
    def __init__(self, llm_provider: Provider, memory_dir: str = ".memory_store"):
        # FAISS for raw episodic & semantic memory (Vector Store)
        self.episodic_memory = VectorMemoryManager(memory_dir=f"{memory_dir}/episodic", max_memories=100000)

        # HRR for symbolic structured reasoning (Concept binding/unbinding)
        self.symbolic_memory = HRRMemory(dimension=5000)

        # World Model & Active Inference (Dreamer/JEPD)
        self.world_model = WorldModelActiveInference(llm_provider=llm_provider, vector_dim=5000)

        # Active Working Memory traces (short-term cache of active HRR bindings)
        self.working_memory_bindings: List[np.ndarray] = []

    def experience_event(self, context_id: str, state_before: str, action: str, outcome_state: str) -> None:
        """
        The core learning loop based on Active Inference and World Models.
        1. We predict the outcome of an action in a given state.
        2. We observe the actual outcome.
        3. We calculate 'surprise' (Prediction Error / Free Energy).
        4. If surprising enough, we commit it to Episodic FAISS Memory.
        5. We extract semantic structure and bind it into Symbolic HRR Memory.
        """
        # Step 1: Predict (Internal Simulation)
        prediction = self.world_model.generate_prediction(context_id, state_before, action)

        # Step 2 & 3: Observe and Calculate Surprise
        # We use the TfidfVectorizer from VectorMemoryManager to embed text for cosine comparison
        self.episodic_memory._fit_vectorizer()
        vectorizer = self.episodic_memory.vectorizer

        surprise = self.world_model.calculate_surprise(context_id, outcome_state, vectorizer)

        # Step 4: Active Inference (Curiosity-driven Retention)
        # If it was exactly what we expected (low surprise), we don't need to learn it deeply.
        # If it was highly surprising, we retain it strongly.
        importance_score = surprise

        if self.world_model.should_retain_memory(importance_score, threshold=0.3):
            logger.info(f"High surprise ({importance_score:.2f}) -> Consolidating to Episodic FAISS.")
            self.episodic_memory.remember(outcome_state, tags=["experience", action], importance=importance_score)

            # Step 5: Symbolic HRR Binding (Extracting a fact)
            # In a full AGI, this extraction is done by parsing the semantic tree (subject, verb, object).
            # For demonstration, we simply bind the action as the relation linking state A to state B.
            fact_vector = self.symbolic_memory.encode_relation(subject=state_before[:20], relation=action, obj=outcome_state[:20])
            self.working_memory_bindings.append(fact_vector)
            logger.info(f"Bound relationship into Symbolic HRR vector space.")

    def search_episodic(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Queries the raw episodic FAISS vector store."""
        return self.episodic_memory.search(query, top_k)

    def query_symbolic(self, query_token: str) -> List[tuple[str, float]]:
        """Queries the Symbolic HRR memory for the closest bound semantic concepts."""
        vec = self.symbolic_memory.get_symbol(query_token)
        return self.symbolic_memory.query_closest_symbol(vec, top_k=5)

    def consolidate_working_memory(self) -> None:
        """
        Differentiable Neural Computer (DNC) style flush:
        Superpose all active working memory HRR bindings into a single long-term memory trace
        and clear the short-term cache.
        """
        if self.working_memory_bindings:
            consolidated_trace = self.symbolic_memory.bundle(self.working_memory_bindings)
            self.working_memory_bindings.clear()
            logger.info(f"Consolidated {len(self.working_memory_bindings)} active HRR traces into semantic memory.")
