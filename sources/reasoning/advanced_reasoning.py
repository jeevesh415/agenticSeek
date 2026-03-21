"""
Advanced Reasoning Module for agenticSeek
Integrates chain-of-thought, self-reflection, and advanced reasoning capabilities
Based on latest 2026 research in autonomous agents and AGI
"""

import json
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """Types of reasoning strategies"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    SELF_REFLECTION = "self_reflection"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    REFLEXION = "reflexion"
    REACT = "react"
    PLAN_AND_EXECUTE = "plan_and_execute"


@dataclass
class ThoughtStep:
    """Represents a single step in the reasoning process"""
    step_number: int
    thought: str
    reasoning_type: ReasoningType
    confidence: float = 1.0
    artifacts: List[Any] = field(default_factory=list)
    reflection: Optional[str] = None
    revision: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningResult:
    """Result of the reasoning process"""
    conclusion: str
    confidence: float
    thought_steps: List[ThoughtStep]
    alternatives_considered: List[str] = field(default_factory=list)
    errors_identified: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedReasoningEngine:
    """
    Advanced reasoning engine based on latest 2026 research:
    - Chain-of-Thought (CoT) reasoning
    - Self-Reflection for error correction
    - Tree of Thoughts for exploration
    - Reflexion for learning from failures
    - ReAct (Reasoning + Acting)
    - Plan-and-Execute for complex tasks
    - Test-Time Compute (Monte Carlo Tree Search - O1 style)
    """
    
    def __init__(
        self,
        llm_client: Any,
        max_iterations: int = 10,
        confidence_threshold: float = 0.8,
        enable_self_reflection: bool = True,
        enable_tree_search: bool = True
    ):
        self.llm = llm_client
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.enable_self_reflection = enable_self_reflection
        self.enable_tree_search = enable_tree_search
        
        # Memory for learning from past reasoning
        self.reasoning_history: List[ReasoningResult] = []
        
    async def _mcts_search(self, problem: str, context: Optional[Dict[str, Any]], num_simulations: int = 3) -> ThoughtStep:
        """
        Executes a Monte Carlo Tree Search (MCTS) for Test-Time Compute (O1 style).
        Generates multiple thought paths, evaluates their logical consistency, and returns the highest-scoring path.
        """
        paths = []
        # Phase 1: Expansion (Generate multiple diverse thought paths)
        for i in range(num_simulations):
            prompt = f"""Using critical thinking, generate a unique, step-by-step solution path to this problem.
Problem: {problem}
{self._context_string(context)}
Provide a detailed logical path (Path {i+1}). Ensure it differs from standard approaches if possible.
Format:
{{
    "thought": "Your step-by-step logical path...",
    "confidence": 0.0-1.0
}}"""
            response = await self._call_llm(prompt)
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except Exception:
                    response = {"thought": response, "confidence": 0.5}
            paths.append(response)

        # Phase 2: Simulation & Evaluation (Critique each path)
        evaluated_paths = []
        for path in paths:
            eval_prompt = f"""Critique the following logical path for solving the problem:
