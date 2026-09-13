#!/usr/bin/env python3
"""CLI for recruitment Agents SDK workflow."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from recruitment_manager import RecruitmentManager, load_project_env


DEFAULT_JOB_HINT = """\
No job description provided. From the repo root (`agents/`):

  uv run python 0_my_notes/recruitment_use_case/main.py --file path/to/job.md

See README.md."""


async def _run(requirements: str) -> None:
    load_project_env(override_file=False)
    mgr = RecruitmentManager()
    async for ev in mgr.run(requirements):
        if ev["kind"] == "status":
            print(ev["message"])
        elif ev["kind"] == "artifact":
            print(f"\n{'=' * 60}\n{ev['title']}  ({ev['filename']})\n{'=' * 60}\n")
            print(ev["markdown"])
        elif ev["kind"] == "final_report":
            print("\n--- Executive report (phase 4) ---\n")
            print(ev["markdown"])


def main() -> int:
    p = argparse.ArgumentParser(description="Recruitment pipeline (OpenAI Agents SDK).")
    p.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Markdown/text file containing job requirements",
    )
    args = p.parse_args()

    if args.file:
        text = args.file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        text = DEFAULT_JOB_HINT

    asyncio.run(_run(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
