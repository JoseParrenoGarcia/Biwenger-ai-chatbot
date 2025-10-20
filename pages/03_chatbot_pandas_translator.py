# pages/04_planner_translate_execute.py
import json
import re
import pandas as pd
import streamlit as st

from llm_clients.router import route_to_tool, PLANNER_SYSTEM
from tools.specs import PLANNER_TOOL_SPECS
from tools.registry import execute_plan, execute_tool  # <-- NEW: we'll call load_* directly for df_in
from tools.schema_catalog import get_planner_context

TABLE = "biwenger_player_stats"

st.set_page_config(page_title="EDA Chatbot — Plan + Translate + Execute", layout="wide")
st.title("Phase 3 — Plan → Pandas code → Execute (MVP)")

with st.container(border=True):
    st.subheader("1) Plan with the LLM")

    user_text = st.text_input(
        "Type a request",
        "Real Madrid players in Oct 2025, return player_name, value, points; sort by value desc"
    )

    colA, colB = st.columns([1, 1])
    plan_clicked = colA.button("Plan with LLM", type="primary")
    exec_plan_clicked = colB.button("Execute plan (show DF or code)")

    # Session state
    if "llm_plan" not in st.session_state:
        st.session_state.llm_plan = None
    if "python_code" not in st.session_state:
        st.session_state.python_code = None
    if "df_in" not in st.session_state:
        st.session_state.df_in = None
    if "df_out" not in st.session_state:
        st.session_state.df_out = None

    # ---- PLAN ----
    if plan_clicked:
        try:
            with st.spinner("Planning…"):
                schema_ctx = get_planner_context(TABLE)
                # Some implementations return a JSON string; normalize to dict if so.
                if isinstance(schema_ctx, str):
                    try:
                        schema_ctx = json.loads(schema_ctx)
                    except Exception:
                        pass

                plan_call = route_to_tool(
                    user_text,
                    PLANNER_TOOL_SPECS,
                    context=schema_ctx,
                    force_tool_name="make_plan",
                    system_override=PLANNER_SYSTEM
                )
            st.session_state.llm_plan = plan_call.args
            st.session_state.python_code = None
            st.session_state.df_in = None
            st.session_state.df_out = None
            st.success("Planned ✔")

            with st.expander("Plan (JSON)"):
                st.json(st.session_state.llm_plan, expanded=True)

            steps = [s.get("tool") for s in st.session_state.llm_plan.get("steps", [])]
            st.info(f"Planned steps: {steps}")

        except Exception as e:
            st.session_state.llm_plan = None
            st.error("Planning failed.")
            st.exception(e)

    # ---- EXECUTE PLAN (non-destructive) ----
    if exec_plan_clicked and st.session_state.llm_plan:
        try:
            with st.spinner("Executing plan…"):
                result = execute_plan(st.session_state.llm_plan)

            st.success("Plan executed ✔")

            # Case A: deterministic path returned a DataFrame
            if hasattr(result, "head"):
                st.session_state.df_out = result
                st.session_state.python_code = None

                st.markdown("**Result (deterministic DataFrame):**")
                st.dataframe(result, use_container_width=True, height=480)
                st.caption(f"{len(result)} rows × {result.shape[1]} cols")

            # Case B: translator path returned a code dict
            elif isinstance(result, dict) and "python_code" in result:
                st.session_state.python_code = result["python_code"]
                st.session_state.df_out = None  # reset

                st.markdown("**Result (pandas code from `translate_to_pandas`):**")
                st.code(st.session_state.python_code, language="python")
                st.caption("This is code only; not executed yet.")

                # NEW: preload df_in so we can run code locally after translation
                st.session_state.df_in = execute_tool("load_biwenger_player_stats", {})
                st.info(f"Loaded df_in for execution: {len(st.session_state.df_in)} rows")

            else:
                st.warning("Executor returned an unexpected type.")
                st.write(result)

        except Exception as e:
            st.error("Execution failed.")
            st.exception(e)

with st.container(border=True):
    st.subheader("2) Run generated pandas code locally (Option 1: simple exec)")

    run_clicked = st.button("Run code against df_in", type="primary", disabled=st.session_state.python_code is None)

    # --- Lightweight, explicit execution path (Option 1) ---
    if run_clicked:
        if st.session_state.python_code is None:
            st.error("No pandas code to execute. Plan and execute first.")
            st.stop()
        if st.session_state.df_in is None:
            st.error("No df_in loaded. Ensure the plan includes a load step or load it manually.")
            st.stop()

        code_str = st.session_state.python_code
        df_in = st.session_state.df_in

        # 2.1 (Optional) strip triple fences
        if code_str.startswith("```"):
            first_nl = code_str.find("\n")
            code_str = code_str[first_nl + 1:] if first_nl != -1 else code_str
            if code_str.endswith("```"):
                code_str = code_str[:-3]
            code_str = code_str.strip()

        # 2.2 (Optional) ultra-thin guardrails (still Option 1)
        # Length caps
        if len(code_str) > 4000 or code_str.count("\n") > 80:
            st.error("Code too long. Refuse to execute.")
            st.stop()
        # Crude bans (no imports beyond pandas, no I/O hints)
        forbidden = ["import ", "__import__", "open(", "to_sql", "read_", "os.", "sys.", "subprocess", "socket", "requests"]
        if any(tok in code_str for tok in forbidden):
            st.error("Code contains forbidden operations. Refusing to execute.")
            st.stop()

        # Optional: quick schema check (regex) — ensures only known columns are referenced
        try:
            schema_spec = get_planner_context(TABLE)
            if isinstance(schema_spec, str):
                schema_spec = json.loads(schema_spec)
            known_cols = {c["name"] for c in (schema_spec.get("columns") or [])}
            refs = set(re.findall(r"df\[['\"]([^'\"]+)['\"]\]", code_str))
            unknown = [c for c in refs if c not in known_cols]
            if unknown:
                st.warning(f"Code references unknown columns: {unknown} — execution may fail.")
        except Exception:
            pass  # keep going; this is only a hint

        # 2.3 Execute with minimal namespace
        try:
            globals_ns = {"pd": pd}       # only pandas in globals
            locals_ns = {"df_in": df_in}  # df_in is provided here

            with st.spinner("Running code…"):
                exec(code_str, globals_ns, locals_ns)

            df_out = locals_ns.get("df_out")
            if df_out is None:
                st.error("Execution produced no 'df_out'.")
                st.stop()

            st.session_state.df_out = df_out
            st.success("Code executed ✔")

            st.dataframe(df_out, use_container_width=True, height=480)
            st.caption(f"{len(df_out)} rows × {df_out.shape[1]} cols")

        except Exception as e:
            st.error("Code execution failed.")
            st.exception(e)

with st.expander("Debug / session state"):
    st.write({
        "has_plan": st.session_state.llm_plan is not None,
        "has_python_code": st.session_state.python_code is not None,
        "df_in_rows": (len(st.session_state.df_in) if st.session_state.df_in is not None else None),
        "df_out_rows": (len(st.session_state.df_out) if st.session_state.df_out is not None else None),
    })

st.caption(
    "This page: (1) plans with the LLM, (2) executes via registry to get either a DataFrame or pandas code, "
    "and (3) runs the code locally with a minimal exec (Option 1). "
    "When ready, you can harden this by adding timeouts, a subprocess sandbox, or AST allowlisting."
)
