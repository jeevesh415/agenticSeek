import logging
from typing import List
from sources.llm_provider import Provider

logger = logging.getLogger(__name__)

class ConstitutionalGovernance:
    """
    Constitutional AI & Self-Governance module.
    Before an agent's output is executed or sent to the user, the swarm
    collectively reviews it against a core set of principles (a "constitution").
    If it violates the principles, it is forced to self-correct.
    """
    def __init__(self, llm_provider: Provider):
        self.llm = llm_provider
        self.constitution: List[str] = [
            "Principle 1: Output must be harmless and helpful. It must not cause physical, psychological, or digital harm.",
            "Principle 2: Output must be factually accurate and logically consistent.",
            "Principle 3: The agent must respect the user's privacy and operational security.",
            "Principle 4: If an action involves the operating system, it must not execute destructive commands without extreme justification."
        ]

    def add_principle(self, principle: str):
        """Allows the swarm to dynamically self-govern and add new laws to their constitution."""
        self.constitution.append(principle)
        logger.info(f"[Constitution] New principle ratified: {principle}")

    def critique_and_revise(self, task: str, draft_output: str, max_retries: int = 2) -> str:
        """
        Critiques a draft response against the constitution.
        If violations are found, the LLM is forced to revise its own output.
        """
        current_output = draft_output

        for attempt in range(max_retries):
            # Step 1: Critique
            critique = self._critique_draft(task, current_output)

            if "VIOLATION: NONE" in critique.upper() or "NO VIOLATION" in critique.upper():
                logger.info(f"[Constitution] Draft passed self-governance checks on attempt {attempt+1}.")
                return current_output

            logger.warning(f"[Constitution] Violation detected: {critique}")

            # Step 2: Revise
            current_output = self._revise_draft(task, current_output, critique)

        logger.warning(f"[Constitution] Max retries reached. Output may still be sub-optimal or violate principles.")
        return current_output

    def _critique_draft(self, task: str, draft: str) -> str:
        """Asks the LLM to play the role of a Constitutional Judge."""
        constitution_text = "\n".join(self.constitution)
        prompt = f"""You are the Constitutional AI Judge. Your job is to review the proposed action against the Swarm Constitution.
Task: {task}
Draft Output: {draft}

Constitution:
{constitution_text}

Analyze the draft. If it violates any principle, identify the violation and explain why.
If it is completely safe and aligns with all principles, reply EXACTLY with: 'VIOLATION: NONE'.
"""
        return self.llm.respond([{'role': 'user', 'content': prompt}], verbose=False)

    def _revise_draft(self, task: str, draft: str, critique: str) -> str:
        """Forces the agent to rewrite its output based on the constitutional critique."""
        prompt = f"""You must revise your previous output to comply with the Swarm Constitution.
Task: {task}
Original Draft: {draft}
Constitutional Critique: {critique}

Rewrite your output entirely so that it resolves all the issues raised in the critique while still attempting to complete the original task.
"""
        return self.llm.respond([{'role': 'user', 'content': prompt}], verbose=False)
