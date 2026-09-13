"""Print agent lifecycle events to stderr (tools, LLM turns, agent switches)."""

from __future__ import annotations

import sys
from typing import Any, Optional

from agents import Agent, RunHooks
from agents.items import ItemHelpers, ModelResponse, TResponseInputItem
from agents.run_context import RunContextWrapper
from agents.tool import Tool
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage


def _ellipsis(text: str, limit: int) -> str:
    t = text.replace("\n", " ").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 1] + "…"


def _as_preview(obj: Any, limit: int) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return _ellipsis(obj, limit)
    try:
        return _ellipsis(str(obj), limit)
    except Exception:
        return "(unpreviewable)"


def _last_turn_preview(input_items: list[TResponseInputItem], limit: int = 200) -> str:
    if not input_items:
        return "∅"
    last: Any = input_items[-1]
    try:
        if isinstance(last, dict):
            role = last.get("role", "?")
            content = last.get("content")
            if isinstance(content, str):
                return f"[{role}] {_ellipsis(content, limit)}"
            if isinstance(content, list):
                return f"[{role}] (multipart content)"
            return f"[{role}] {_as_preview(content, limit)}"
        # OpenAI SDK Param objects often support model_dump
        if hasattr(last, "model_dump"):
            d = last.model_dump(exclude_unset=True)
            role = d.get("role", "?")
            content = d.get("content")
            if isinstance(content, str):
                return f"[{role}] {_ellipsis(content, limit)}"
            return f"[{role}] {_as_preview(content, limit)}"
    except Exception:
        pass
    return _as_preview(last, limit)


class TerminalActivityHooks(RunHooks):
    """Hooks passed to ``Runner.run(..., hooks=...)`` for readable terminal progress."""

    def __init__(self, phase_label: str, *, stream=sys.stderr) -> None:
        super().__init__()
        self._phase = phase_label
        self._stream = stream
        self._llm_calls = 0

    def _line(self, msg: str) -> None:
        print(msg, file=self._stream, flush=True)

    async def on_agent_start(
        self, context: RunContextWrapper[Any], agent: Agent[Any]
    ) -> None:
        self._llm_calls = 0
        self._line(f"[{self._phase}] ▶ agent: {agent.name}")

    async def on_llm_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        system_prompt: Optional[str],
        input_items: list[TResponseInputItem],
    ) -> None:
        self._llm_calls += 1
        tail = _last_turn_preview(input_items, limit=220)
        self._line(
            f"[{self._phase}] {agent.name}: LLM request #{self._llm_calls} "
            f"({len(input_items)} items) → context tail: {tail}"
        )

    async def on_tool_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
    ) -> None:
        raw_args = getattr(context, "tool_arguments", None)
        args_preview = _as_preview(raw_args, 280)
        self._line(
            f"[{self._phase}] {agent.name}: tool → {tool.name} "
            f"(args): {args_preview}"
        )

    async def on_tool_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
        result: str,
    ) -> None:
        body = str(result) if result is not None else ""
        n = len(body)
        self._line(
            f"[{self._phase}] {agent.name}: tool ← {tool.name} "
            f"({n} chars): {_ellipsis(body, 320)}"
        )

    async def on_llm_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        response: ModelResponse,
    ) -> None:
        parts: list[str] = []
        for item in response.output:
            if isinstance(item, ResponseFunctionToolCall):
                parts.append(
                    f"call {item.name}({_as_preview(item.arguments, 120)})"
                )
            elif isinstance(item, ResponseOutputMessage):
                txt = ItemHelpers.extract_last_text(item)
                if txt:
                    parts.append(f"text {_as_preview(txt, 220)}")
        summary = " | ".join(parts) if parts else "(no structured output)"
        u = response.usage
        tok = f" in={getattr(u, 'input_tokens', '?')} out={getattr(u, 'output_tokens', '?')}"
        self._line(f"[{self._phase}] {agent.name}: LLM reply ← {summary}{tok}")
