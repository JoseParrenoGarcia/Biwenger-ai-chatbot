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

        # categorical hints (teams/positions/seasons) from value_hints
        vh = schema_spec.get("value_hints", {}) or {}
        # keep hints compact; only names and up to ~12 values each
        cats_lines = []
        for k, meta in vh.items():
            values = meta.get("values", [])
            if values:
                cats_lines.append(f"- {k}: {values[:12]}")
        cats_block = "\n".join(cats_lines) if cats_lines else "None"

        categorical_guidance = rules.get("categorical_guidance", "")

        columns_block = "\n".join(f"- {name}: {dtype}" for name, dtype in cols.items()) or "None"

        prompt = textwrap.dedent(f"""
        You write ONE pandas snippet that transforms an existing DataFrame named df_in into df_out.

        RULES (strict):
        - Use ONLY these columns and dtypes:
        {columns_block}
        - Date columns: {date_cols}
        - Categorical hints (subset):
        {cats_block}
        - Guidance: {categorical_guidance}
        - Imports: only "import pandas as pd".
        - Start with: df = df_in.copy()
        - If filtering a date column, ensure datetime: df['col'] = pd.to_datetime(df['col'], errors='coerce')
        - End with: df_out = df
        - No file/network I/O. No other libraries. No prose—return CODE ONLY.

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
