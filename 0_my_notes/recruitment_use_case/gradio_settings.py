"""Gradio settings: apply env overrides, optional .env merge, credential smoke tests."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_AGENTS_TOOLS_DIR = Path(__file__).resolve().parent / "agents-and-tools"
if _AGENTS_TOOLS_DIR.is_dir() and str(_AGENTS_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_TOOLS_DIR))

import requests
from dotenv import load_dotenv
from openai import OpenAI


def recruitment_env_path() -> Path:
    return Path(__file__).resolve().parent / ".env"


def effective_model_name() -> str:
    return (os.getenv("OPENAI_MODEL_NAME") or "gpt-4o").strip() or "gpt-4o"


def effective_openai_base_url() -> str:
    return (
        os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or ""
    ).strip().rstrip("/")


def secret_status(set_var: str) -> str:
    v = (os.getenv(set_var) or "").strip()
    return "configured" if v else "not set"


def settings_summary_md() -> str:
    return (
        "**Environment (session)**\n\n"
        f"- **Model:** `{effective_model_name()}`\n"
        f"- **OpenAI base URL:** `{effective_openai_base_url() or '(default api.openai.com)'}`\n"
        f"- **OPENAI_API_KEY:** _{secret_status('OPENAI_API_KEY')}_\n"
        f"- **SERPER_API_KEY:** _{secret_status('SERPER_API_KEY')}_\n"
        f"- **LINKEDIN_COOKIE:** _{secret_status('LINKEDIN_COOKIE')}_\n"
        f"- **LINKEDIN_EMAIL:** _{secret_status('LINKEDIN_EMAIL')}_ / "
        f"**PASSWORD:** _{secret_status('LINKEDIN_PASSWORD')}_\n"
    )


def apply_to_environ(
    model: str,
    base_url: str,
    openai_key: str,
    serper_key: str,
    li_cookie: str,
    li_email: str,
    li_password: str,
) -> str:
    """Update ``os.environ`` from UI. Empty secret fields leave existing values unchanged."""
    if (model or "").strip():
        os.environ["OPENAI_MODEL_NAME"] = model.strip()

    bu = (base_url or "").strip().rstrip("/")
    if bu:
        os.environ["OPENAI_BASE_URL"] = bu
        os.environ.pop("OPENAI_API_BASE", None)
    # Do not clear base URL if field empty — avoids wiping on partial apply

    if (openai_key or "").strip():
        os.environ["OPENAI_API_KEY"] = openai_key.strip()

    if (serper_key or "").strip():
        os.environ["SERPER_API_KEY"] = serper_key.strip()

    if (li_cookie or "").strip():
        os.environ["LINKEDIN_COOKIE"] = li_cookie.strip()

    if (li_email or "").strip():
        os.environ["LINKEDIN_EMAIL"] = li_email.strip()

    if (li_password or "").strip():
        os.environ["LINKEDIN_PASSWORD"] = li_password.strip()

    key = os.getenv("OPENAI_API_KEY")
    if key is not None:
        os.environ["OPENAI_API_KEY"] = key.strip()

    return "Applied to this Python session. Pipeline runs use these values."


def _fmt_dotenv_line(key: str, val: str) -> str:
    if any(ch in val for ch in '\n\r#"\'') or " " in val:
        esc = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'{key}="{esc}"'
    return f"{key}={val}"


def save_to_dotenv(
    model: str,
    base_url: str,
    openai_key: str,
    serper_key: str,
    li_cookie: str,
    li_email: str,
    li_password: str,
) -> str:
    """Persist non-empty fields to ``recruitment_use_case/.env`` (merge; does not delete keys)."""
    path = recruitment_env_path()
    apply_to_environ(
        model,
        base_url,
        openai_key,
        serper_key,
        li_cookie,
        li_email,
        li_password,
    )
    updates: dict[str, str] = {}
    if (model or "").strip():
        updates["OPENAI_MODEL_NAME"] = model.strip()
    if (base_url or "").strip():
        updates["OPENAI_BASE_URL"] = base_url.strip().rstrip("/")
    if (openai_key or "").strip():
        updates["OPENAI_API_KEY"] = openai_key.strip()
    if (serper_key or "").strip():
        updates["SERPER_API_KEY"] = serper_key.strip()
    if (li_cookie or "").strip():
        updates["LINKEDIN_COOKIE"] = li_cookie.strip()
    if (li_email or "").strip():
        updates["LINKEDIN_EMAIL"] = li_email.strip()
    if (li_password or "").strip():
        updates["LINKEDIN_PASSWORD"] = li_password.strip()

    if not updates:
        return "Nothing to save (all secret fields were empty)."

    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    keys_written: set[str] = set()
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            out.append(line)
            continue
        if "=" in line:
            k = line.split("=", 1)[0].strip()
            if k in updates:
                out.append(_fmt_dotenv_line(k, updates[k]))
                keys_written.add(k)
            else:
                out.append(line)
        else:
            out.append(line)

    for k, v in updates.items():
        if k not in keys_written:
            out.append(_fmt_dotenv_line(k, v))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    load_dotenv(path, override=True)
    key = os.getenv("OPENAI_API_KEY")
    if key is not None:
        os.environ["OPENAI_API_KEY"] = key.strip()
    base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
    if base_url:
        os.environ.setdefault("OPENAI_BASE_URL", base_url.rstrip("/"))
    return f"Saved keys to `{path}` and reloaded."


def test_openai(
    model: str,
    base_url: str,
    api_key: str,
) -> str:
    """Minimal chat completion to verify API key + base URL + model id."""
    key = (api_key or "").strip() or (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return "Error: no API key (enter one or apply from .env first)."
    m = (model or "").strip() or effective_model_name()
    bu = (base_url or "").strip().rstrip("/") or effective_openai_base_url() or None
    try:
        client = OpenAI(api_key=key, base_url=bu) if bu else OpenAI(api_key=key)
        r = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=8,
        )
        txt = (r.choices[0].message.content or "").strip()
        return f"OK — chat completion succeeded. Snippet: {txt!r} (model={m})"
    except Exception as e:
        return f"Error: {e!s}"


def test_serper(api_key: str) -> str:
    key = (api_key or "").strip() or (os.getenv("SERPER_API_KEY") or "").strip()
    if not key:
        return "Error: no Serper API key."
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": key,
                "Content-Type": "application/json",
            },
            json={"q": "OpenAI", "num": 1},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            organic = data.get("organic") or []
            if organic:
                return f"OK — Serper returned results (e.g. {organic[0].get('title', '')[:60]}…)."
            return "OK — HTTP 200 but no organic results (quota/format?)."
        return f"Error HTTP {r.status_code}: {r.text[:400]}"
    except Exception as e:
        return f"Error: {e!s}"


async def test_linkedin(
    cookie: str,
    email: str,
    password: str,
) -> str:
    """Open Playwright briefly and run the same auth path as profile scraping."""
    from linkedin_auth import authenticate_linkedin_page, linkedin_chromium_launch_options
    from linkedin_scraper import AuthenticationError, BrowserManager

    ck = (cookie or "").strip()
    em = (email or "").strip()
    pw = (password or "").strip()

    saved: dict[str, str | None] = {}
    for k in (
        "LINKEDIN_COOKIE",
        "LINKEDIN_EMAIL",
        "LINKEDIN_PASSWORD",
        "LINKEDIN_USERNAME",
    ):
        saved[k] = os.environ.get(k)

    try:
        if ck:
            os.environ["LINKEDIN_COOKIE"] = ck
            os.environ.pop("LINKEDIN_EMAIL", None)
            os.environ.pop("LINKEDIN_PASSWORD", None)
            os.environ.pop("LINKEDIN_USERNAME", None)
        elif em and pw:
            os.environ["LINKEDIN_EMAIL"] = em
            os.environ["LINKEDIN_PASSWORD"] = pw
            os.environ.pop("LINKEDIN_COOKIE", None)
        else:
            return "Error: set **LinkedIn cookie** OR **email + password** for the test."

        headless = os.getenv("LINKEDIN_HEADLESS", "true").lower().strip() in (
            "1",
            "true",
            "yes",
            "on",
        )
        async with BrowserManager(
            headless=headless,
            **linkedin_chromium_launch_options(),
        ) as browser:
            await authenticate_linkedin_page(browser.page)
        return "OK — LinkedIn authentication succeeded (session usable for scraping)."
    except AuthenticationError as e:
        return f"Auth failed: {e!s}"
    except Exception as e:
        return f"Error: {e!s}"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def run_linkedin_test_sync(
    cookie: str,
    email: str,
    password: str,
) -> str:
    return asyncio.run(test_linkedin(cookie, email, password))
