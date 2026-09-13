"""LinkedIn profile scraping as an OpenAI Agents async function_tool."""

from __future__ import annotations

import asyncio
import os
import re

from agents import function_tool

from linkedin_auth import authenticate_linkedin_page, linkedin_chromium_launch_options
from linkedin_scraper import (
    AuthenticationError,
    BrowserManager,
    Person,
    PersonScraper,
    ProfileNotFoundError,
    RateLimitError,
)


def _headless_from_env() -> bool:
    v = os.getenv("LINKEDIN_HEADLESS", "true").lower().strip()
    return v in ("1", "true", "yes", "on")


def _extract_urls(text: str) -> list[str]:
    """Collect unique LinkedIn /in/ URLs from free text."""
    seen: set[str] = set()
    out: list[str] = []
    for m in re.finditer(
        r"https?://(?:[\w.-]+\.)?linkedin\.com/in/[\w%-]+/?",
        text,
        re.IGNORECASE,
    ):
        u = m.group(0).split("?")[0].rstrip("/")
        if u not in seen:
            seen.add(u)
            out.append(u)
    if out:
        return out
    for part in re.split(r"[\s,;]+", text.strip()):
        part = part.strip().strip("'\"")
        if "linkedin.com/in/" not in part.lower():
            continue
        if not part.startswith("http"):
            part = "https://" + part.lstrip("/")
        part = part.split("?")[0].rstrip("/")
        if part not in seen:
            seen.add(part)
            out.append(part)
    return out


def _format_person(person: Person) -> str:
    lines = [
        "Person Profile",
        "-------------",
        person.name or "(name unavailable)",
        person.job_title or "(title unavailable)",
        person.location or "(location unavailable)",
        str(person.linkedin_url),
    ]
    if person.about:
        about = person.about.strip()
        if len(about) > 800:
            about = about[:800] + "…"
        lines.append(f"About: {about}")
    if person.experiences:
        lines.append("Experience (recent):")
        for exp in person.experiences[:5]:
            title = exp.position_title or ""
            org = exp.institution_name or ""
            dates = ""
            if exp.from_date or exp.to_date:
                dates = f" ({exp.from_date or '?'} – {exp.to_date or 'present'})"
            lines.append(f"  - {title} at {org}{dates}")
    if person.educations:
        lines.append("Education:")
        for edu in person.educations[:3]:
            lines.append(
                f"  - {(edu.degree or '')} {(edu.institution_name or '')}".strip()
            )
    return "\n".join(lines)


async def _scrape_profiles_async(profile_urls: str) -> str:
    urls = _extract_urls(profile_urls)
    if not urls:
        return (
            "Error: No LinkedIn profile URLs found. Pass one or more "
            "https://www.linkedin.com/in/... URLs (comma, space, or newline separated). "
            "Discover candidates with web search first, then call this tool with their profile links."
        )

    blocks: list[str] = []
    headless = _headless_from_env()

    async with BrowserManager(
        headless=headless,
        **linkedin_chromium_launch_options(),
    ) as browser:
        try:
            await authenticate_linkedin_page(browser.page)
        except AuthenticationError as e:
            return f"Error: {e!s}"
        scraper = PersonScraper(browser.page)

        for i, url in enumerate(urls):
            try:
                person = await scraper.scrape(url)
                blocks.append(_format_person(person))
            except ProfileNotFoundError as e:
                blocks.append(f"Profile not found or private: {url}\n{e!s}")
            except RateLimitError as e:
                blocks.append(f"Rate limited by LinkedIn while scraping {url}: {e!s}")
                break
            except AuthenticationError as e:
                blocks.append(
                    "LinkedIn authentication failed while scraping (refresh "
                    "LINKEDIN_COOKIE or check LINKEDIN_EMAIL/LINKEDIN_PASSWORD): "
                    f"{e!s}"
                )
                break
            except Exception as e:
                blocks.append(f"Error scraping {url}: {e!s}")
            if i < len(urls) - 1:
                await asyncio.sleep(2)

    if not blocks:
        return "No profile data could be scraped."
    return "\n\n".join(blocks)


@function_tool
async def scrape_linkedin_profiles(profile_urls: str) -> str:
    """
    Fetch full LinkedIn profile data (name, title, location, about, experience,
    education) for recruitment. REQUIRED after URLs are collected: paste all
    https://www.linkedin.com/in/... URLs (comma or newline separated).
    Requires LINKEDIN_EMAIL + LINKEDIN_PASSWORD or LINKEDIN_COOKIE in the environment.
    """
    try:
        return await _scrape_profiles_async(profile_urls)
    except AuthenticationError as e:
        return (
            f"LinkedIn authentication failed: {e!s}. "
            "Check LINKEDIN_EMAIL/LINKEDIN_PASSWORD or LINKEDIN_COOKIE (li_at)."
        )
    except Exception as e:
        return f"LinkedIn scrape failed: {e!s}"