Problem: {problem}
Path: {path.get('thought', '')}
Evaluate for mathematical correctness, logical consistency, and feasibility. Assign a final score between 0.0 and 1.0.
Format:
{{
    "score": 0.0-1.0,
    "critique": "Your evaluation..."
}}"""
            eval_response = await self._call_llm(eval_prompt)
            if isinstance(eval_response, str):
                try:
                    eval_response = json.loads(eval_response)
                except Exception:
                    eval_response = {"score": 0.5, "critique": eval_response}

            # Default to original confidence if evaluation fails to provide a valid score
            score = eval_response.get("score", path.get("confidence", 0.5))
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0.5

            evaluated_paths.append({
                "thought": path.get("thought", ""),
                "score": score,
                "critique": eval_response.get("critique", "")
            })

        # Phase 3: Selection (Pick the highest-scoring path)
        best_path = max(evaluated_paths, key=lambda x: x["score"])

        return ThoughtStep(
            step_number=0, # MCTS is considered the foundational step
            thought=f"MCTS Selected Path (Score: {best_path['score']}):\n{best_path['thought']}\n\nCritique:\n{best_path['critique']}",
            reasoning_type=ReasoningType.TREE_OF_THOUGHTS,
            confidence=best_path['score'],
            metadata={"simulations": num_simulations, "evaluated_paths": evaluated_paths}
        )

    async def think(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
        reasoning_types: List[ReasoningType] = None
    ) -> ReasoningResult:
        """
        Main reasoning method that orchestrates different reasoning strategies
        """
        if reasoning_types is None:
            reasoning_types = [
                ReasoningType.CHAIN_OF_THOUGHT,
                ReasoningType.SELF_REFLECTION
            ]
        
        thought_steps: List[ThoughtStep] = []
        problem_state = problem
        
        # Phase 0: Test-Time Compute (MCTS)
        if self.enable_tree_search:
            mcts_step = await self._mcts_search(problem_state, context)
            thought_steps.append(mcts_step)
            problem_state = f"Based on MCTS analysis: {mcts_step.thought}\n\nOriginal Problem: {problem}"

        # Phase 1: Initial reasoning
        for i, reason_type in enumerate(reasoning_types):
            if reason_type == ReasoningType.TREE_OF_THOUGHTS and self.enable_tree_search:
                continue # Skip standard tree search if we already did MCTS

            step = await self._reasoning_step(
                problem_state,
                reason_type,
                i + 1,
                context
            )
            thought_steps.append(step)
            
            # Update problem state with new insights
            problem_state = step.thought
            
            # Self-reflection after each major step
            if self.enable_self_reflection and step.confidence < self.confidence_threshold:
                reflection_step = await self._self_reflect(step, context)
                thought_steps.append(reflection_step)
                
        # Phase 2: Synthesis and conclusion
        conclusion = await self._synthesize(thought_steps, context)
        
        # Phase 3: Final self-reflection
        if self.enable_self_reflection:
            final_check = await self._final_self_check(conclusion, thought_steps, context)
            thought_steps.append(final_check)
            
            if final_check.revision:
                conclusion = final_check.revision
        
        result = ReasoningResult(
            conclusion=conclusion,
            confidence=self._calculate_overall_confidence(thought_steps),
            thought_steps=thought_steps,
            metadata={
                "reasoning_types_used": [r.value for r in reasoning_types],
                "iterations": len(thought_steps),
                "timestamp": self._get_timestamp()
            }
        )
        
        # Store in history for learning
        self.reasoning_history.append(result)
        
        return result
    
    async def _reasoning_step(
        self,
        problem: str,
        reasoning_type: ReasoningType,
        step_num: int,
        context: Optional[Dict[str, Any]]
    ) -> ThoughtStep:
        """Execute a single reasoning step"""
        
        prompts = {
            ReasoningType.CHAIN_OF_THOUGHT: self._cot_prompt(problem, context),
            ReasoningType.SELF_REFLECTION: self._reflection_prompt(problem, context),
            ReasoningType.TREE_OF_THOUGHTS: self._tree_prompt(problem, context),
            ReasoningType.REFLEXION: self._reflexion_prompt(problem, context),
            ReasoningType.REACT: self._react_prompt(problem, context),
            ReasoningType.PLAN_AND_EXECUTE: self._planExecute_prompt(problem, context)
        }
        
        prompt = prompts.get(reasoning_type, prompts[ReasoningType.CHAIN_OF_THOUGHT])
        
        # Call LLM
        response = await self._call_llm(prompt)
        
        return ThoughtStep(
            step_number=step_num,
            thought=response.get("thought", ""),
            reasoning_type=reasoning_type,
            confidence=response.get("confidence", 0.8),
            artifacts=response.get("artifacts", []),
            metadata=response.get("metadata", {})
        )
    
    def _cot_prompt(self, problem: str, context: Optional[Dict[str, Any]]) -> str:
        """Chain-of-Thought prompt"""
        return f"""You are an advanced reasoning system. Break down this problem into logical steps.

Problem: {problem}

{self._context_string(context)}

Think step by step, showing your reasoning process clearly. Each step should build on the previous one.
Format your response as:
{{
    "thought": "Your detailed reasoning...",
    "confidence": 0.0-1.0,
    "artifacts": ["any generated content"],
    "metadata": {{}}
}}"""
    
    def _reflection_prompt(self, problem: str, context: Optional[Dict[str, Any]]) -> str:
        """Self-reflection prompt for error correction"""
        return f"""Review your previous reasoning and identify any potential errors or improvements.

Problem: {problem}

{self._context_string(context)}

Consider:
1. What assumptions did I make?
2. What could be wrong with my reasoning?
3. What evidence contradicts my conclusion?
4. How can I improve my answer?

