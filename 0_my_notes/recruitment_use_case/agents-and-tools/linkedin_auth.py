"""Shared LinkedIn Playwright authentication for the scrape tool and connection check."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from linkedin_scraper import AuthenticationError, login_with_cookie
from linkedin_scraper.core import detect_rate_limit, is_logged_in, warm_up_browser


def linkedin_chromium_launch_options() -> dict[str, Any]:
    """Pass as ``BrowserManager(..., **linkedin_chromium_launch_options())``."""
    return {
        "args": [
            "--disable-blink-features=AutomationControlled",
        ],
    }


async def _try_dismiss_cookie_banner(page) -> None:
    """Best-effort; consent UIs vary by region."""
    selectors = (
        'button[action-type="ACCEPT"]',
        '[data-control-name="accept"]',
        "button.artdeco-global-alert__action",
    )
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=2500)
            await loc.click(timeout=3000)
            await asyncio.sleep(0.4)
            return
        except Exception:
            continue


async def login_with_credentials_flexible(
    page,
    email: str,
    password: str,
    *,
    timeout_ms: int = 90000,
) -> None:
    """
    Email/password login with selectors aligned to current LinkedIn login markup.

    Supplements linkedin_scraper's ``login_with_credentials`` (which only waits for ``#username``),
    which often fails in headless or when LinkedIn serves ``session_key`` / ``session_password`` fields.
    """
    await warm_up_browser(page)

    await page.goto(
        "https://www.linkedin.com/login",
        wait_until="domcontentloaded",
        timeout=timeout_ms,
    )
    await detect_rate_limit(page)
    await _try_dismiss_cookie_banner(page)

    user_selectors = (
        "#username, "
        "input[name='session_key'], "
        "input[id='username'], "
        "input[type='email']"
    )
    pass_selectors = (
        "#password, "
        "input[name='session_password'], "
        "input[id='password']"
    )

    try:
        user_field = page.locator(user_selectors).first
        await user_field.wait_for(state="visible", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        url = page.url
        if "authwall" in url:
            raise AuthenticationError(
                "LinkedIn showed an auth wall instead of the login form. "
                "Set LINKEDIN_HEADLESS=false in .env and retry, or use LINKEDIN_COOKIE (li_at)."
            ) from None
        raise AuthenticationError(
            "Login email field not found. LinkedIn often blocks headless automation — "
            "set LINKEDIN_HEADLESS=false, complete any challenge in the browser, "
            "or use LINKEDIN_COOKIE (li_at). "
            f"Current URL: {url}"
        ) from None

    await user_field.fill(email)
    pwd_field = page.locator(pass_selectors).first
    await pwd_field.wait_for(state="visible", timeout=15000)
    await pwd_field.fill(password)

    submitted = False
    for sel in ("button[type='submit']", "input[type='submit']"):
        try:
            await page.locator(sel).first.click(timeout=8000)
            submitted = True
            break
        except Exception:
            continue
    if not submitted:
        for name in ("Sign in", "Se connecter", "S’identifier", "Accept and Sign in"):
            try:
                await page.get_by_role("button", name=name).click(timeout=8000)
                submitted = True
                break
            except Exception:
                continue
    if not submitted:
        raise AuthenticationError(
            "Could not find LinkedIn Sign in / submit control after entering credentials."
        )

    try:
        await page.wait_for_url(
            lambda u: any(
                x in u
                for x in ("feed", "checkpoint", "challenge", "authwall", "linkedin.com/feed")
            ),
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError:
        if "login" in page.url:
            raise AuthenticationError(
                "Login did not finish (still on login). Check email/password, "
                "or try LINKEDIN_HEADLESS=false / LINKEDIN_COOKIE."
            ) from None

    current_url = page.url
    if "checkpoint" in current_url or "challenge" in current_url:
        raise AuthenticationError(
            "LinkedIn security checkpoint after sign-in. "
            "Set LINKEDIN_HEADLESS=false and complete verification, or use LINKEDIN_COOKIE. "
            f"URL: {current_url}"
        )
    if "authwall" in current_url:
        raise AuthenticationError(
            f"Authentication wall after sign-in: {current_url}"
        )

    deadline = time.time() + 12.0
    while time.time() < deadline:
        if await is_logged_in(page):
            return
        await asyncio.sleep(0.5)

    raise AuthenticationError(
        "Could not confirm LinkedIn session after login (nav markers missing). "
        "Try LINKEDIN_HEADLESS=false or LINKEDIN_COOKIE (li_at)."
    )


async def authenticate_linkedin_page(page) -> None:
    """
    Log in to LinkedIn on the given Playwright page.

    Priority:
    1. LINKEDIN_EMAIL + LINKEDIN_PASSWORD (LINKEDIN_USERNAME is accepted as an alias for email)
    2. Else LINKEDIN_COOKIE (raw li_at value), via login_with_cookie

    Raises:
        AuthenticationError: If no valid auth configuration is present or login fails.
    """
    email = (os.getenv("LINKEDIN_EMAIL") or os.getenv("LINKEDIN_USERNAME") or "").strip()
    password = os.getenv("LINKEDIN_PASSWORD", "").strip()
    cookie = os.getenv("LINKEDIN_COOKIE", "").strip()

    if email and password:
        await login_with_credentials_flexible(page, email, password)
        return
    if cookie:
        await login_with_cookie(page, cookie)
        return

    raise AuthenticationError(
        "LinkedIn authentication is not configured. Set LINKEDIN_EMAIL and "
        "LINKEDIN_PASSWORD, or set LINKEDIN_COOKIE (li_at), in recruitment/.env (see README)."
    )
