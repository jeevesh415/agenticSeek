from .agent import Agent

__all__ = [
    "Agent",
    "CasualAgent",
    "CoderAgent",
    "FileAgent",
    "PlannerAgent",
    "BrowserAgent",
    "McpAgent",
]


def _missing_dependency_agent(class_name: str, error: ModuleNotFoundError):
    class _MissingDependencyAgent(Agent):
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                f"Cannot initialize {class_name}: missing optional dependency {error.name!r}."
            ) from error

        async def process(self, prompt, speech_module):
            raise ModuleNotFoundError(
                f"Cannot run {class_name}: missing optional dependency {error.name!r}."
            ) from error

    _MissingDependencyAgent.__name__ = class_name
    return _MissingDependencyAgent


# Keep package-level imports backward-compatible without eager imports
# of optional/heavy dependencies at import time.
def __getattr__(name):
    targets = {
        "CasualAgent": (".casual_agent", "CasualAgent"),
        "CoderAgent": (".code_agent", "CoderAgent"),
        "FileAgent": (".file_agent", "FileAgent"),
        "PlannerAgent": (".planner_agent", "PlannerAgent"),
        "BrowserAgent": (".browser_agent", "BrowserAgent"),
        "McpAgent": (".mcp_agent", "McpAgent"),
    }
    if name not in targets:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, class_name = targets[name]
    try:
        module = __import__(f"{__name__}{module_name}", fromlist=[class_name])
        return getattr(module, class_name)
    except ModuleNotFoundError as error:
        return _missing_dependency_agent(class_name, error)