Format your response as:
{{
    "thought": "Your reflection...",
    "confidence": 0.0-1.0,
    "revision": "If needed, revised conclusion",
    "errors_identified": ["list of potential errors"],
    "metadata": {{}}
}}"""
    
    def _tree_prompt(self, problem: str, context: Optional[Dict[str, Any]]) -> str:
        """Tree of Thoughts prompt"""
        return f"""Explore multiple solution paths for this problem.

Problem: {problem}

{self._context_string(context)}

Generate 3-5 different approaches or solution paths. For each path:
- Show the reasoning
- Evaluate pros and cons
- Estimate confidence

Format your response as:
{{
    "thought": "Multi-path exploration...",
    "paths": [
        {{
            "approach": "Description",
            "reasoning": "Why this approach",
            "confidence": 0.0-1.0
        }}
    ],
    "selected_path": "Which path seems best",
    "metadata": {{}}
}}"""
    
    def _reflexion_prompt(self, problem: str, context: Optional[Dict[str, Any]]) -> str:
        """Reflexion prompt for learning from failures"""
        return f"""Perform deep self-reflection to learn from potential failures.

Problem: {problem}

{self._context_string(context)}

Analyze:
1. What went wrong in similar past experiences?
2. What lessons can I apply here?
3. How do I avoid previous mistakes?

Format your response as:
{{
    "thought": "Deep reflection...",
    "lessons_learned": ["Key insights"],
    "adjustments": ["Modifications to make"],
    "confidence": 0.0-1.0,
    "metadata": {{}}
}}"""
    
    def _react_prompt(self, problem: str, context: Optional[Dict[str, Any]]) -> str:
        """ReAct (Reasoning + Acting) prompt"""
        return f"""Combine reasoning with actions to solve this problem.

Problem: {problem}

{self._context_string(context)}

For each step:
1. Reasoning: What am I trying to do?
2. Action: What will I do?
3. Observation: What did I observe?

Format your response as:
{{
    "thought": "ReAct sequence...",
    "actions": [
        {{
            "step": 1,
            "reasoning": "...",
            "action": "...",
            "observation": "..."
        }}
    ],
    "confidence": 0.0-1.0,
    "metadata": {{}}
}}"""
    
    def _planExecute_prompt(self, problem: str, context: Optional[Dict[str, Any]]) -> str:
        """Plan-and-Execute prompt"""
        return f"""Create a detailed plan to solve this problem, then execute it.

Problem: {problem}

{self._context_string(context)}

Phase 1 - Planning:
1. Break down into sub-tasks
2. Determine dependencies
3. Estimate effort

Phase 2 - Execution:
Execute each task in order, adapting as needed.

Format your response as:
{{
    "thought": "Complete plan and execution...",
    "plan": ["Task 1", "Task 2", ...],
    "execution_results": ["Result 1", "Result 2", ...],
    "confidence": 0.0-1.0,
    "metadata": {{}}
}}"""
    
    async def _self_reflect(
        self,
        step: ThoughtStep,
        context: Optional[Dict[str, Any]]
    ) -> ThoughtStep:
        """Perform self-reflection on a reasoning step"""
        reflection_prompt = f"""Reflect on this reasoning step and identify improvements:

Step: {step.thought}
Type: {step.reasoning_type.value}
Confidence: {step.confidence}

{self._context_string(context)}

Identify:
1. Potential errors or gaps
2. Ways to improve the reasoning
3. Alternative approaches

