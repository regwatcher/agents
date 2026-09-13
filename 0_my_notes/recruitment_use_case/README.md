# Recruitment (OpenAI Agents SDK)

Same pipeline as [`recruitment/`](./recruitment/) (CrewAI), implemented with the Agents SDK and flat scripts like [`2_openai/deep_research`](../../2_openai/deep_research/): **research (Serper + web + LinkedIn) → scoring → outreach → report**. Agent definitions and tools live in [`agents-and-tools/`](./agents-and-tools/). Markdown files land in [`output/`](./output/).

## Quick start (uv)

From **`agents/`** (repo root, where [`pyproject.toml`](../../pyproject.toml) lives):

```bash
cd agents
uv sync
uv run playwright install chromium    # once, for LinkedIn scraping
uv run python 0_my_notes/recruitment_use_case/recruitment_app.py   # UI
uv run python 0_my_notes/recruitment_use_case/main.py --file /path/to/job.md
```

If your cwd is **`agents/0_my_notes/`**, do not repeat `0_my_notes/` in the path:

```bash
uv run python recruitment_use_case/recruitment_app.py
```

## Configuration

Copy or edit **[`recruitment/.env`](./recruitment/.env)** (same file the app loads): `OPENAI_API_KEY`, `SERPER_API_KEY`, and LinkedIn auth (`LINKEDIN_COOKIE` or email/password). Optional: `OPENAI_API_BASE` / `OPENAI_BASE_URL`, `OPENAI_MODEL_NAME`, `LINKEDIN_HEADLESS=false`.

For **any base URL other than `api.openai.com`**, this project automatically switches the Agents SDK to **Chat Completions** (many compatible hosts omit the Responses API) and turns off uploads to OpenAI platform tracing—otherwise you often see harmless “invalid_api_key” errors when your key is only valid at Z.ai / Azure / etc.

If you still get **401 Authentication Failed** on model calls: the key or base URL does not match the provider (regenerate the key in the provider’s console, check for typos or expired keys, and ensure `OPENAI_MODEL_NAME` is a model that host actually serves).

Optional overrides in `.env`: `RECRUITMENT_TARGET_CANDIDATES` (default `10`, max `50`; researcher aims for this many profiles), `OPENAI_AGENTS_USE_CHAT_COMPLETIONS=true`, `OPENAI_AGENTS_DISABLE_TRACING=true`. If research or tool-heavy steps hit **Max turns exceeded**, raise `RECRUITMENT_TOOL_MAX_TURNS` (default 50); for the reporter phase use `RECRUITMENT_MAX_TURNS` (default 20).

## Outputs

While the UI runs, **Intermediate results** streams phases 1–3 as markdown; **Executive report** shows phase 4. The same content is saved under [`output/`](./output/):

| `output/` file | Contents |
|----------------|----------|
| `candidates_list.md` | Researched / scraped profiles |
| `candidates_scores.md` | Ranking / scores |
| `outreach_templates.md` | Copy for outreach |
| `candidates_report.md` | Executive summary |

## Note

Automating LinkedIn can conflict with their terms — see [`recruitment/README.md`](./recruitment/README.md).
