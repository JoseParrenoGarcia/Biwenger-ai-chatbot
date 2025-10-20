# pages/03_planner_and_translator.py
import json
import streamlit as st

from llm_clients.router import route_to_tool, PLANNER_SYSTEM
from tools.specs import PLANNER_TOOL_SPECS
from tools.registry import execute_plan
from tools.schema_catalog import get_planner_context

st.set_page_config(page_title="EDA Chatbot — Planner + Pandas Translator", layout="wide")
st.title("Phase 3 — Planner (make_plan) + Pandas Code (translate_to_pandas)")

with st.container(border=True):
    st.subheader("LLM Planner")

    user_text = st.text_input(
        "Type a request (e.g., 'Real Madrid players in Oct 2025, show name/value/points sorted by value desc')",
        "Show Madrid players in Oct 2025 sorted by value desc; keep player_name,value,points."
    )

    table = "biwenger_player_stats"

    st.markdown("**Planner tool:** `MAKE_PLAN_SPEC` (allowed steps: load_biwenger_player_stats, filter_df, translate_to_pandas)")

    colA, colB = st.columns([1, 1])
    plan_clicked = colA.button("Plan with LLM", type="primary")
    run_clicked  = colB.button("Execute plan (non-destructive)")

    if "llm_plan" not in st.session_state:
        st.session_state.llm_plan = None
    if "last_outputs" not in st.session_state:
        st.session_state.last_outputs = []  # collect step-wise outputs

    # ---- PLAN ----
    if plan_clicked:
        try:
            with st.spinner("Planning…"):
                # get schema context for planner; tolerate JSON string or dict
                schema_ctx = get_planner_context(table)
                if isinstance(schema_ctx, str):
                    try:
                        schema_ctx = json.loads(schema_ctx)
                    except Exception:
                        pass  # if it's already a compact string, pass it through

                plan_call = route_to_tool(
                    user_text,
                    PLANNER_TOOL_SPECS,
                    context=schema_ctx,
                    force_tool_name="make_plan",
                    system_override=PLANNER_SYSTEM
                )
            plan = plan_call.args  # STRICT JSON plan (dict with steps, why, assumptions)
            st.session_state.llm_plan = plan
            st.session_state.last_outputs = []

            st.success("Planned ✔")
            with st.expander("Plan (JSON)"):
                st.json(st.session_state.llm_plan, expanded=True)

            # Quick plan summary
            steps = [s.get("tool") for s in plan.get("steps", [])]
            st.info(f"Planned steps: {steps}")

        except Exception as e:
            st.session_state.llm_plan = None
            st.session_state.last_outputs = []
            st.error("Planning failed.")
            st.exception(e)

    # ---- EXECUTE (no arbitrary code execution here) ----
    if run_clicked and st.session_state.llm_plan:
        plan = st.session_state.llm_plan

        with st.expander("Plan (JSON)"):
            st.json(plan, expanded=True)

        try:
            with st.spinner("Executing plan…"):
                # Your registry’s executor should chain steps in order.
                # It may return a DataFrame (deterministic path) or a dict with {"python_code": "..."} for translate_to_pandas.
                result = execute_plan(plan)  # expected to run: load_* -> (filter_df | translate_to_pandas)

            st.session_state.last_outputs.append(result)
            st.success("Plan executed ✔")

            # ---- Render outputs ----
            # Case A: deterministic path returns a DataFrame
            if hasattr(result, "head"):  # naive check for DataFrame-like
                row_count = getattr(result, "__len__", lambda: None)() or 0
                st.markdown(f"**Result (DataFrame):** {row_count} rows")
                st.dataframe(result, use_container_width=True, height=480)

            # Case B: translator path returns code dict
            elif isinstance(result, dict) and "python_code" in result:
                st.markdown("**Result (pandas code from translate_to_pandas):**")
                st.code(result["python_code"], language="python")
                st.caption("This is code only; not executed here.")

            else:
                st.warning("Executor returned an unexpected type. Check the registry's return values.")
                st.write(result)

        except Exception as e:
            st.error("Execution failed.")
            st.exception(e)

with st.expander("Debug: last outputs"):
    st.write(st.session_state.last_outputs)

st.caption(
    "This page uses the LLM planner to propose steps and then executes them via the registry. "
    "If the plan uses 'translate_to_pandas', the page shows the generated pandas code (without executing it)."
)
