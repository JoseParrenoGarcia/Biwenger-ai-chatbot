from __future__ import annotations
import json, re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

# 1) Return type
class ToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5

# 2) Tiny prompt bits
ROUTER_SYSTEM = (
    "You are a tool router. Choose exactly one tool from the provided list and output STRICT JSON "
    'as {"tool_name": "...", "args": {...}, "confidence": 0..1}. Do not add prose.'
)

# 3) Robust JSON extraction
_FENCED = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    m = _FENCED.search(text)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    try:
        return json.loads(text)
    except:
        # last resort: first {...}
        start = text.find("{")
        if start == -1: return None
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try: return json.loads(text[start:i+1])
                    except: return None
    return None

# 4) The router: returns a plan or raises
def route_to_tool(
    user_text: str,
    tool_specs: List[dict],
    *,
    model: str = "gpt-4o-mini",
    client: Optional[OpenAI] = None,
) -> ToolCall:
    """
    Ask the model to select a single tool and arguments.
    Returns a ToolCall. Does NOT execute the tool. Does NOT have a fallback.
    Raises ValueError if no valid plan is returned.
    """
    if not tool_specs:
        raise ValueError("No tools provided to router.")
    if not user_text or not user_text.strip():
        raise ValueError("Empty user_text.")

    client = client or OpenAI()

    # Keep the prompt short; your tool specs carry the meaning.
    user_prompt = f'User: "{user_text}"\nRespond with STRICT JSON only.'

    resp = client.responses.create(
        model=model,
        input=[{"role": "system", "content": ROUTER_SYSTEM},
               {"role": "user",   "content": user_prompt}],
        tools=tool_specs,
    )

    # Prefer structured tool_call blocks if the model returns them
    try:
        for item in resp.output:
            if getattr(item, "type", None) == "tool_call":
                fn = item.tool_call.function
                data = {
                    "tool_name": fn.name,
                    "args": json.loads(fn.arguments or "{}"),
                    "confidence": 0.75  # conservative default if not provided
                }
                return ToolCall(**data)
    except Exception:
        pass

    # Otherwise parse text
    data = _extract_json(resp.output_text or "")
    if not data:
        raise ValueError("Router returned no parsable plan.")

    try:
        return ToolCall(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid plan structure: {e}")
