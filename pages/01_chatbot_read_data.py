# app/streamlit_app.py
import json
import streamlit as st

from tools.specs import PLANNER_TOOL_SPECS, EXECUTION_TOOL_SPECS
from tools.registry import execute_tool
from llm_clients.router import route_to_tool

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
        st.subheader("LLM route")

        user_text = st.text_input(
            "Type a request (e.g., 'show me player stats')",
            "show me player stats"
        )

        st.markdown("**Tools advertised to the LLM (preview):**")
        st.code(json.dumps(EXECUTION_TOOL_SPECS, indent=2), language="json")

        colA, colB = st.columns([1, 1])
        route_clicked = colA.button("Route with LLM", type="primary")
        run_clicked = colB.button("Route + Execute")

        # Keep latest plan in session so routing and execution can be separate clicks
        if "llm_plan" not in st.session_state:
            st.session_state.llm_plan = None

        if route_clicked or run_clicked:
            try:
                with st.spinner("Routing…"):
                    plan = route_to_tool(user_text, PLANNER_TOOL_SPECS)   # pure plan: {tool_name, args, confidence}
                st.session_state.llm_plan = plan
                st.success(f"Planned tool: `{plan.tool_name}` (confidence={plan.confidence:.2f})")
                with st.expander("Plan (JSON)"):
                    st.json(plan.model_dump())
            except Exception as e:
                st.session_state.llm_plan = None
                st.error(f"Routing failed: {e}")

        # Execute if we have a plan and user clicked "Route + Execute"
        if run_clicked and st.session_state.llm_plan:
            try:
                with st.spinner("Executing tool…"):
                    plan = st.session_state.llm_plan
                    df = execute_tool(plan.tool_name, plan.args)
                st.success(f"Executed `{plan.tool_name}` → {len(df)} rows")
                st.dataframe(df, use_container_width=True, height=480)

            except Exception as e:
                st.error("❌ Failed to execute tool")
                st.exception(e)

st.markdown("---")
st.caption(
    "Notes: Left column calls the registry directly. Right column shows the LLM-facing tool specs and a "
    "mock plan. When we add LLM routing, we’ll replace the mock with a real `tool_call` and reuse the same executor."
)
