from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class CapabilityTrack:
    """Reusable capability track for advanced, production-grade agent systems."""

    name: str
    triggers: Tuple[str, ...]
    guidance: str


CAPABILITY_TRACKS: Tuple[CapabilityTrack, ...] = (
    CapabilityTrack(
        name="orchestration",
        triggers=("agent", "workflow", "planner", "multi-step", "autonomous"),
        guidance="Use a graph-based multi-agent orchestrator pattern (e.g., LangGraph-like state machine) with explicit task states and retries.",
    ),
    CapabilityTrack(
        name="memory-rag",
        triggers=("memory", "knowledge", "retrieval", "rag", "document", "search"),
        guidance="Add a retrieval layer (vector + keyword hybrid) and keep short-term vs long-term memory separated with explicit eviction rules.",
    ),
    CapabilityTrack(
        name="tooling",
        triggers=("tool", "integration", "api", "mcp", "ecosystem", "framework"),
        guidance="Define tools with strict schemas, sandboxed execution, and integration adapters for external services/MCP servers.",
    ),
    CapabilityTrack(
        name="eval-observability",
        triggers=("quality", "evaluation", "benchmark", "monitor", "trace", "reliability"),
        guidance="Ship eval harnesses and observability (structured logs, traces, and task-level metrics) before scaling autonomy.",
    ),
    CapabilityTrack(
        name="safety-alignment",
        triggers=("safe", "alignment", "policy", "guardrail", "agi", "asi"),
        guidance="Include policy checks, model-level guardrails, and execution-time risk gates with explicit refusal/escalation paths.",
    ),
    CapabilityTrack(
        name="deployment",
        triggers=("production", "deploy", "scaling", "latency", "cost", "infra"),
        guidance="Design for deployment with async queues, caching, fallback models, and clear SLO budgets for latency/cost.",
    ),
)


def suggest_capability_guidance(goal: str, limit: int = 4) -> List[str]:
    """Return ranked capability guidance lines based on goal content.

    The function is deterministic and lightweight so it can run for every planner request.
    """

    if not goal:
        return []

    goal_lower = goal.lower()
    scored: List[Tuple[int, str]] = []

    for track in CAPABILITY_TRACKS:
        score = sum(1 for trigger in track.triggers if trigger in goal_lower)
        if score > 0:
            scored.append((score, track.guidance))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [guidance for _, guidance in scored[:limit]]

    if not selected:
        # Default baseline for advanced planning when request is broad.
        selected = [
            "Plan with modular architecture: orchestration, memory, tool-use, evaluation, and safety should be explicit workstreams.",
            "Prioritize measurable milestones and validation checkpoints before adding more autonomous behavior.",
        ]
    return selected
