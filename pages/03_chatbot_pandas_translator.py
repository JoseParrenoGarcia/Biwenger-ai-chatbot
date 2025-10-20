# pages/02_translate_to_pandas.py
import streamlit as st

from tools.english_to_pandas import EnglishToPandas
from tools.schema_catalog import get_planner_context  # returns your registry entry for a table
from llm_clients.openai_client import get_openai_client, get_default_model
import json

st.set_page_config(page_title="EDA Chatbot — Phase 3", layout="wide")
st.title("Phase 3 — Translate NL → pandas (no execution)")

with st.container(border=True):
    st.subheader("Translator")

    # Input
    user_text = st.text_input(
        "Type a request (e.g., 'Real Madrid in Oct 2025 sorted by value desc; keep player_name,value,points')",
        "Show Madrid players in Oct 2025 sorted by value desc; keep player_name,value,points."
    )

    colA, colB = st.columns([1, 1])
    gen_clicked = colA.button("Generate pandas code", type="primary")
    clear_clicked = colB.button("Clear")

    if "py_code" not in st.session_state:
        st.session_state.py_code = None

    if clear_clicked:
        st.session_state.py_code = None

    if gen_clicked:
        try:
            with st.spinner("Generating code…"):
                # 1) Get schema spec in your registry format (columns[], rules.date_column, value_hints)
                schema_spec_raw = get_planner_context("biwenger_player_stats")  # already exists in your Phase 2 code
                schema_spec = json.loads(schema_spec_raw)

                # 2) Init LLM + translator
                llm = get_openai_client()  # must expose .complete(prompt: str) -> str
                translator = EnglishToPandas()

                # 3) Ask LLM to emit a single pandas snippet (df_in -> df_out)
                code_str = translator.generate_code(
                    user_query=user_text,
                    schema_spec=schema_spec,
                )
                st.session_state.py_code = code_str

            st.success("Pandas code generated ✔")
        except Exception as e:
            st.session_state.py_code = None
            st.error("Translation failed.")
            st.exception(e)

    # Display result (code only; no execution yet)
    if st.session_state.py_code:
        with st.expander("Generated pandas code (read-only)"):
            st.code(st.session_state.py_code, language="python")

st.caption("This page asks the LLM to translate your request into a pandas snippet. It assumes df_in already exists (loaded elsewhere). Execution will come next.")
