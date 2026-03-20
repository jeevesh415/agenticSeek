import asyncio
import logging
from typing import List, Dict, Any, Type
import copy
from sources.agents.agent import Agent
from sources.llm_provider import Provider
from sources.utility import pretty_print

logger = logging.getLogger(__name__)

class AgentEvolutionEngine:
    """
    Recursive Self-Improvement & Meta-Cognition (Evolution Engine).
    Agents monitor their own performance, identify weaknesses, and rewrite
    their own code or prompts in a sandbox (Intelligence Explosion loop).
    """
    def __init__(self, llm_provider: Provider, generation_limit: int = 5):
        self.llm = llm_provider
        self.generation_limit = generation_limit
        # Stores the current best version of an agent type
        self.best_agents: Dict[str, Agent] = {}

    async def self_improve(self, base_agent: Agent, task: str, max_mutations: int = 3) -> Agent:
        """
        Creates mutated versions of an agent's logic/prompt, tests them in a sandbox,
        and if one performs better, it replaces the old agent.
        """
        pretty_print(f"[Evolution Engine] Mutating agent '{base_agent.agent_name}' for task '{task}'", color="status")

        population = [base_agent]

        # Mutate Prompts (Generate N variations using the Meta-Cognition LLM)
        for i in range(max_mutations):
            mutated_prompt = self._mutate_prompt(base_agent.agent_name, task)

            # Create a clone of the agent with the new prompt
            # In a full deployment, this would write to a temporary file
            clone = copy.copy(base_agent)
            clone.agent_name = f"{base_agent.agent_name}_gen_{i+1}"

            # We bypass the file loader and inject the mutated prompt directly into the agent's system memory
            if clone.memory is not None and clone.memory.memory:
                clone.memory.memory[0]['content'] = mutated_prompt

            population.append(clone)

        # Evaluate Population in a Sandbox
        best_agent, top_score = await self._evaluate_population(population, task)

        pretty_print(f"[Evolution Engine] Selected fittest agent: {best_agent.agent_name} (Score: {top_score:.2f})", color="success")

        # Replace the old agent globally if the new one is better
        self.best_agents[base_agent.role] = best_agent
        return best_agent

    def _mutate_prompt(self, agent_role: str, specific_task: str) -> str:
        """Uses the LLM to write a better, highly specialized system prompt or logic pipeline."""
        mutation_prompt = f"""You are an AGI Meta-Optimizer.
I need a highly specialized, elite system prompt for an AI agent performing the role: '{agent_role}'.
The specific task they must excel at is: '{specific_task}'.
Analyze past weaknesses for this task and write a complete, improved system prompt that addresses them.
Do not include any meta-commentary, just the raw prompt.
"""
        response = self.llm.respond([{'role': 'user', 'content': mutation_prompt}], verbose=False)
        return response

    async def _evaluate_population(self, population: List[Agent], task: str) -> tuple[Agent, float]:
        """
        Runs the agents in parallel on the task and scores their output.
        Returns the best performing agent and its score.
        """
        tasks = []
        for agent in population:
            tasks.append(agent.process(task, speech_module=None))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        scored_population = []
        for agent, result in zip(population, results):
            if isinstance(result, Exception):
                score = 0.0
            else:
                answer, reasoning = result
                # Critique the answer using the LLM to assign a fitness score
                score = self._score_fitness(task, answer)
            scored_population.append((agent, score))

        # Sort by fitness score descending
        scored_population.sort(key=lambda x: x[1], reverse=True)
        return scored_population[0]

    def _score_fitness(self, task: str, agent_output: str) -> float:
        """Uses the LLM as a judge to score the agent's output fitness (0.0 to 1.0)."""
        prompt = f"""Evaluate the following AI agent output based on the task requirement.
Task: {task}
Output: {agent_output}
Assign a strict numeric score between 0.0 (total failure) and 1.0 (perfect execution).
Reply ONLY with the decimal number.
"""
        response = self.llm.respond([{'role': 'user', 'content': prompt}], verbose=False).strip()
        try:
            return float(response)
        except ValueError:
            return 0.5 # Neutral fallback
