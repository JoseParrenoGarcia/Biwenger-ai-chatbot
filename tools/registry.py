# ----------------------------------------------------
# The registry file defines how your app runs them.
# ----------------------------------------------------
from typing import Callable, Dict, Any
from tools.supabase_tools import load_biwenger_player_stats

# --- 1. Define mapping of tool name to Python callable ---
TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "load_biwenger_player_stats": load_biwenger_player_stats,
}

# --- 2. Optional helper: unified executor ---
def execute_tool(tool_name: str, args: dict | None = None) -> Any:
    """
    Executes a registered tool by name.
    Raises a clear error if the tool name is unknown.
    """
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        raise ValueError(f"Unknown tool: {tool_name}")
    return fn(**(args or {}))
