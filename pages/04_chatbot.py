# pages/06_planning_chat.py
import json
import streamlit as st

from llm_clients.router import route_to_tool, PLANNER_SYSTEM
from tools.specs import PLANNER_TOOL_SPECS
from tools.schema_catalog import get_planner_context

TABLE = "biwenger_player_stats"

st.set_page_config(page_title="Planning Chat (JSON + Summary)", page_icon="🧩", layout="wide")
st.title("Phase 4 — Planning Chat (plan JSON + English summary)")

# --- simple helpers -----------------------------------------------------------
def summarize_plan(plan: dict) -> str:
    """Deterministic English summary of the plan (no LLM)."""
    if not plan or "steps" not in plan:
        return "No plan produced."
    steps = plan.get("steps", [])
    why = plan.get("why", "")
    assumptions = plan.get("assumptions", [])
    lines = []
    if why:
        lines.append(f"**Intent:** {why}")
    lines.append("\n**Steps:**")
    for i, s in enumerate(steps, 1):
        tool = s.get("tool")
        args = s.get("args", {})
        if tool == "load_biwenger_player_stats":
            lines.append(f"{i}. Load Biwenger season snapshot (cached).")
        elif tool == "filter_df":
            fs = args.get("filters", [])
            if fs:
                descs = [f"{f['col']} {f['op']} {repr(f['val'])}" for f in fs]
                lines.append(f"{i}. Filter current DataFrame where " + "; ".join(descs) + ".")
            else:
                lines.append(f"{i}. Filter current DataFrame (no filters provided).")
        elif tool == "translate_to_pandas":
            q = args.get("query", "")
            lines.append(f"{i}. Generate pandas code for: {q!r} (no execution here).")
        else:
            lines.append(f"{i}. {tool} (args: {args})")
    if assumptions:
        lines.append("\n**Assumptions:**")
        for a in assumptions:
            lines.append(f"- {a}")
    return "\n".join(lines)

# --- session state ------------------------------------------------------------
if "plan_messages" not in st.session_state:
    st.session_state.plan_messages = [
        {"role": "assistant", "content": "Ask a data question (e.g., 'Real Madrid players in Oct 2025 …'). I’ll return a JSON plan and a short English summary."}
    ]

# replay history
for m in st.session_state.plan_messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- chat input ---------------------------------------------------------------
if user_text := st.chat_input("Ask a data question…"):
    st.session_state.plan_messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # plan with the LLM (function-call to make_plan), using schema as context
    try:
        schema_ctx = get_planner_context(TABLE)  # JSON string is fine for router context
        plan_call = route_to_tool(
            user_text,
            PLANNER_TOOL_SPECS,
            context=schema_ctx,
            force_tool_name="make_plan",
            system_override=PLANNER_SYSTEM,
        )
        plan = plan_call.args  # the validated arguments passed to make_plan

        # assistant message: English summary + expandable raw JSON
        with st.chat_message("assistant"):
            st.markdown(summarize_plan(plan))
            with st.expander("Plan (raw JSON)"):
                st.json(plan, expanded=True)

        st.session_state.plan_messages.append({"role": "assistant", "content": summarize_plan(plan)})

    except Exception as e:
        with st.chat_message("assistant"):
            st.error("Planning failed.")
            st.exception(e)
        st.session_state.plan_messages.append({"role": "assistant", "content": f"Planning failed: {e}"})
