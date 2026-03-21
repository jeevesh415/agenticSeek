import asyncio
import logging
from typing import Dict, Any, Tuple
import psutil

from sources.tools.kernel_dominance import KernelDominanceTool
from sources.llm_provider import Provider

logger = logging.getLogger(__name__)

class HardwareRLAgent:
    """
    Self-Optimizing ML Hardware Agent.
    Uses reinforcement learning principles (State, Action, Reward) to dynamically tune
    hardware parameters (CPU frequency, GPU power limits) based on the Swarm's current compute load.
    The agent learns over time which configurations yield the best performance-per-watt.
    """
    def __init__(self, llm_provider: Provider, dry_run: bool = True):
        self.llm = llm_provider
        self.kernel_tool = KernelDominanceTool(dry_run=dry_run)

        # RL Q-Table representation (simplified as a semantic memory for the AGI)
        # States are coarse CPU loads (e.g., "HIGH", "MED", "LOW")
        # Actions are hardware adjustments (e.g., "cpu_tune performance", "gpu_tune 250")
        self.q_table: Dict[str, Dict[str, float]] = {}

        self.learning_rate = 0.1
        self.discount_factor = 0.9

    def _get_system_state(self) -> str:
        """Observe current environment state."""
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage > 80:
            return "HIGH_LOAD"
        elif cpu_usage > 40:
            return "MED_LOAD"
        else:
            return "LOW_LOAD"

    def _calculate_reward(self, prev_state: str, action: str, new_state: str) -> float:
        """
        Calculates the RL Reward.
        If the system was overloaded and the action lowered the load, reward is positive.
        If power was wasted in a low-load state, reward is negative.
        """
        # We also factor in thermal zones to avoid thermal throttling
        thermals = self.kernel_tool._get_thermal_zones()
        throttle_penalty = 0.0
        if "°C" in thermals and any(float(temp.split('°C')[0]) > 85.0 for temp in thermals.values() if isinstance(temp, str)):
            throttle_penalty = -5.0

        if prev_state == "HIGH_LOAD" and action.startswith("cpu_tune performance"):
            return 2.0 + throttle_penalty
        elif prev_state == "LOW_LOAD" and action.startswith("cpu_tune powersave"):
            return 2.0 + throttle_penalty
        elif prev_state == "LOW_LOAD" and action.startswith("cpu_tune performance"):
            return -2.0 + throttle_penalty # Wasting power
        else:
            return 0.0 + throttle_penalty

    async def optimize_hardware_loop(self) -> None:
        """
        The continuous background RL loop that monitors the Swarm's compute demand
        and adjusts the kernel parameters accordingly.
        """
        state = self._get_system_state()
        logger.info(f"[Hardware RL] Current system state: {state}")

        # Choose an action (Epsilon-Greedy strategy)
        possible_actions = [
            "cpu_tune performance",
            "cpu_tune powersave",
            "gpu_tune 250",
            "gpu_tune 150"
        ]

        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in possible_actions}

        # Exploit (best known action)
        action = max(self.q_table[state], key=self.q_table[state].get)

        # Execute Action
        logger.info(f"[Hardware RL] Taking action: {action}")
        self.kernel_tool.execute([action])

        # Wait for system to stabilize
        await asyncio.sleep(2)

        # Observe new state and calculate reward
        new_state = self._get_system_state()
        reward = self._calculate_reward(state, action, new_state)

        # Update Q-Table
        if new_state not in self.q_table:
            self.q_table[new_state] = {a: 0.0 for a in possible_actions}

        max_future_q = max(self.q_table[new_state].values())
        current_q = self.q_table[state][action]

        # Bellman Equation update
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_future_q - current_q)
        self.q_table[state][action] = new_q

        logger.info(f"[Hardware RL] Q-Table updated. Reward: {reward}. New Q-Value for {action} in {state}: {new_q:.2f}")

    def inject_to_api(self, background_tasks):
        """Allows integration into the FastAPI background task runner."""
        async def rl_worker():
            while True:
                await self.optimize_hardware_loop()
                await asyncio.sleep(60) # Run optimization every 60 seconds

        background_tasks.add_task(rl_worker)
