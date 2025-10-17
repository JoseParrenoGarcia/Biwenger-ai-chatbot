# ----------------------------------------------------
# tools/registry.py
# Central runtime registry for executing tools & plans
# ----------------------------------------------------
from typing import Callable, Dict, Any

# --- Import deterministic callables ---
from tools.supabase_tools import load_biwenger_player_stats
from tools.dataframe_transformation_tools import apply_filters

# --- Core registry of callable tools ---
TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "load_biwenger_player_stats": load_biwenger_player_stats,
    "filter_df": apply_filters,
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
def execute_plan(plan: dict):
    steps = plan.get("steps", [])
    if not steps:
        raise ValueError("Plan has no steps.")
    current = None
    for step in steps:
        tool = step.get("tool")
        args = step.get("args", {}) or {}

        if tool == "load_biwenger_player_stats":
            current = execute_tool(tool, args)  # returns a DataFrame
        elif tool == "filter_df":
            if current is None:
                raise ValueError("filter_df requires a DataFrame from a prior step.")
            # inject the df expected by apply_filters(df, filters)
            current = execute_tool(tool, {"df": current, **args})
        else:
            raise ValueError(f"Unknown tool: {tool}")

    if current is None:
        raise ValueError("Plan produced no data.")
    return current
