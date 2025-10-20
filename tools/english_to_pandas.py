# tools/english_to_pandas.py
from __future__ import annotations
from typing import Any, Dict, Optional
import textwrap
from llm_clients.openai_client import get_openai_client, get_default_model

# Optional: normalize dtypes just for the prompt (keeps it short & clear)
_DTYPE_MAP = {
    "int8": "int", "int4": "int",
    "float8": "float",
    "text": "string",
    "date": "date",
    "timestamptz": "datetime",
}
def _norm_dtype(d: str) -> str:
    return _DTYPE_MAP.get(d, d)

class EnglishToPandas:
    """
    NL -> pandas code (string). Assumes df_in already exists (loaded elsewhere).
    Expects llm_client.complete(prompt: str) -> str
    """

    def __init__(self):
        pass

    def generate_code(
        self,
        user_query: str,
        schema_spec: Dict[str, Any],          # <- pass _SCHEMA_REGISTRY[table]
        alias_hints: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Returns a pandas snippet as a string. The snippet MUST:
          - import pandas as pd
          - start with: df = df_in.copy()
          - coerce date columns before comparisons if used
          - end with: df_out = df
        """

        # --- derive prompt context directly from your registry shape ---
        # columns: list of {"name","dtype"} -> dict name->dtype (normalized for readability)
        cols_list = schema_spec.get("columns", [])
        cols = {c["name"]: _norm_dtype(c["dtype"]) for c in cols_list}

        # single date column from rules.date_column (if present)
        rules = schema_spec.get("rules", {}) or {}
        date_col = rules.get("date_column")
        date_cols = [date_col] if date_col else []

        vh = schema_spec.get("value_hints", {}) or {}
        team_canon = (vh.get("team", {}) or {}).get("values", [])
        pos_canon = (vh.get("position", {}) or {}).get("values", [])
        season_canon = (vh.get("season", {}) or {}).get("values", [])

        columns_block = "\n".join(f"- {name}: {dtype}" for name, dtype in cols.items()) or "None"
        alias_hints = alias_hints or {}
        alias_str = ", ".join(f"{k} -> {v}" for k, v in alias_hints.items()) or "None"

        # Keep canonical lists short but explicit
        canon_block = textwrap.dedent(f"""\
                Canonical values:
                - team: {team_canon}
                - position: {pos_canon}
                - season: {season_canon}
                """).strip()

        prompt = textwrap.dedent(f"""
                You write ONE pandas snippet that transforms an existing DataFrame named df_in into df_out.

                RULES (strict):
                - Use ONLY these columns and dtypes:
                {columns_block}
                - Date columns: {date_cols}
                - {canon_block}
                - Alias hints: {alias_str}
                - Categorical policy:
                  * NEVER modify categorical columns (e.g., NO df['team'].replace(...)).
                  * Filter using EXACT equality (==) against canonical values only.
                  * If the user mentions a non-canonical alias (e.g., "Madrid"), map via alias_hints if present;
                    otherwise choose the canonical value that the alias clearly refers to (e.g., "Real Madrid").
                - Date policy:
                  * If filtering by a month or range, coerce the date column once:
                      df['{date_col}'] = pd.to_datetime(df['{date_col}'], errors='coerce')
                    Then use inclusive bounds with ISO strings: 
                      (df['{date_col}'] >= 'YYYY-MM-DD') & (df['{date_col}'] <= 'YYYY-MM-DD')
                    Do NOT filter with .dt.year/.dt.month when a concrete month range is implied.
                - Imports: only "import pandas as pd".
                - Start with: df = df_in.copy()
                - End with: df_out = df
                - No file/network I/O. No other libraries. Return CODE ONLY (no prose).

                USER REQUEST:
                {user_query}
                """).strip()

        # --- Call OpenAI directly (simple + explicit) ---
        client = get_openai_client()
        model = get_default_model()

        messages = [
            {"role": "system", "content": "You output ONLY valid Python pandas code — no prose."},
            {"role": "user", "content": prompt},
        ]

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        raw = (resp.choices[0].message.content or "").strip()

        # # tolerate fenced responses (``` or ```python/```json)
        # if raw.startswith("```"):
        #     first_nl = raw.find("\n")
        #     raw = raw[first_nl + 1:] if first_nl != -1 else raw
        #     if raw.endswith("```"):
        #         raw = raw[:-3]
        #     raw = raw.strip()

        return raw
