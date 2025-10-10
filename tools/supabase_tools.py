from typing import Optional, List
from supabase import create_client, Client
from pathlib import Path
import tomllib
import pandas as pd
from functools import lru_cache
import streamlit as st

# ---------- 0) Cached data ----------
try:
    def cache_data(ttl: Optional[int] = None):
        def _wrap(fn):
            # keep a few variants if you later add args
            cached = lru_cache(maxsize=4)(fn)
            return cached
        return _wrap

    STREAMLIT = False

except Exception:  # not running in functools
    def cache_data(ttl: Optional[int] = 3600):
        return st.cache_data(show_spinner=False, ttl=ttl)

    STREAMLIT = True


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
def _fetch_all_rows_from_supabase_raw(
    table_name: str,
    page_size: int = 1000,
) -> pd.DataFrame:
    """
    Read ALL rows from `table_name` using simple pagination. No filters, no ordering.
    Returns a pandas DataFrame (empty if the table has no rows).

    Notes:
    - If the table is large, this will load it fully into memory.
    - For Streamlit, wrap this with st.cache_data to avoid repeated downloads.
    """
    supabase = get_supabase_client()

    rows: List[dict] = []
    start = 0

    while True:
        # Request a fixed window [start, start+page_size-1]
        res = supabase.table(table_name).select("*").range(start, start + page_size - 1).execute()
        batch = getattr(res, "data", None) or []
        if not batch:
            break

        rows.extend(batch)
        got = len(batch)
        start += got

        # If we got fewer rows than requested, that was the last page.
        if got < page_size:
            break

    return pd.DataFrame(rows)


# ---------- 3) Cached wrappers to call by specific functions ----------
@cache_data(ttl=3600)  # adjust TTL (seconds) to your freshness needs
def fetch_all_rows_from_supabase(table_name: str) -> pd.DataFrame:
    """
    Cached "read entire table" helper.
    In Streamlit, this uses st.cache_data; otherwise an in-process LRU.
    """
    return _fetch_all_rows_from_supabase_raw(table_name=table_name)

# ---------- 4) Table-specific loading functions  ----------
def load_biwenger_player_stats() -> pd.DataFrame:
    """
    Loads the full 'biwenger_player_stats' table (cached).
    """
    df = fetch_all_rows_from_supabase("biwenger_player_stats")
    return df


if __name__ == "__main__":
    pd.set_option('display.max_columns', None)

    # 1. Test connection
    try:
        supabase = get_supabase_client()
        print("✅ Connected to Supabase successfully.")

    except Exception as e:
        print("❌ Failed to connect to Supabase.")
        print(e)

    print('' + '='*70 + '\n')

    # 2. Reading all rows from a table
    try:
        df = _fetch_all_rows_from_supabase_raw("biwenger_player_stats")
        print(f"📥 Fetched {len(df)} rows from 'biwenger_player_stats' table.")
        print(df.head(3))
    except Exception as e:
        print("❌ Failed to fetch rows from 'biwenger_player_stats' table.")
        print(e)

    print('' + '=' * 70 + '\n')

    # 3. Cached read
    try:
        df_cached = load_biwenger_player_stats()
        print(f"📥 (Cached) Fetched {len(df_cached)} rows from 'biwenger_player_stats' table.")
        print(df_cached.head(3))
    except Exception as e:
        print("❌ Failed to fetch rows from 'biwenger_player_stats' table.")
        print(e)