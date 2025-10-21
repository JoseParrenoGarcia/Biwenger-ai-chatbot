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
      # "  - 'filter_df' (apply deterministic filters to the current DataFrame; MUST include args.filters)\n"
      "  - 'translate_to_pandas' (emit a pandas code string that expects df_in and sets df_out; no execution)\n"
      "Guidance:\n"
      "  • Prefer the shortest path (usually: load_biwenger_player_stats → ONE of {filter_df | translate_to_pandas}).\n"
      "  • Do NOT include any execution step for pandas code; just return the code string when using translate_to_pandas.\n"
      "  • Use the provided schema context; only use listed columns.\n"
      "  • For columns present in value_hints (e.g., team, position, season): map user text to a canonical value from that list and use exact equality (==). Never modify categorical values in-place.\n"
      "  • For date filtering, prefer inclusive ISO bounds (>= start & <= end) over year/month extraction when a concrete range is implied.\n"
      "Return shape:\n"
      "  • A PLAN object with keys: steps, why, assumptions (no top-level 'filters' or other keys).\n"
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
                "enum": ["load_biwenger_player_stats", "translate_to_pandas"]
                # "enum": ["load_biwenger_player_stats", "filter_df", "translate_to_pandas"]
              },
              "args": {
                "type": "object",
                "description": (
                  "Arguments for the step.\n"
                  "- For 'load_biwenger_player_stats', use an empty object {}.\n"
                  "- For 'filter_df', provide 'filters' as a non-empty array of {col, op, val}.\n"
                  "- For 'translate_to_pandas', provide 'query' with the user's natural-language request."
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
                  },
                  "query": {
                    "type": "string",
                    "description": "Only for 'translate_to_pandas': the user request to translate into pandas code."
                  }
                },
                "additionalProperties": False
              }
            },
            "required": ["tool","args"],
            "additionalProperties": False
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

TRANSLATE_TO_PANDAS_SPEC = {
    "type": "function",
    "function": {
        "name": "translate_to_pandas",
        "description": (
            "Translate a natural-language query into pandas code that reads df_in and outputs df_out. "
            "Use only columns from the schema context and canonical categorical values from value_hints. "
            "Return code only, not prose or explanations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The natural-language query to translate."}
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}



# Router will see ONLY the planner:
PLANNER_TOOL_SPECS = [MAKE_PLAN_SPEC]

# Executor knows about concrete runtime functions:
EXECUTION_TOOL_SPECS = [
    LOAD_BIWENGER_PLAYER_STATS_SPEC,
    TRANSLATE_TO_PANDAS_SPEC
]