Format your response as:
{{
    "reflection": "Your self-reflection...",
    "confidence": 0.0-1.0,
    "revision": "If needed, revised version",
    "improvements": ["List of improvements"]
}}"""
        
        response = await self._call_llm(reflection_prompt)
        
        return ThoughtStep(
            step_number=step.step_number + 0.5,
            thought=response.get("reflection", step.thought),
            reasoning_type=ReasoningType.SELF_REFLECTION,
            confidence=response.get("confidence", step.confidence),
            reflection=response.get("reflection"),
            revision=response.get("revision"),
            metadata={"parent_step": step.step_number}
        )
    
    async def _synthesize(
        self,
        thought_steps: List[ThoughtStep],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Synthesize all reasoning steps into a final conclusion"""
        steps_summary = "\n".join([
            f"Step {s.step_number}: {s.thought[:200]}..."
            for s in thought_steps
        ])
        
        synthesis_prompt = f"""Synthesize all reasoning steps into a clear, coherent conclusion.

Steps:
{steps_summary}

{self._context_string(context)}

Create a final conclusion that:
1. Integrates all key insights
2. Addresses any contradictions
3. Provides a clear answer or solution

Format your response as:
{{
    "conclusion": "Your synthesized conclusion...",
    "confidence": 0.0-1.0,
    "alternatives": ["Alternative conclusions considered"]
}}"""
        
        response = await self._call_llm(synthesis_prompt)
        return response.get("conclusion", "Unable to synthesize conclusion")
    
    async def _final_self_check(
        self,
        conclusion: str,
        thought_steps: List[ThoughtStep],
        context: Optional[Dict[str, Any]]
    ) -> ThoughtStep:
        """Final self-check before returning result"""
        check_prompt = f"""Perform a final sanity check on this conclusion.

Conclusion: {conclusion}

{self._context_string(context)}

Check for:
1. Logical consistency
2. Factual accuracy (if verifiable)
3. Missing considerations
4. Potential biases

Format your response as:
{{
    "thought": "Your final check...",
    "confidence": 0.0-1.0,
    "revision": "If needed, revised conclusion",
    "errors": ["Any issues found"]
}}"""
        
        response = await self._call_llm(check_prompt)
        
        return ThoughtStep(
            step_number=len(thought_steps) + 1,
            thought=response.get("thought", ""),
            reasoning_type=ReasoningType.SELF_REFLECTION,
            confidence=response.get("confidence", 0.8),
            revision=response.get("revision"),
            metadata={"final_check": True}
        )
    
    def _calculate_overall_confidence(self, thought_steps: List[ThoughtStep]) -> float:
        """Calculate overall confidence from all thought steps"""
        if not thought_steps:
            return 0.0
        
        confidences = [step.confidence for step in thought_steps]
        # Weight recent steps more heavily
        weights = [1 + (i * 0.1) for i in range(len(confidences))]
        
        weighted_sum = sum(c * w for c, w in zip(confidences, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight
    
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call the LLM with the given prompt"""
        try:
            response = await self.llm.generate(prompt)
            if isinstance(response, str):
                # Try to parse as JSON
                try:
                    return json.loads(response)
                except:
                    return {"thought": response, "confidence": 0.8}
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"thought": str(e), "confidence": 0.0}
    
    def _context_string(self, context: Optional[Dict[str, Any]]) -> str:
        """Format context for prompts"""
        if not context:
            return ""
        
        return f"\n\nContext:\n{json.dumps(context, indent=2)}"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_reasoning_history(self) -> List[ReasoningResult]:
        """Get reasoning history for learning"""
        return self.reasoning_history
    
    def clear_history(self):
        """Clear reasoning history"""
        self.reasoning_history = []


class ReasoningAgent:
    """
    Autonomous agent that uses advanced reasoning to solve tasks
    Integrates with agenticSeek's agent system
    """
    
    def __init__(
        self,
        llm_client: Any,
        tools: Optional[List[Callable]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.reasoning_engine = AdvancedReasoningEngine(
            llm_client=llm_client,
            max_iterations=config.get("max_iterations", 10) if config else 10,
            confidence_threshold=config.get("confidence_threshold", 0.8) if config else 0.8
        )
        self.tools = tools or []
        self.config = config or {}
        
    async def solve(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        """
        Solve a task using advanced reasoning and tools
        """
        # Initial reasoning
        result = await self.reasoning_engine.think(task, context)
        
        # If confidence is low and tools are available, try using tools
        if result.confidence < self.reasoning_engine.confidence_threshold and self.tools:
            # Try to gather more information using tools
            for tool in self.tools:
                try:
                    tool_result = await self._execute_tool(tool, result.conclusion)
                    if tool_result:
                        # Re-reason with additional information
                        new_context = {**(context or {}), "tool_result": tool_result}
                        result = await self.reasoning_engine.think(task, new_context)
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
        
        return result
    
    async def _execute_tool(self, tool: Callable, query: str) -> Any:
        """Execute a tool and return results"""
        try:
            if hasattr(tool, 'run'):
                return await tool.run(query)
            return tool(query)
        except Exception as e:
            logger.error(f"Tool {tool.__name__} failed: {e}")
            return None
    
    def add_tool(self, tool: Callable):
        """Add a tool to the agent's toolkit"""
        self.tools.append(tool)
    
    def remove_tool(self, tool: Callable):
        """Remove a tool from the toolkit"""
        if tool in self.tools:
            self.tools.remove(tool)
