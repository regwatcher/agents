"""Sequential recruitment workflow (Agents SDK): research → score → outreach → report."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv


class RecruitmentStatusEvent(TypedDict):
    kind: Literal["status"]
    message: str


class RecruitmentArtifactEvent(TypedDict):
    kind: Literal["artifact"]
    filename: str
    title: str
    markdown: str


class RecruitmentFinalReportEvent(TypedDict):
    kind: Literal["final_report"]
    markdown: str


RecruitmentStreamEvent = (
    RecruitmentStatusEvent | RecruitmentArtifactEvent | RecruitmentFinalReportEvent
)


def _status(message: str) -> RecruitmentStatusEvent:
    return {"kind": "status", "message": message}


def _artifact(filename: str, title: str, markdown: str) -> RecruitmentArtifactEvent:
    return {"kind": "artifact", "filename": filename, "title": title, "markdown": markdown}


def _final_report(markdown: str) -> RecruitmentFinalReportEvent:
    return {"kind": "final_report", "markdown": markdown}


_PLATFORM_TRACING_ENABLED = True


# def load_project_env() -> None:
#     base = Path(__file__).resolve().parent
#     load_dotenv(base / ".env", override=True)
#     load_dotenv(override=False)
#     base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
#     if base_url:
#         os.environ.setdefault("OPENAI_BASE_URL", base_url.rstrip("/"))
#     key = os.getenv("OPENAI_API_KEY")
#     if key is not None:
#         os.environ["OPENAI_API_KEY"] = key.strip()

def load_project_env(*, override_file: bool = False) -> None:
    base = Path(__file__).resolve().parent
    env_path = base / ".env"
    loaded_env = False
    if env_path.exists():
        load_dotenv(env_path, override=override_file)
        print(f"Loaded environment variables from {env_path}", file=sys.stderr)
        loaded_env = True
    else:
        print("No .env file found in local directory", file=sys.stderr)
    load_dotenv(override=False)
    base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
    if base_url:
        os.environ.setdefault("OPENAI_BASE_URL", base_url.rstrip("/"))
    key = os.getenv("OPENAI_API_KEY")
    if key is not None:
        os.environ["OPENAI_API_KEY"] = key.strip()


load_project_env(override_file=True)


from agents import RunConfig, Runner, gen_trace_id, set_default_openai_api, trace
from agents.tracing import set_tracing_disabled


def _configure_agents_sdk_for_env() -> None:
    """
    OpenAI-compatible hosts (Z.ai, Azure, local proxies) usually do not implement the
    Responses API; the SDK defaults to Responses. Also, trace export targets
    platform.openai.com and rejects non-OpenAI keys (noisy 401).
    """
    global _PLATFORM_TRACING_ENABLED

    raw_base = (
        os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or ""
    ).strip()

    truthy = {"1", "true", "yes", "on"}
    force_chat = (
        os.getenv("OPENAI_AGENTS_USE_CHAT_COMPLETIONS", "").lower().strip() in truthy
    )
    force_disable_trace = (
        os.getenv("OPENAI_AGENTS_DISABLE_TRACING", "").lower().strip() in truthy
    )

    non_openai_host = bool(
        raw_base and "api.openai.com" not in raw_base.lower()
    )

    if force_chat or non_openai_host:
        set_default_openai_api("chat_completions")

    if force_disable_trace or non_openai_host:
        set_tracing_disabled(True)
        _PLATFORM_TRACING_ENABLED = False


_configure_agents_sdk_for_env()


def _ensure_agents_tools_path() -> None:
    """Agents and tools live under ``agents-and-tools/`` (hyphenated folder name)."""
    sub = Path(__file__).resolve().parent / "agents-and-tools"
    if sub.is_dir():
        p = str(sub)
        if p not in sys.path:
            sys.path.insert(0, p)


_ensure_agents_tools_path()

from agent_activity_hooks import TerminalActivityHooks
from communicator_agent import OutreachPlan, communicator_agent
from matcher_agent import ScoredCandidates, matcher_agent
from model_env import target_candidate_count
from reporter_agent import RecruitmentReport, reporter_agent
from researcher_agent import CandidateList, researcher_agent


def _output_dir() -> Path:
    return Path(__file__).resolve().parent / "output"


def _write_output(name: str, content: str) -> Path:
    out = _output_dir()
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    path.write_text(content, encoding="utf-8")
    return path


def _run_config() -> RunConfig:
    """Honor ``OPENAI_MODEL_NAME`` at run time (Gradio can update env without reloading agents)."""
    model = (os.getenv("OPENAI_MODEL_NAME") or "gpt-4o").strip() or "gpt-4o"
    return RunConfig(model=model)


def _max_turns(tool_heavy: bool) -> int:
    """Agents SDK defaults to max_turns=10; Serper batches + scrape tools need more."""
    if tool_heavy:
        raw = os.getenv("RECRUITMENT_TOOL_MAX_TURNS", "").strip()
        return int(raw) if raw.isdigit() else 50
    raw = os.getenv("RECRUITMENT_MAX_TURNS", "").strip()
    return int(raw) if raw.isdigit() else 20


def _terminal_activity_hooks(phase_label: str) -> TerminalActivityHooks | None:
    """Live stderr lines for LLM turns and tool calls. Disable with RECRUITMENT_SILENT_AGENT_ACTIVITY=1."""
    v = os.getenv("RECRUITMENT_SILENT_AGENT_ACTIVITY", "").lower().strip()
    if v in {"1", "true", "yes", "on"}:
        return None
    return TerminalActivityHooks(phase_label)


class RecruitmentManager:
    async def run(self, job_requirements: str):
        """
        Yield stream events:
        - status: trace / phase lines
        - artifact: markdown for completed phase outputs (research … outreach)
        - final_report: executive report markdown
        """
        load_project_env(override_file=False)
        trace_id = gen_trace_id()
        with trace("Recruitment trace", trace_id=trace_id):
            if _PLATFORM_TRACING_ENABLED:
                url = (
                    "View trace: https://platform.openai.com/traces/trace?trace_id="
                    f"{trace_id}"
                )
                print(url)
                yield _status(url)
            else:
                msg = (
                    "(Platform tracing disabled — using a non-OpenAI-compatible host or "
                    "OPENAI_AGENTS_DISABLE_TRACING=1)"
                )
                yield _status(msg)
            print("Starting recruitment pipeline...")
            n_candidates = target_candidate_count()
            yield _status(
                f"Phase 1: researching candidates (Serper, web, LinkedIn; target {n_candidates})…"
            )
            research_input = (
                f"Job requirements:\n{job_requirements}\n\n"
                f"Target number of candidates to find and profile: {n_candidates}\n\n"
                "Complete the researcher task: find that many suitable candidates, using "
                "tools as needed, then produce markdown_candidates and structured output."
            )
            res = await Runner.run(
                researcher_agent,
                research_input,
                max_turns=_max_turns(tool_heavy=True),
                hooks=_terminal_activity_hooks("Phase 1 · Research"),
                run_config=_run_config(),
            )
            candidates = res.final_output_as(CandidateList)
            _write_output("candidates_list.md", candidates.markdown_candidates)
            yield _artifact(
                "candidates_list.md",
                "Phase 1 — Candidate research",
                candidates.markdown_candidates,
            )
            yield _status("research → output/candidates_list.md")

            yield _status("Phase 2: scoring candidates…")
            m_res = await Runner.run(
                matcher_agent,
                f"Enriched candidates (markdown):\n{candidates.markdown_candidates}\n\n"
                f"Structured:\n{candidates.model_dump_json(indent=2)}\n\n"
                f"Job requirements:\n{job_requirements}",
                max_turns=_max_turns(tool_heavy=True),
                hooks=_terminal_activity_hooks("Phase 2 · Match & score"),
                run_config=_run_config(),
            )
            scored = m_res.final_output_as(ScoredCandidates)
            _write_output("candidates_scores.md", scored.markdown_scores)
            yield _artifact(
                "candidates_scores.md",
                "Phase 2 — Scores & ranking",
                scored.markdown_scores,
            )
            yield _status("scores → output/candidates_scores.md")

            yield _status("Phase 3: outreach strategy…")
            c_res = await Runner.run(
                communicator_agent,
                f"Scores (markdown):\n{scored.markdown_scores}\n\n"
                f"Structured:\n{scored.model_dump_json(indent=2)}\n\n"
                f"Job requirements:\n{job_requirements}",
                max_turns=_max_turns(tool_heavy=True),
                hooks=_terminal_activity_hooks("Phase 3 · Outreach"),
                run_config=_run_config(),
            )
            outreach = c_res.final_output_as(OutreachPlan)
            _write_output("outreach_templates.md", outreach.markdown_outreach)
            yield _artifact(
                "outreach_templates.md",
                "Phase 3 — Outreach templates",
                outreach.markdown_outreach,
            )
            yield _status("outreach → output/outreach_templates.md")

            yield _status("Phase 4: executive report…")
            r_res = await Runner.run(
                reporter_agent,
                f"Candidates (markdown):\n{candidates.markdown_candidates}\n\n"
                f"Scores (markdown):\n{scored.markdown_scores}\n\n"
                f"Outreach (markdown):\n{outreach.markdown_outreach}\n\n"
                "Produce the final recruiter report (do not repeat the full job posting).",
                max_turns=_max_turns(tool_heavy=False),
                hooks=_terminal_activity_hooks("Phase 4 · Report"),
                run_config=_run_config(),
            )
            report = r_res.final_output_as(RecruitmentReport)
            _write_output("candidates_report.md", report.markdown_report)
            yield _status("report → output/candidates_report.md")
            yield _status("Done.")
            yield _final_report(report.markdown_report)
