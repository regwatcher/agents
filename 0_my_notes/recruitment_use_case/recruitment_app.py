"""Gradio UI for the recruitment Agents SDK workflow."""

from __future__ import annotations

import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from recruitment_manager import RecruitmentManager, load_project_env

import gradio_settings
from pdf_job_description import pdf_to_markdown


def _prep_env() -> None:
    load_project_env(override_file=False)
    load_dotenv(override=False)


_prep_env()

JOB_DESCRIPTIONS_DIR = Path(__file__).resolve().parent / "job-descriptions"


def list_job_description_files() -> list[str]:
    JOB_DESCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(p.name for p in JOB_DESCRIPTIONS_DIR.glob("*.md"))


def safe_job_filename(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        raise ValueError("Enter a file name.")
    base = Path(raw).name
    if not base or base in {".", ".."}:
        raise ValueError("Invalid file name.")
    if not base.lower().endswith(".md"):
        base = f"{base}.md"
    return base


def render_job_preview(markdown_source: str | None) -> str:
    """Feed raw Markdown into the preview panel."""
    text = (markdown_source or "").strip()
    return text if text else "*Nothing to preview yet. Edit Markdown on the left.*"


def refresh_job_file_dropdown():
    return gr.update(choices=list_job_description_files())


def load_job_description_file(selected: str | None):
    if not selected:
        return (
            gr.update(),
            gr.update(),
            "**Choose a `.md` file, then click Open.**",
        )
    safe = Path(selected).name
    path = JOB_DESCRIPTIONS_DIR / safe
    if not path.is_file():
        return gr.update(), gr.update(), f"**Not found:** `{safe}`"
    text = path.read_text(encoding="utf-8")
    return text, render_job_preview(text), f"**Opened** `{safe}` from `job-descriptions/`."


def save_job_description_file(filename: str, content: str | None):
    try:
        safe = safe_job_filename(filename)
    except ValueError as e:
        return gr.update(), f"**Error:** {e!s}"
    JOB_DESCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = JOB_DESCRIPTIONS_DIR / safe
    path.write_text(content if content is not None else "", encoding="utf-8")
    choices = list_job_description_files()
    return (
        gr.update(choices=choices, value=safe),
        f"**Saved** `{safe}` to `job-descriptions/`.",
    )


def import_pdf_job_description(pdf_file: str | None):
    """Convert PDF → Markdown, save under ``job-descriptions/``, load editor + preview."""
    if not pdf_file:
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "**Choose a PDF file, then click Convert & load.**",
        )
    path = Path(str(pdf_file))
    if path.suffix.lower() != ".pdf":
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            "**Please upload a `.pdf` file.**",
        )
    try:
        md = pdf_to_markdown(path)
    except Exception as e:
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            f"**PDF error:** {e!s}",
        )

    safe = safe_job_filename(f"{path.stem}.md")
    JOB_DESCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = JOB_DESCRIPTIONS_DIR / safe
    out_path.write_text(md, encoding="utf-8")
    choices = list_job_description_files()
    preview = render_job_preview(md)
    return (
        md,
        preview,
        gr.update(choices=choices, value=safe),
        gr.update(value=safe),
        f"**Imported** `{safe}` — PDF converted to Markdown, saved to `job-descriptions/`, and loaded.",
    )


def refresh_settings_fields():
    """Populate model/base URL and summary from ``os.environ`` (does not reload `.env`)."""
    model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
    base = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or ""
    return model, base, gradio_settings.settings_summary_md()


def reload_env_from_disk():
    """Reload `recruitment_use_case/.env` over current session variables."""
    load_project_env(override_file=True)
    return refresh_settings_fields()


async def run_pipeline(job_description: str | tuple | None):
    placeholder_intermediate = "_Waiting for phase 1…_"

    raw = job_description
    if isinstance(raw, tuple):
        raw = raw[0] if raw else ""
    if raw is None:
        raw = ""
    text = str(raw).strip()

    if not text:
        yield (
            "**Paste job requirements first.**",
            placeholder_intermediate,
            "",
        )
        return

    mgr = RecruitmentManager()
    status_lines: list[str] = []
    sections: list[str] = []
    final_md = ""

    async for ev in mgr.run(text):
        if ev["kind"] == "status":
            status_lines.append(ev["message"])
        elif ev["kind"] == "artifact":
            sections.append(
                f"### {ev['title']}\n*{ev['filename']}*\n\n{ev['markdown']}"
            )
        elif ev["kind"] == "final_report":
            final_md = ev["markdown"]

        intermediate = (
            "\n\n---\n\n".join(sections) if sections else placeholder_intermediate
        )
        yield (
            "\n".join(status_lines),
            intermediate,
            final_md,
        )


