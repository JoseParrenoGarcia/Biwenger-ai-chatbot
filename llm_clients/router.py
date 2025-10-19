# llm_clients/router.py
from __future__ import annotations
import json, re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

from llm_clients.openai_client import get_openai_client, get_default_model

class ToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    why: str = ""
    assumptions: List[str] = Field(default_factory=list)

_FENCED = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text: return None
    m = _FENCED.search(text)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    try: return json.loads(text)
    except: return None

def _to_chat_tools(tool_specs: List[dict]) -> List[dict]:
    out = []
    for t in tool_specs:
        if t.get("type") != "function":
            raise ValueError("Only function tools are supported.")
        if "function" in t:
            out.append(t)
        else:
            out.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {"type":"object","properties":{},"additionalProperties":False})
                }
            })
    return out

# NEW: a planner-specific system prompt (kept here for convenience)
PLANNER_SYSTEM = (
    "You are a planner. You must call the function 'make_plan' with arguments that follow its JSON schema. "
    "Use the provided CONTEXT_SCHEMA if present. "
    "Return a plan object with keys: steps, why, assumptions. "
    "Do NOT print free-form JSON or any content outside the function call. "
    "Do NOT return top-level 'filters'. Use the exact key 'args' for step arguments."
)

def route_to_tool(
    user_text: str,
    tool_specs: List[dict],
    *,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
    context: Optional[str] = None,           # <-- NEW
    force_tool_name: Optional[str] = None,   # <-- NEW
    system_override: Optional[str] = None,   # <-- NEW
) -> ToolCall:
    """
    Single-shot router. Returns a ToolCall; does NOT execute the tool.
    Raises ValueError if the model doesn't produce a valid plan.
    """
    if not user_text.strip():
        raise ValueError("Empty user_text.")
    if not tool_specs:
        raise ValueError("No tool specs provided.")

    client = client or get_openai_client()
    model = model or get_default_model()
    tools = _to_chat_tools(tool_specs)

    # Default router system (kept for non-planning use)
    ROUTER_SYSTEM = (
        "You are a tool router. Choose exactly one function from the provided tools and "
        "output STRICT JSON with keys:\n"
        '  - \"tool_name\": string\n'
        '  - \"args\": object\n'
        '  - \"confidence\": number (0..1)\n'
        '  - \"why\": short string (<=120 chars)\n'
        '  - \"assumptions\": array of 0-3 short strings\n'
        "No prose or explanations outside the JSON. Do NOT include chain-of-thought."
    )

    sys_prompt = system_override or ROUTER_SYSTEM

    messages = [{"role": "system", "content": sys_prompt}]
    if context:
        messages.append({"role": "system", "content": f"CONTEXT_SCHEMA:\n{context}"})
    messages.append({"role": "user", "content": f'User: "{user_text}"'})

    # Enforce the function call when requested (e.g., for planning)
    tool_choice = "auto"
    if force_tool_name:
        tool_choice = {"type": "function", "function": {"name": force_tool_name}}

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
    )

    msg = resp.choices[0].message

    # Preferred: function call
    if msg.tool_calls:
        tc = msg.tool_calls[0]
        data = {
            "tool_name": tc.function.name,
            "args": json.loads(tc.function.arguments or "{}"),
            "confidence": 0.75,
        }
        return ToolCall(**data)

    # Fallback: parse raw JSON (rare for planning, but keep it)
    data = _extract_json(msg.content or "")
    if not data:
        raise ValueError("Router returned no tool_call and no parsable JSON plan.")
    try:
        return ToolCall(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid plan structure: {e}")
