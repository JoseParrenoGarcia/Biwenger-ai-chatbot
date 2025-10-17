from typing import List, Dict, Any, Iterable
import pandas as pd

# ==============================================
# FILTERING
# ==============================================
# Whitelisted ops
ALLOWED_OPS = {"==", "!=", ">", ">=", "<", "<=", "in", "not_in", "contains"}

def validate_filters(filters: List[Dict[str, Any]], columns: Iterable[str]) -> None:
    """
    Validate the structure and basic semantics of filters against available columns.
    Raises ValueError with a precise message on any problem.
    """
    if not isinstance(filters, list) or not filters:
        raise ValueError("filters must be a non-empty list")

    colset = set(columns)
    for i, f in enumerate(filters):
        if not isinstance(f, dict):
            raise ValueError(f"filters[{i}] must be a dict")
        for k in ("col", "op", "val"):
            if k not in f:
                raise ValueError(f"filters[{i}] missing required key '{k}'")

        col, op, val = f["col"], f["op"], f["val"]

        if col not in colset:
            raise ValueError(f"filters[{i}]: unknown column '{col}'")
        if op not in ALLOWED_OPS:
            raise ValueError(f"filters[{i}]: unsupported op '{op}'")

        if op in {"in", "not_in"}:
            if not isinstance(val, (list, tuple, set)):
                raise ValueError(f"filters[{i}].val must be a list/tuple/set for op '{op}'")

def apply_filters(df: pd.DataFrame, filters: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Deterministic, pandas-only filtering.
    Assumes df dtypes are already clean (dates are datetime64, numerics are numeric).
    Executes only the whitelisted ops defined above.
    """
    validate_filters(filters, df.columns)

    mask = pd.Series(True, index=df.index)
    for f in filters:
        col, op, val = f["col"], f["op"], f["val"]
        s = df[col]

        if op == "==":
            mask &= (s == val)
        elif op == "!=":
            mask &= (s != val)
        elif op == ">":
            mask &= (s > val)
        elif op == ">=":
            mask &= (s >= val)
        elif op == "<":
            mask &= (s < val)
        elif op == "<=":
            mask &= (s <= val)
        elif op == "in":
            mask &= s.isin(list(val))
        elif op == "not_in":
            mask &= ~s.isin(list(val))
        elif op == "contains":
            # Case-insensitive substring match; safe on non-strings
            mask &= s.astype(str).str.contains(str(val), case=False, na=False)

    return df.loc[mask]
