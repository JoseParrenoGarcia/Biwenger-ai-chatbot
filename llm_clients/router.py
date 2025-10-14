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
    """
    Accepts specs like {"type":"function","function":{...}} (preferred)
    or flat {"type":"function","name":...} and returns nested chat-compatible form.
    """
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

def route_to_tool(
    user_text: str,
    tool_specs: List[dict],
    *,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
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

    messages = [
        {"role": "system",
         "content": (
            "You are a tool router. Choose exactly one function from the provided tools and "
            'output STRICT JSON: {"tool_name":"...","args":{...},"confidence":0..1}. '
            "Do not add prose."
         )},
        {"role": "user", "content": f'User: "{user_text}"\nRespond with STRICT JSON only.'}
    ]

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    msg = resp.choices[0].message

    # Preferred: model emits a tool call directly
    if msg.tool_calls:
        tc = msg.tool_calls[0]
        data = {
            "tool_name": tc.function.name,
            "args": json.loads(tc.function.arguments or "{}"),
            "confidence": 0.75,  # default if model didn't include one
        }
        return ToolCall(**data)

    # Else parse raw JSON plan text, if the model printed it
    data = _extract_json(msg.content or "")
    if not data:
        raise ValueError("Router returned no tool_call and no parsable JSON plan.")
    try:
        return ToolCall(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid plan structure: {e}")
