import streamlit as st

from llm_clients.router import route_to_tool
from tools.specs import PLANNER_TOOL_SPECS
from tools.registry import execute_plan
from tools.schema_catalog import get_planner_context

st.set_page_config(page_title="EDA Chatbot — Plan Only", layout="wide")
st.title("Phase 2 (minimal) — Plan Only")

with st.container(border=True):
    st.subheader("LLM Planner")

    user_text = st.text_input(
        "Type a request (e.g., 'Real Madrid players since 2025-09-01')",
        "Show me data about Mbappe in 2025"
    )

    st.markdown("**LLM-visible tools:** `PLANNER_TOOL_SPECS = [MAKE_PLAN_SPEC]`")

    colA, colB= st.columns([1, 1])
    plan_clicked = colA.button("Plan with LLM", type="primary")
    run_clicked  = colB.button("Execute plan")

    if "llm_plan" not in st.session_state:
        st.session_state.llm_plan = None

    # PLAN
    if plan_clicked:
        try:
            with st.spinner("Planning…"):
                schema_json = get_planner_context("biwenger_player_stats")
                plan_call = route_to_tool(user_text, PLANNER_TOOL_SPECS, context=schema_json)  # ToolCall for make_plan
            plan = plan_call.args  # STRICT JSON plan (dict with steps, why, assumptions)
            st.session_state.llm_plan = plan

            st.success("Planned ✔")
            with st.expander("Plan (JSON)"):
                st.json(st.session_state.llm_plan)

        except Exception as e:
            st.session_state.llm_plan = None
            st.error("Planning failed.")
            st.exception(e)

    # EXECUTE
    if run_clicked and st.session_state.llm_plan:
        plan = st.session_state.llm_plan
        with st.expander("Plan (JSON)"):
            st.json(plan)
        for step in plan.get("steps", []):
            if step.get("tool") == "filter_df":
                filters = (step.get("args") or {}).get("filters")
                if not filters:
                    st.error("Plan has a 'filter_df' step without 'filters'. Please re-run planning.")
                    st.stop()

        try:
            with st.spinner("Executing plan…"):
                df = execute_plan(plan)  # your registry’s executor chains load -> filter_df
            st.success(f"Executed plan → {len(df)} rows")
            st.dataframe(df, use_container_width=True, height=480)
        except Exception as e:
            st.error("Execution failed.")
            st.exception(e)

st.caption("This page runs the LLM plan through the deterministic pandas executor.")
