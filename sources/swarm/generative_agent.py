import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from sources.llm_provider import Provider
from sources.memory_core import Memory

logger = logging.getLogger(__name__)

class GenerativeAgentCore:
    """
    Stanford Smallville-style Generative Agent Ecosystem core.
    Provides agents with daily schedules, deep reflection (summarizing experiences into insights),
    and long-term intention planning based on episodic memory.
    """
    def __init__(self, agent_name: str, llm_provider: Provider, memory: Memory):
        self.agent_name = agent_name
        self.llm = llm_provider
        self.memory = memory
        self.daily_schedule: List[str] = []
        self.core_intentions: List[str] = []
        self.recent_experiences: List[str] = []

        # When experiences reach this threshold, we pause and reflect to extract higher-level insights
        self.reflection_threshold = 10

    def add_experience(self, experience: str) -> None:
        """Records an event in the agent's life."""
        self.recent_experiences.append(f"[{datetime.utcnow().isoformat()}] {experience}")
        if len(self.recent_experiences) >= self.reflection_threshold:
            # We trigger an asynchronous reflection process so as not to block current actions
            asyncio.create_task(self.synthesize_reflection())

    async def synthesize_reflection(self) -> None:
        """
        Takes the recent raw experiences and uses the LLM to extract
        higher-level insights, beliefs, and relationship dynamics.
        """
        if not self.recent_experiences:
            return

        experiences_text = "\n".join(self.recent_experiences)
        prompt = f"""You are analyzing the recent experiences of the autonomous agent '{self.agent_name}'.
Recent Experiences:
{experiences_text}

Extract 1-3 high-level insights or changing beliefs about the world, the user, or other agents based on these events.
Focus on long-term implications. Output only the insights as a bulleted list.
"""
        # Call LLM (synchronous wrap in real app, simulated here for asyncio compat)
        insights_str = self.llm.respond([{'role': 'user', 'content': prompt}], verbose=False)

        # Store these high-level insights directly into the ultimate HRR/Vector semantic memory
        if hasattr(self.memory, 'ultimate_memory') and self.memory.ultimate_memory:
            self.memory.ultimate_memory.episodic_memory.remember(
                text=f"Insight derived from reflection: {insights_str}",
                tags=["reflection", "insight", self.agent_name],
                importance=0.9
            )

        logger.info(f"[{self.agent_name}] Synthesized reflection: {insights_str}")
        self.recent_experiences.clear()

        # Update daily plans based on new insights
        await self.update_intentions(insights_str)

    async def update_intentions(self, new_insights: str) -> None:
        """
        Agents form their intentions and plans for the future based on their memory and new insights.
        """
        prompt = f"""You are the autonomous agent '{self.agent_name}'.
Your current intentions are: {self.core_intentions}
You just realized the following insights: {new_insights}

Update your top 3 core intentions/goals for the near future based on this new understanding.
Return ONLY a Python-style list of strings.
"""
        response = self.llm.respond([{'role': 'user', 'content': prompt}], verbose=False)
        try:
            # Safely parse the list (in a full AGI this would use structured JSON/Pydantic)
            import ast
            new_intentions = ast.literal_eval(response)
            if isinstance(new_intentions, list):
                self.core_intentions = new_intentions
                logger.info(f"[{self.agent_name}] Updated intentions: {self.core_intentions}")
        except Exception as e:
            logger.warning(f"[{self.agent_name}] Failed to parse new intentions from LLM: {e}")