def apply_settings(model, base_url, openai_key, serper_key, li_cookie, li_email, li_pw):
    gradio_settings.apply_to_environ(
        model, base_url, openai_key, serper_key, li_cookie, li_email, li_pw
    )
    notice = "**Applied** to this Python session (in-memory). Pipeline **Run** uses these values."
    summary = gradio_settings.settings_summary_md()
    empty = gr.update(value="")
    return notice, summary, empty, empty, empty, empty


def save_settings(model, base_url, openai_key, serper_key, li_cookie, li_email, li_pw):
    msg = gradio_settings.save_to_dotenv(
        model, base_url, openai_key, serper_key, li_cookie, li_email, li_pw
    )
    summary = gradio_settings.settings_summary_md()
    empty = gr.update(value="")
    return f"**{msg}**", summary, empty, empty, empty, empty


def test_openai_btn(model, base_url, openai_key):
    return gradio_settings.test_openai(model, base_url, openai_key)


def test_serper_btn(serper_key):
    return gradio_settings.test_serper(serper_key)


def test_linkedin_btn(li_cookie, li_email, li_pw):
    return gradio_settings.run_linkedin_test_sync(li_cookie, li_email, li_pw)


with gr.Blocks(theme=gr.themes.Default(primary_hue="sky")) as ui:
    gr.Markdown("# Recruitment (OpenAI Agents SDK)")
    gr.Markdown(
        "Phases 1–3 appear under **Intermediate results** as each step finishes; the **Executive report** "
        "updates when phase 4 completes. Files are also written to `output/`."
    )

    with gr.Accordion("Settings", open=False):
        settings_summary = gr.Markdown(gradio_settings.settings_summary_md())
        settings_notice = gr.Markdown("")

        model_in = gr.Textbox(
            label="Model (`OPENAI_MODEL_NAME`)",
            value=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
        )
        base_url_in = gr.Textbox(
            label="API base URL (`OPENAI_BASE_URL`, optional)",
            placeholder="Empty = default OpenAI host",
            value=os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "",
        )

        gr.Markdown("Secrets use password fields; leave blank to **keep** the current session value.")

        openai_key_in = gr.Textbox(
            label="OpenAI API key",
            type="password",
            placeholder="Leave blank to keep current",
        )
        with gr.Row():
            test_openai_b = gr.Button("Test OpenAI", size="sm")
        test_openai_out = gr.Markdown()

        serper_key_in = gr.Textbox(
            label="Serper API key (`SERPER_API_KEY`)",
            type="password",
            placeholder="Leave blank to keep current",
        )
        with gr.Row():
            test_serper_b = gr.Button("Test Serper", size="sm")
        test_serper_out = gr.Markdown()

        gr.Markdown(
            "**LinkedIn:** use **cookie** (`li_at`) *or* **email + password**. "
            "Headless login may fail — set `LINKEDIN_HEADLESS=false` in `.env` if needed."
        )
        li_cookie_in = gr.Textbox(
            label="LinkedIn cookie (`LINKEDIN_COOKIE`)",
            type="password",
            placeholder="Leave blank to keep current",
        )
        li_email_in = gr.Textbox(
            label="LinkedIn email",
            placeholder="Optional if cookie set",
        )
        li_pw_in = gr.Textbox(
            label="LinkedIn password",
            type="password",
            placeholder="Leave blank to keep current",
        )
        with gr.Row():
            test_li_b = gr.Button("Test LinkedIn", size="sm")
        test_li_out = gr.Markdown()

        with gr.Row():
            apply_b = gr.Button("Apply to session", variant="secondary")
            save_b = gr.Button("Save to `.env`")
            reload_b = gr.Button("Reload from `.env`")

    gr.Markdown("### Job requirements")
    gr.Markdown(
        "Edit **Markdown** in the code editor (syntax-aware). The right column shows the **rendered** preview. "
        "Stored JD files: **`job-descriptions/*.md`**. **PDF:** upload a text-based PDF and use **Convert** "
        "(image-only scans may not extract)."
    )
    job_files_notice = gr.Markdown("")
    with gr.Row():
        job_file_dropdown = gr.Dropdown(
            choices=list_job_description_files(),
            label="Open from folder",
            interactive=True,
            scale=3,
        )
        open_job_btn = gr.Button("Open", size="sm", scale=0)
        save_filename_in = gr.Textbox(
            label="Save as",
            placeholder="e.g. senior-backend.md",
            scale=2,
        )
        save_job_btn = gr.Button("Save to folder", size="sm", scale=0)
    with gr.Row():
        pdf_upload = gr.File(
            label="Upload PDF job description",
            file_types=[".pdf"],
            type="filepath",
            scale=3,
        )
        import_pdf_btn = gr.Button("Convert PDF → Markdown & load", size="sm", scale=0)
    with gr.Row(equal_height=False):
        job_editor = gr.Code(
            label="Editor (Markdown)",
            language="markdown",
            lines=22,
            wrap_lines=True,
            show_line_numbers=True,
            value="",
        )
        job_preview = gr.Markdown(
            value="*Nothing to preview yet. Edit Markdown on the left.*",
            label="Rendered preview",
        )

    run_btn = gr.Button("Run", variant="primary")
    status_md = gr.Markdown(label="Activity log")
    intermediate_md = gr.Markdown(label="Intermediate results (phases 1–3)")
    report_md = gr.Markdown(label="Executive report (phase 4)")

    ui.load(
        fn=refresh_settings_fields,
        inputs=[],
        outputs=[model_in, base_url_in, settings_summary],
    )
    ui.load(
        fn=render_job_preview,
        inputs=[job_editor],
        outputs=[job_preview],
    )
    ui.load(
        fn=refresh_job_file_dropdown,
        inputs=[],
        outputs=[job_file_dropdown],
    )

    apply_b.click(
        fn=apply_settings,
        inputs=[
            model_in,
            base_url_in,
            openai_key_in,
            serper_key_in,
            li_cookie_in,
            li_email_in,
            li_pw_in,
        ],
        outputs=[
            settings_notice,
            settings_summary,
            openai_key_in,
            serper_key_in,
            li_cookie_in,
            li_pw_in,
        ],
    )

    save_b.click(
        fn=save_settings,
        inputs=[
            model_in,
            base_url_in,
            openai_key_in,
            serper_key_in,
            li_cookie_in,
            li_email_in,
            li_pw_in,
        ],
        outputs=[
            settings_notice,
            settings_summary,
            openai_key_in,
            serper_key_in,
            li_cookie_in,
            li_pw_in,
        ],
    )

    reload_b.click(
        fn=reload_env_from_disk,
        inputs=[],
        outputs=[model_in, base_url_in, settings_summary],
    )

    job_editor.change(
        fn=render_job_preview,
        inputs=job_editor,
        outputs=job_preview,
    )

    open_job_btn.click(
        fn=load_job_description_file,
        inputs=[job_file_dropdown],
        outputs=[job_editor, job_preview, job_files_notice],
    )
    save_job_btn.click(
        fn=save_job_description_file,
        inputs=[save_filename_in, job_editor],
        outputs=[job_file_dropdown, job_files_notice],
    )

    import_pdf_btn.click(
        fn=import_pdf_job_description,
        inputs=[pdf_upload],
        outputs=[
            job_editor,
            job_preview,
            job_file_dropdown,
            save_filename_in,
            job_files_notice,
        ],
    )

    test_openai_b.click(
        fn=test_openai_btn,
        inputs=[model_in, base_url_in, openai_key_in],
        outputs=[test_openai_out],
    )
    test_serper_b.click(
        fn=test_serper_btn,
        inputs=[serper_key_in],
        outputs=[test_serper_out],
    )
    test_li_b.click(
        fn=test_linkedin_btn,
        inputs=[li_cookie_in, li_email_in, li_pw_in],
        outputs=[test_li_out],
    )

    run_btn.click(
        fn=run_pipeline,
        inputs=job_editor,
        outputs=[status_md, intermediate_md, report_md],
    )

if __name__ == "__main__":
    ui.launch(inbrowser=True)
