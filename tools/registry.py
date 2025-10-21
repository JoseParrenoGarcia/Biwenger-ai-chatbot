# ----------------------------------------------------
# tools/registry.py
# Central runtime registry for executing tools & plans
# ----------------------------------------------------
from typing import Callable, Dict, Any

# --- Import deterministic callables ---
from tools.supabase_tools import load_biwenger_player_stats
from tools.dataframe_transformation_tools import apply_filters
from tools.english_to_pandas import EnglishToPandas
import json
from tools.schema_catalog import get_planner_context

# --- Core registry of callable tools ---
TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "load_biwenger_player_stats": load_biwenger_player_stats,
    # "filter_df": apply_filters,
    "translate_to_pandas": EnglishToPandas().generate_code,
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
            current = execute_tool(tool, {"df": current, **args})

        elif tool == "translate_to_pandas":
            # 1) get schema for the active table (here fixed; parameterize later if needed)
            schema_spec = get_planner_context("biwenger_player_stats")
            if isinstance(schema_spec, str):
                try:
                    schema_spec = json.loads(schema_spec)
                except Exception:
                    pass

            # 2) run translator with correct argument names
            code = EnglishToPandas().generate_code(
                user_query=args.get("query", ""),
                schema_spec=schema_spec,
            )

            # 3) return *code only* (no execution yet). Stop here.
            return {"python_code": code}

        else:
            raise ValueError(f"Unknown tool: {tool}")

    if current is None:
        raise ValueError("Plan produced no data.")
    return current
