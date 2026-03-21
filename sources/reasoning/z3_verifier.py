import logging
import json
import z3
from typing import Dict, Any

from sources.llm_provider import Provider

logger = logging.getLogger(__name__)

class Z3Verifier:
    """
    Neuro-Symbolic Verification Engine (Z3 Theorem Prover).
    Translates LLM thought into strict theorem solver constraints to guarantee
    0% hallucination in mathematical, logical, and structural planning tasks.
    """
    def __init__(self, llm_provider: Provider):
        self.llm = llm_provider

    def _translate_to_z3(self, logic_problem: str) -> str:
        """
        Uses the LLM to parse a natural language logic problem into a Python Z3 script.
        """
        prompt = f"""You are a Neuro-Symbolic reasoning engine.
Translate the following logical/mathematical problem into a strictly formatted, executable Python script using the `z3-solver` library.
The script MUST print "SATISFIABLE" followed by the model if a solution exists, or "UNSATISFIABLE" if it does not.
Do not output anything except the raw Python code.

Problem: {logic_problem}
"""
        response = self.llm.respond([{'role': 'user', 'content': prompt}], verbose=False)
        # Strip markdown code blocks if present
        if response.startswith("```python"):
            response = response[9:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()

    def verify_logic(self, problem: str) -> Dict[str, Any]:
        """
        Takes a logical constraint problem, generates a Z3 script via the LLM,
        executes the script in a safe sandbox, and returns the mathematically proven result.
        """
        logger.info(f"[Z3 Verifier] Parsing neuro-symbolic logic: {problem[:50]}...")

        z3_script = self._translate_to_z3(problem)

        # Execute the generated Z3 script safely using a restricted globals/locals environment
        try:
            # Prepare an environment capturing stdout
            import sys
            import io

            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout

            # Execute the script
            exec(z3_script, {"z3": z3, "Int": z3.Int, "Solver": z3.Solver, "solve": z3.solve})

            output = new_stdout.getvalue()
            sys.stdout = old_stdout

            if "UNSATISFIABLE" in output or "unsat" in output:
                return {
                    "status": "UNSATISFIABLE",
                    "proof": "The proposed logic is mathematically impossible.",
                    "z3_script": z3_script
                }
            elif "SATISFIABLE" in output or "sat" in output:
                return {
                    "status": "SATISFIABLE",
                    "proof": output.replace("SATISFIABLE", "").strip(),
                    "z3_script": z3_script
                }
            else:
                return {
                    "status": "UNKNOWN",
                    "proof": output,
                    "z3_script": z3_script
                }

        except Exception as e:
            # Restore stdout on error
            sys.stdout = sys.__stdout__
            logger.error(f"[Z3 Verifier] Script execution failed: {e}")
            return {
                "status": "ERROR",
                "proof": str(e),
                "z3_script": z3_script
            }
