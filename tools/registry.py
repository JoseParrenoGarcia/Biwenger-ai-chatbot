# ----------------------------------------------------
# tools/registry.py
# Central runtime registry for executing tools & plans
# ----------------------------------------------------
from typing import Callable, Dict, Any

# --- Import deterministic callables ---
from tools.supabase_tools import load_biwenger_player_stats
# (later you'll import df_tools.filter_df, etc.)

# --- Core registry of callable tools ---
TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "load_biwenger_player_stats": load_biwenger_player_stats,
    # Later you'll add: "filter_df": df_tools.execute_filter_plan, etc.
}

# --- Unified executor for individual tools ---
def execute_tool(tool_name: str, args: dict | None = None) -> Any:
    """
    Executes a registered tool by name.
    Raises a clear error if the tool name is unknown.
    """
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        raise ValueError(f"Unknown tool: {tool_name}")
    return fn(**(args or {}))

# --- Plan executor (for multi-step plans) ---
def execute_plan(plan: dict) -> Any:
    """
    Executes a multi-step plan (Plan IR) where each step corresponds to
    a registered tool. Returns the final DataFrame or object.
    """
    steps = plan.get("steps", [])
    if not steps:
        raise ValueError("Plan has no steps.")
    df = None
    for step in steps:
        tool = step.get("tool")
        args = step.get("args", {}) or {}
        df = execute_tool(tool, args)
    if df is None:
        raise ValueError("Plan produced no data.")
    return df
