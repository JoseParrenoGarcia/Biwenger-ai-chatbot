# ----------------------------------------------------
# The specs file defines how the LLM sees the tools.
# ----------------------------------------------------
MAKE_PLAN_SPEC = {
  "type": "function",
  "function": {
    "name": "make_plan",
    "description": (
      "Plan the MINIMAL sequence of steps to satisfy the user's request using available tools.\n"
      "Allowed steps:\n"
      "  - 'load_biwenger_player_stats' (load season snapshot as a DataFrame)\n"
      "  - 'filter_df' (filter the current DataFrame; MUST include args.filters)\n"
      "Rules:\n"
      "  • Use the provided schema context; only use listed columns.\n"
      "  • If a column appears in value_hints (e.g., team, position, season), map user text to a canonical value from that list and use '==' (never 'contains').\n"
      "  • Return a PLAN object with keys: steps, why, assumptions. Do NOT return top-level 'filters' or any other shape.\n"
      "  • Use the exact key 'args' (lowercase) for step arguments.\n"
      "Always include 'why' (<=120 chars) and up to 3 short 'assumptions'."
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
              "tool": {
                "type": "string",
                "enum": ["load_biwenger_player_stats", "filter_df"]
              },
              "args": {
                "type": "object",
                "description": (
                  "Arguments for the step. For 'load_biwenger_player_stats', use an empty object {}. "
                  "For 'filter_df', provide 'filters' as a non-empty array of {col, op, val}."
                ),
                "properties": {
                  "filters": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "col": {"type": "string"},
                        "op": {
                          "type": "string",
                          "enum": ["==","!=",">",">=","<","<=","in","not_in","contains"]
                        },
                        "val": {}
                      },
                      "required": ["col","op","val"],
                      "additionalProperties": False
                    },
                    "minItems": 1
                  }
                },
                "additionalProperties": False  # <-- close the keyspace
              }
            },
            "required": ["tool","args"],        # <-- make args mandatory for every step
            "additionalProperties": False        # <-- no stray keys like 'Arguments'
          }
        },
        "why": {
          "type": "string",
          "maxLength": 120,
          "description": "One-sentence rationale."
        },
        "assumptions": {
          "type": "array",
          "items": {"type": "string", "maxLength": 120},
          "maxItems": 3
        }
      },
      "required": ["steps","why","assumptions"],
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