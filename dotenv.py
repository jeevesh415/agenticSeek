"""Compatibility shim for python-dotenv.

If python-dotenv is installed, this module forwards `load_dotenv` to the real package
instead of overriding it with a no-op.
"""

from importlib.machinery import PathFinder
from importlib.util import module_from_spec
from pathlib import Path
import sys


def _load_real_dotenv():
    current_dir = str(Path(__file__).resolve().parent)
    search_paths = [p for p in sys.path if str(Path(p).resolve()) != current_dir]
    spec = PathFinder.find_spec("dotenv", search_paths)
    if spec is None or spec.loader is None:
        return None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_real_dotenv = _load_real_dotenv()

if _real_dotenv and hasattr(_real_dotenv, "load_dotenv"):
    load_dotenv = _real_dotenv.load_dotenv
else:
    def load_dotenv(*_args, **_kwargs):
        return False
