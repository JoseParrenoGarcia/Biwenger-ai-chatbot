# ----------------------------------------------------
# The specs file defines how the LLM sees the tools.
# ----------------------------------------------------
MAKE_PLAN_SPEC = {
    "type": "function",
    "function": {
        "name": "make_plan",
        "description": (
            "Plan a minimal sequence of steps to satisfy the user's request. "
            "Understand the user's intent and decompose it into a series of calls to available tools. "
            "For example, only read a table, or read and process the data by filtering, aggregating, etc, or even generating plots."
            "Return STRICT JSON matching the schema of {steps, why, assumptions}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": { "type": "string", "enum": ["load_biwenger_player_stats"] },
                            "args": { "type": "object" }
                        },
                        "required": ["tool"]
                    }
                },
                "why": {
                    "type": "string",
                    "description": "One-sentence rationale (<=120 chars).",
                    "maxLength": 120
                },
                "assumptions": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "maxLength": 120
                    },
                    "maxItems": 3,
                    "description": "0–3 short bullets that state key assumptions."
                }
            },
            "required": ["steps", "why", "assumptions"],
            "additionalProperties": False
        }
    }
}

LOAD_BIWENGER_PLAYER_STATS_SPEC = {
    "type": "function",
    "function": {
        "name": "load_biwenger_player_stats",
        "description": (
            "Load the full Biwenger player **season snapshot** table from Supabase (cached, read-only). "
            "Each row is one player with cumulative season metrics as of `as_of_date` "
            "(fields include: player_name, team, position, points, matches_played, average (which is average points), "
            "value/min_value/max_value, market_purchases_pct, market_sales_pct, market_usage_pct, season, as_of_date). "
            "Use this when the user asks for player statistics, totals, averages, values or market % at the season snapshot level."
        ),
        "parameters": {
            "type": "object",
            "properties": {},              # no arguments yet; full snapshot
            "additionalProperties": False
        }
    }
}

# Router will see ONLY the planner:
PLANNER_TOOL_SPECS = [MAKE_PLAN_SPEC]

# Executor knows about concrete runtime functions:
EXECUTION_TOOL_SPECS = [LOAD_BIWENGER_PLAYER_STATS_SPEC]