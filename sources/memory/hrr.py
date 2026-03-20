import numpy as np

class HRRMemory:
    """
    Holographic Reduced Representations (HRR) / Vector Symbolic Architecture.
    Allows compositional encoding of structured knowledge into a single high-dimensional vector.
    This enables analogical reasoning, binding, and unbinding of concepts (e.g., subject * verb * object).
    """
    def __init__(self, dimension: int = 10000):
        self.dim = dimension
        self.vocab = {}

    def _generate_random_vector(self) -> np.ndarray:
        """Generates a random high-dimensional vector drawn from a normal distribution N(0, 1/d)."""
        vec = np.random.normal(0, 1.0 / np.sqrt(self.dim), self.dim)
        # Normalize the vector to unit length
        return vec / np.linalg.norm(vec)

    def get_symbol(self, token: str) -> np.ndarray:
        """Retrieves or creates a base vector representation for a symbolic token."""
        if token not in self.vocab:
            self.vocab[token] = self._generate_random_vector()
        return self.vocab[token]

    def bind(self, vec1: np.ndarray, vec2: np.ndarray) -> np.ndarray:
        """
        Binds two vectors together using Circular Convolution.
        This operation creates a new vector representing the composition of both concepts.
        """
        # Circular convolution is equivalent to element-wise multiplication in the Fourier domain
        result = np.fft.irfft(np.fft.rfft(vec1) * np.fft.rfft(vec2), n=self.dim)
        # Re-normalize to prevent magnitude explosion over multiple bindings
        norm = np.linalg.norm(result)
        if norm > 0:
             return result / norm
        return result

    def unbind(self, bound_vec: np.ndarray, known_vec: np.ndarray) -> np.ndarray:
        """
        Unbinds a known vector from a bound vector to retrieve the other component
        using Circular Correlation (the approximate inverse of convolution).
        """
        # Circular correlation is element-wise multiplication with the complex conjugate in the Fourier domain
        inv_known = np.fft.rfft(known_vec).conj()
        result = np.fft.irfft(np.fft.rfft(bound_vec) * inv_known, n=self.dim)
        norm = np.linalg.norm(result)
        if norm > 0:
            return result / norm
        return result

    def bundle(self, vectors: list[np.ndarray]) -> np.ndarray:
        """
        Bundles (superposes) multiple vectors into a single memory trace using vector addition.
        The resulting vector is similar to all constituent vectors.
        """
        if not vectors:
            return np.zeros(self.dim)
        result = np.sum(vectors, axis=0)
        norm = np.linalg.norm(result)
        if norm > 0:
            return result / norm
        return result

    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculates the cosine similarity between two vectors."""
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-10))

    def query_closest_symbol(self, target_vec: np.ndarray, top_k: int = 3) -> list[tuple[str, float]]:
        """Finds the base vocabulary symbols that are most similar to the target vector."""
        if not self.vocab:
            return []

        similarities = []
        for token, vec in self.vocab.items():
            sim = self.similarity(target_vec, vec)
            similarities.append((token, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def encode_relation(self, subject: str, relation: str, obj: str) -> np.ndarray:
        """
        Encodes a structured relationship: (Subject * Role_Subject) + (Relation * Role_Relation) + (Object * Role_Object)
        This is a classic Vector Symbolic Architecture encoding scheme.
        """
        v_subj = self.get_symbol(subject)
        v_rel = self.get_symbol(relation)
        v_obj = self.get_symbol(obj)

        # We need role vectors to position them contextually
        r_subj = self.get_symbol("__ROLE_SUBJECT__")
        r_rel = self.get_symbol("__ROLE_RELATION__")
        r_obj = self.get_symbol("__ROLE_OBJECT__")

        bound_subj = self.bind(v_subj, r_subj)
        bound_rel = self.bind(v_rel, r_rel)
        bound_obj = self.bind(v_obj, r_obj)

        # Superpose them into a single memory trace representing the entire fact
        return self.bundle([bound_subj, bound_rel, bound_obj])
