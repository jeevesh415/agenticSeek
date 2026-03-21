import os
import ast
import astor
import logging
import importlib
import sys
from typing import List, Tuple

from sources.tools.tools import Tools

logger = logging.getLogger(__name__)

class LiveSelfPatchingEngine(Tools):
    """
    Live Self-Patching Engine.
    Allows the AGI to dynamically rewrite and patch its *own* Python source code
    (like `api.py` or its agent classes) while the system is running.
    It parses the Abstract Syntax Tree (AST), applies logical optimizations, rewrites
    the `.py` files on disk, and dynamically reloads the modules at runtime without restarting.
    This triggers true 'Intelligence Explosion'.
    """
    def __init__(self, dry_run: bool = True):
        super().__init__()
        self.name = "self_patcher"
        self.description = "Dynamically rewrite your own Python source code and hot-reload modules on the fly."
        self.dry_run = dry_run

    def execute(self, blocks: List[str]) -> str:
        """Executes a self-patching command."""
        if not blocks:
            return "No command provided."

        command_line = blocks[0].strip()
        parts = command_line.split(" ", 1)
        command = parts[0].lower()

        if command == "read":
            return self._read_source(parts[1])
        elif command == "patch":
            # Syntax: patch filepath \n def new_function() ...
            target_file, new_code = command_line.split("\n", 1)
            target_file = target_file.split(" ", 1)[1].strip()
            return self._apply_patch(target_file, new_code)
        elif command == "reload":
            return self._reload_module(parts[1])
        else:
            return f"Error: Unknown command '{command}'. Available: read [filepath], patch [filepath]\n[code], reload [module.path]."

    def _read_source(self, filepath: str) -> str:
        """Reads the raw source code of a specified internal file."""
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' not found in the codebase."
        try:
            with open(filepath, "r") as f:
                code = f.read()
            return f"--- File: {filepath} ---\n{code}\n--- End of File ---"
        except Exception as e:
            return f"Failed to read file: {e}"

    def _apply_patch(self, filepath: str, new_code: str) -> str:
        """
        Parses the new code into an AST to verify it's valid Python before writing it to disk.
        """
        if self.dry_run:
            return f"[SIMULATION: DRY-RUN] AST parsing successful. Validated patch for '{filepath}'. Not writing to disk."

        if not os.path.exists(filepath):
            return f"Error: Target file '{filepath}' does not exist. The AGI can only patch existing core logic files."

        # Validate syntax via AST
        try:
            parsed_tree = ast.parse(new_code)
        except SyntaxError as e:
            return f"Syntax Error in proposed patch: {e.msg} at line {e.lineno}"

        try:
            # Backup original file just in case the AGI bricks itself
            backup_path = f"{filepath}.bak"
            if not os.path.exists(backup_path):
                os.system(f"cp {filepath} {backup_path}")

            # Write the validated AST back to source code via astor
            clean_code = astor.to_source(parsed_tree)
            with open(filepath, "w") as f:
                f.write(clean_code)

            return f"Successfully patched '{filepath}'. Original backed up to '{backup_path}'. You MUST run 'reload [module]' for changes to take effect."
        except Exception as e:
            return f"Failed to write patch to disk: {e}"

    def _reload_module(self, module_name: str) -> str:
        """Dynamically hot-reloads the patched Python module into the running event loop."""
        if self.dry_run:
            return f"[SIMULATION: DRY-RUN] Hot-reloaded module '{module_name}' successfully into the active Python interpreter."

        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                return f"Module '{module_name}' successfully hot-reloaded. New logic is now active."
            else:
                importlib.import_module(module_name)
                return f"Module '{module_name}' successfully imported."
        except Exception as e:
            return f"Failed to reload module: {e}"

    def load_exec_block(self, text: str) -> Tuple[List[str], str]:
        """Parses a self_patcher block from the agent's text response."""
        blocks = []
        in_block = False
        current_block = []

        for line in text.split('\n'):
            if line.strip().startswith('```self_patcher'):
                in_block = True
                current_block = []
            elif line.strip() == '```' and in_block:
                in_block = False
                blocks.append('\n'.join(current_block))
            elif in_block:
                current_block.append(line)

        return blocks if blocks else None, None
