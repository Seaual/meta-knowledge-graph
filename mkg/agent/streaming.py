"""Convert DeepAgents stream chunks to frontend SSE events."""

from typing import Any


def convert_chunk_to_sse(chunk: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a DeepAgents v2 stream chunk to an SSE event.

    Returns None for unhandled chunk types.
    """
    chunk_type = chunk.get("type")
    ns = chunk.get("ns", ())

    if chunk_type == "updates":
        data = chunk.get("data", {})
        node = ""
        if "__meta__" in data and isinstance(data["__meta__"], dict):
            node = data["__meta__"].get("node", "")

        # Check for todo/planning steps
        if "todos" in data:
            return {
                "type": "todo",
                "todos": data["todos"],
            }

        # Tool call start
        if node == "tools" and "messages" in data:
            msgs = data["messages"]
            if msgs and hasattr(msgs[-1], "tool_calls") and msgs[-1].tool_calls:
                tc = msgs[-1].tool_calls[0]
                return {
                    "type": "tool_call",
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                    "ns": ns,
                }

        # Tool result
        if node == "tools" and "messages" in data:
            msgs = data["messages"]
            if msgs and hasattr(msgs[-1], "type") and msgs[-1].type == "tool":
                return {
                    "type": "tool_result",
                    "name": msgs[-1].name,
                    "result": str(msgs[-1].content)[:500],
                    "ns": ns,
                }

        # Subagent start/end
        if any(isinstance(s, str) and s.startswith("tools:") for s in ns):
            if "messages" in data and data["messages"]:
                msg = data["messages"][-1]
                if hasattr(msg, "type") and msg.type == "ai":
                    return {
                        "type": "subagent_start",
                        "name": next((s for s in ns if isinstance(s, str) and s.startswith("tools:")), ""),
                        "task": msg.content[:200] if hasattr(msg, "content") else "",
                    }

        return None

    if chunk_type == "messages":
        token, _meta = chunk.get("data", (None, None))
        if token and hasattr(token, "content") and token.content:
            return {
                "type": "token",
                "content": token.content,
                "ns": ns,
            }
        return None

    if chunk_type == "custom":
        return {
            "type": "progress",
            "data": chunk.get("data", {}),
        }

    return None
