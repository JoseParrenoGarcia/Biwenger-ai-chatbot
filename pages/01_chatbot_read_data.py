# app/streamlit_app.py
import json
import pandas as pd
import streamlit as st

from tools.registry import execute_tool
from tools.specs import TOOL_SPECS  # just to show what's exposed to the LLM later

st.set_page_config(page_title="EDA Chatbot — Dual Route Prototype", layout="wide")
st.title("EDA Chatbot — Phase R0: Deterministic vs. LLM Route (scaffold)")

st.caption("Left = deterministic tool call. Right = reserved for LLM routing (UI + stubs).")

col_left, col_right = st.columns(2, gap="large")

# ----------------------------
# LEFT: Deterministic route
# ----------------------------
with col_left:
    with st.container(border=True):
        st.subheader("Deterministic route (manual tool)")

        # Simulated user query (fixed)
        query = "show me player stats"
        st.markdown(f"**User query (fixed):** {query}")

        # Chosen tool (fixed for now)
        tool_name = "load_biwenger_player_stats"
        st.markdown(f"**Router output (simulated):** `{tool_name}`")

        if st.button("Run tool (deterministic)", type="primary"):
            st.info(f"Executing tool: `{tool_name}` …")
            try:
                df = execute_tool(tool_name, args={})  # no args yet
                st.success(f"Fetched {len(df)} rows via `{tool_name}`")
                st.dataframe(df, use_container_width=True, height=480)

                # quick glance at columns
                with st.expander("Columns returned"):
                    st.write(list(df.columns))
            except Exception as e:
                st.error(f"❌ Tool `{tool_name}` failed")
                st.exception(e)
        else:
            st.info("Click **Run tool (deterministic)** to load data from Supabase (cached).")

# ----------------------------
# RIGHT: LLM route (scaffold)
# ----------------------------
with col_right:
    with st.container(border=True):
        st.subheader("LLM route (coming soon)")

        # This is the UI we’ll keep; we’ll just replace the mock plan with a real LLM call later.
        user_text = st.text_input("Type a request (e.g., 'show me player stats')", "show me player stats")

        st.markdown("**Tools advertised to the LLM (preview):**")
        st.code(json.dumps(TOOL_SPECS, indent=2), language="json")

        # --- MOCK plan to show what will be returned by the LLM later ---
        # For now we simulate the plan; later you'll call the model and parse its tool_call.
        mock_plan = {
            "tool_name": "load_biwenger_player_stats",  # what the model would likely choose
            "args": {}                                  # no args yet
        }
        with st.expander("Planned tool call (mock)"):
            st.json(mock_plan)

        # Button that *will* run the selected tool once LLM is wired
        if st.button("Execute planned tool (mock)"):
            try:
                df = execute_tool(mock_plan["tool_name"], mock_plan.get("args", {}))
                st.success(f"LLM plan executed: {mock_plan['tool_name']} → {len(df)} rows")
                st.dataframe(df, use_container_width=True, height=480)
            except Exception as e:
                st.error("❌ Failed to execute planned tool")
                st.exception(e)

st.markdown("---")
st.caption(
    "Notes: Left column calls the registry directly. Right column shows the LLM-facing tool specs and a "
    "mock plan. When we add LLM routing, we’ll replace the mock with a real `tool_call` and reuse the same executor."
)
