import asyncio
import logging
from typing import List, Dict, Any, Tuple
from sources.agents.agent import Agent

logger = logging.getLogger(__name__)

class SwarmDAO:
    """
    Decentralized Autonomous Agents (DAO of Agents).
    Agents coordinate via a trustless "ledger" mechanism where they bid for compute
    resources and vote on the best execution paths. This provides resilience against
    single points of failure in the orchestration layer.
    """
    def __init__(self):
        self.ledger: List[Dict[str, Any]] = []
        # Total compute budget for the swarm. Agents spend this to perform tasks.
        self.compute_treasury = 1000.0

    async def distribute_task(self, task: str, agents: List[Agent]) -> Agent:
        """
        Agents review the task and "bid" based on their perceived confidence and efficiency.
        The DAO automatically allocates the task to the lowest-cost/highest-confidence bidder.
        """
        bids = []
        for agent in agents:
            # In a full AGI, agents calculate their own confidence and compute cost independently
            # based on their specialized skills (e.g., Coder vs Browser)
            confidence, compute_cost = self._calculate_bid(agent, task)
            bids.append((agent, confidence, compute_cost))

        # Sort by best value (highest confidence, lowest cost)
        bids.sort(key=lambda x: x[1] / (x[2] + 0.1), reverse=True)
        winning_agent, winning_confidence, winning_cost = bids[0]

        if self.compute_treasury >= winning_cost:
            self.compute_treasury -= winning_cost
            self._record_transaction(winning_agent.agent_name, task, winning_cost, winning_confidence)
            logger.info(f"[Swarm DAO] {winning_agent.agent_name} won the bid with {winning_confidence:.2f} confidence for {winning_cost} compute.")
            return winning_agent
        else:
            logger.warning("[Swarm DAO] Insufficient compute funds in treasury to execute task.")
            return None

    def _calculate_bid(self, agent: Agent, task: str) -> Tuple[float, float]:
        """
        Simulates an agent submitting a bid for a task.
        A specialized agent will have higher confidence and lower compute cost.
        """
        # Determine affinity between agent's role and the task
        task_lower = task.lower()
        confidence = 0.5
        cost = 10.0

        if agent.role == "coder" and ("code" in task_lower or "script" in task_lower):
            confidence = 0.95
            cost = 5.0
        elif agent.role == "browser" and ("search" in task_lower or "web" in task_lower):
            confidence = 0.95
            cost = 5.0
        elif agent.role == "file" and ("file" in task_lower or "directory" in task_lower):
            confidence = 0.90
            cost = 3.0

        return confidence, cost

    def _record_transaction(self, agent_name: str, task: str, cost: float, expected_confidence: float):
        """Records the transaction on the internal decentralized ledger."""
        transaction = {
            "agent": agent_name,
            "task": task[:50] + "...",
            "compute_cost": cost,
            "expected_confidence": expected_confidence,
            "status": "ALLOCATED"
        }
        self.ledger.append(transaction)
