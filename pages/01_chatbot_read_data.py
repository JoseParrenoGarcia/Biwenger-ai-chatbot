# app/streamlit_app.py
import json
import streamlit as st

from tools.specs import PLANNER_TOOL_SPECS, EXECUTION_TOOL_SPECS
from tools.registry import execute_tool, execute_plan
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
        st.code("""
        Router will see ONLY the planner: 
        PLANNER_TOOL_SPECS = [MAKE_PLAN_SPEC]
         
        Executor knows about concrete runtime functions: 
        EXECUTION_TOOL_SPECS = [LOAD_BIWENGER_PLAYER_STATS_SPEC]""",
                language="python")

        colA, colB = st.columns([1, 1])
        route_clicked = colA.button("Route with LLM", type="primary")
        run_clicked = colB.button("Route + Execute")

        # Keep latest plan in session so routing and execution can be separate clicks
        if "llm_plan" not in st.session_state:
            st.session_state.llm_plan = None

        # Route (plan) --------------------------------------
        if route_clicked or run_clicked:
            try:
                with st.spinner("Planning…"):
                    plan_call = route_to_tool(user_text, PLANNER_TOOL_SPECS)  # ToolCall for make_plan
                plan_dict = plan_call.args  # <-- the Plan IR dict
                st.session_state.llm_plan = plan_dict
                st.success("Planned ✔")
                with st.expander("Plan (JSON)"):
                    st.json(plan_dict)  # show steps/why/assumptions
            except Exception as e:
                st.session_state.llm_plan = None
                st.error(f"Planning failed: {e}")

        # Execute (run the plan steps) -----------------------
        if run_clicked and st.session_state.llm_plan:
            try:
                with st.spinner("Executing plan…"):
                    df = execute_plan(st.session_state.llm_plan)  # <-- run steps, not make_plan
                st.success(f"Executed plan → {len(df)} rows")
                st.dataframe(df, use_container_width=True, height=480)
            except Exception as e:
                st.error("❌ Failed to execute plan")
                st.exception(e)

st.markdown("---")
st.caption(
    "Notes: Left column calls the registry directly. Right column shows the LLM-facing tool specs and a "
    "mock plan. When we add LLM routing, we’ll replace the mock with a real `tool_call` and reuse the same executor."
)
