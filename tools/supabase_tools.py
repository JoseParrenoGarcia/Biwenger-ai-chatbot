from typing import Sequence, Optional
from supabase import create_client, Client
from pathlib import Path
import tomllib
import pandas as pd


# ---------- 1) Client loader (reads ./secrets/supabase.toml) ----------
def get_supabase_client() -> Client:
    """
    Returns an authenticated Supabase client using ./secrets/supabase.toml by default.
    File format:
        [supabase]
        url = "https://xxx.supabase.co"
        anon_key = "xxx"
    """
    secrets_path = (
        Path(__file__).resolve().parent.parent / "secrets" / "supabase.toml"
    )

    if not secrets_path.exists():
        raise FileNotFoundError(f"Missing secrets file at: {secrets_path}")

    with open(secrets_path, "rb") as f:
        cfg = tomllib.load(f)

    url = cfg.get("supabase", {}).get("url")
    key = cfg.get("supabase", {}).get("anon_key")
    if not url or not key:
        raise KeyError("Missing 'url' or 'anon_key' in supabase.toml")

    return create_client(url, key)

# ---------- 2) Function to fetch any data from Supabase ----------
def fetch_all_rows(
    client: Client,
    table: str,
    columns: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    order_by: Optional[str] = None,
    ascending: bool = True,
    page_size: int = 1000,   # practical PostgREST cap
) -> pd.DataFrame:
    """
    Pages through `table` and returns a DataFrame.
    - columns: explicit projection (None -> "*")
    - limit: optional hard cap (stops early)
    - order_by: optional single-column ordering
    """
    select_clause = ",".join(columns) if columns else "*"
    out_rows: list[dict] = []
    fetched = 0
    start = 0

    while True:
        q = client.table(table).select(select_clause)
        if order_by:
            q = q.order(order_by, desc=not ascending)

        # respect the global limit if provided
        effective_page = page_size
        if limit is not None:
            remaining = max(limit - fetched, 0)
            if remaining == 0:
                break
            effective_page = min(effective_page, remaining)

        res = q.range(start, start + effective_page - 1).execute()
        data = getattr(res, "data", None) or []
        if not data:
            break

        out_rows.extend(data)
        batch = len(data)
        fetched += batch
        start += batch

        if batch < effective_page:
            break

    return pd.DataFrame(out_rows)



if __name__ == "__main__":
    from pprint import pprint

    # 1. Test connection
    try:
        supabase = get_supabase_client()
        print("✅ Connected to Supabase successfully.")

        # Minimal test: try selecting 0 rows from the 'articles' table (if it exists)
        try:
            result = supabase.table("articles").select("*").limit(1).execute()
            print("📦 Sample query from 'articles' table succeeded.")
            pprint(result.data)
        except Exception as query_err:
            print("⚠️ Connection OK, but table query failed (maybe table doesn't exist yet):")
            print(query_err)

    except Exception as e:
        print("❌ Failed to connect to Supabase.")
        print(e)

    # 2. xxx
