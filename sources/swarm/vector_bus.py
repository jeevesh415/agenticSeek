import asyncio
import logging
from typing import Dict, List, Callable
import numpy as np

from sources.memory.hrr import HRRMemory

logger = logging.getLogger(__name__)

class SharedVectorBus:
    """
    Shared Vector Communication Bus for AGI Swarms.
    Agents publish and subscribe to high-dimensional Holographic Reduced Representations (HRR)
    rather than brittle text strings, enabling composable, semantic, and analogical broadcast messages.
    """
    def __init__(self, dimension: int = 5000):
        self.hrr = HRRMemory(dimension=dimension)
        # Topics mapped to lists of async callback functions
        self.subscribers: Dict[str, List[Callable]] = {}
        # Stores the current aggregated "world state" vector of the swarm
        self.global_state_vector = np.zeros(dimension)

    def subscribe(self, topic: str, callback: Callable):
        """Allows an agent to listen to a specific semantic channel."""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        logger.debug(f"New subscriber attached to topic: {topic}")

    async def publish(self, topic: str, concept: str, context: str):
        """
        An agent publishes a concept. The bus translates it to a structured HRR vector,
        updates the global swarm state, and broadcasts the vector to all subscribers.
        """
        # Encode the message into a composed vector: (Topic * Role_Topic) + (Concept * Role_Concept)
        v_topic = self.hrr.get_symbol(topic)
        v_concept = self.hrr.get_symbol(concept)
        v_context = self.hrr.get_symbol(context)

        r_topic = self.hrr.get_symbol("__ROLE_TOPIC__")
        r_concept = self.hrr.get_symbol("__ROLE_CONCEPT__")
        r_context = self.hrr.get_symbol("__ROLE_CONTEXT__")

        bound_topic = self.hrr.bind(v_topic, r_topic)
        bound_concept = self.hrr.bind(v_concept, r_concept)
        bound_context = self.hrr.bind(v_context, r_context)

        # The bundled message vector
        message_vector = self.hrr.bundle([bound_topic, bound_concept, bound_context])

        # Update the global continuous swarm state (Meta-memory)
        self.global_state_vector = self.hrr.bundle([self.global_state_vector, message_vector])

        if topic in self.subscribers:
            # Broadcast the pure mathematical vector to all subscribed agents
            tasks = [callback(message_vector) for callback in self.subscribers[topic]]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def query_global_state(self, target_concept: str) -> float:
        """
        Agents can query the current global "vibe" or state of the swarm
        to see if a specific concept is highly active across the network.
        """
        v_concept = self.hrr.get_symbol(target_concept)
        return self.hrr.similarity(self.global_state_vector, v_concept)
