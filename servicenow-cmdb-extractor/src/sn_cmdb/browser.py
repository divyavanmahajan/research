"""
browser.py — Playwright browser and session management.

Responsibilities:
  - Launch a Chromium browser (visible or headless).
  - Interactive login: open visible browser, wait for user to complete login
    (supports SSO, MFA, etc.), then save the authenticated session to disk.
  - Credential login: automate username/password fields (fallback for basic auth).
  - Load a saved session for headless extraction runs.
  - Validate whether a saved session is still authenticated.
  - Provide a context manager that yields a ready Page object.

Session storage format:
  ~/.sn_cmdb/sessions/<hostname>.json  (Playwright storageState JSON)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Generator
from contextlib import contextmanager
from urllib.parse import urlparse

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)
from rich.console import Console
from rich.prompt import Confirm, Prompt

logger = logging.getLogger(__name__)
console = Console()

# URL fragment that indicates a successful ServiceNow login
SN_HOME_PATTERNS = [
    "/now/nav/ui/classic/params/target/%24home.do",
    "/nav_to.do",
    "/$home.do",
    "/now/",
    "/ui/",
]

# Login page URL path used for credential-based login
SN_LOGIN_PATH = "/login.do"

# How long to wait for the user to complete interactive login (seconds)
INTERACTIVE_LOGIN_TIMEOUT_S = 300


class SessionManager:
    """
    Manages Playwright browser sessions for a ServiceNow instance.

    Args:
        instance_url:  Base URL, e.g. ``https://dev12345.service-now.com``
        session_dir:   Directory where session JSON files are persisted.
        headless:      Whether to launch the browser headlessly.
    """

    def __init__(
        self,
        instance_url: str,
        session_dir: Path,
        headless: bool = False,
    ) -> None:
        self.instance_url = instance_url.rstrip("/")
        self.session_dir = session_dir
        self.headless = headless
        self._hostname = urlparse(instance_url).hostname or "unknown"
        self._session_file = session_dir / f"{self._hostname}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def session_exists(self) -> bool:
        """Return True if a saved session file exists on disk."""
        return self._session_file.exists()

    def delete_session(self) -> None:
        """Remove the saved session file."""
        if self._session_file.exists():
            self._session_file.unlink()
            console.print(f"[yellow]Session deleted:[/yellow] {self._session_file}")

    def login_interactive(self) -> None:
        """
        Open a visible browser and wait for the user to complete login manually.
        Saves the session to disk on success.
        Supports SSO, MFA, and any other auth flow the browser can handle.
        """
        console.print(
            "\n[bold cyan]Interactive login[/bold cyan]\n"
            f"  Opening browser at: [link]{self.instance_url}[/link]\n"
            "  Please log in. The tool will detect when login is complete.\n"
            f"  Timeout: {INTERACTIVE_LOGIN_TIMEOUT_S}s\n"
        )
        with sync_playwright() as pw:
            browser, ctx = self._launch_context(pw, headless=False, session_file=None)
            page = ctx.new_page()
            page.goto(f"{self.instance_url}/login.do", wait_until="domcontentloaded")

            # Poll until we detect a successful login
            deadline = time.time() + INTERACTIVE_LOGIN_TIMEOUT_S
            logged_in = False
            while time.time() < deadline:
                current_url = page.url
                if self._is_authenticated_url(current_url):
                    logged_in = True
                    break
                # Check for ServiceNow's glide_user_activity cookie
                cookies = ctx.cookies()
                if any(c["name"] == "glide_user_activity" for c in cookies):
                    logged_in = True
                    break
                page.wait_for_timeout(1500)

            if not logged_in:
                console.print("[red]Login timed out. Please try again.[/red]")
                browser.close()
                return

            self._save_session(ctx)
            console.print(
                f"[green]Login successful![/green] Session saved to {self._session_file}"
            )
            browser.close()

    def login_credentials(self, username: str, password: str) -> bool:
        """
        Automate username/password login (basic auth only — no SSO/MFA).
        Returns True on success.
        """
        console.print(
            f"[cyan]Attempting credential login as[/cyan] [bold]{username}[/bold]"
        )
        with sync_playwright() as pw:
            browser, ctx = self._launch_context(pw, headless=True, session_file=None)
            page = ctx.new_page()
            try:
                page.goto(
                    f"{self.instance_url}/login.do",
                    wait_until="networkidle",
                    timeout=30_000,
                )
                page.fill("#user_name", username)
                page.fill("#user_password", password)
                page.click("#sysverb_login")
                page.wait_for_load_state("networkidle", timeout=30_000)

                if not self._is_authenticated_url(page.url):
                    console.print("[red]Credential login failed — check username/password.[/red]")
                    browser.close()
                    return False

                self._save_session(ctx)
                console.print(
                    f"[green]Login successful![/green] Session saved to {self._session_file}"
                )
                browser.close()
                return True
            except Exception as exc:
                logger.error("Credential login error: %s", exc)
                browser.close()
                return False

    def validate_session(self) -> bool:
        """
        Open a headless browser with the saved session and check if it is
        still authenticated. Returns True if valid.
        """
        if not self.session_exists():
            return False
        try:
            with sync_playwright() as pw:
                browser, ctx = self._launch_context(
                    pw, headless=True, session_file=self._session_file
                )
                page = ctx.new_page()
                page.goto(
                    f"{self.instance_url}/api/now/table/sys_user_session?sysparm_limit=1",
                    wait_until="domcontentloaded",
                    timeout=20_000,
                )
                content = page.content()
                browser.close()
                # If we get JSON back (not a login page), session is valid
                return '"result"' in content or '"sys_id"' in content
        except Exception as exc:
            logger.debug("Session validation error: %s", exc)
            return False

    @contextmanager
    def active_page(
        self,
        *,
        headless: bool | None = None,
        force_visible: bool = False,
    ) -> Generator[Page, None, None]:
        """
        Context manager that yields an authenticated Playwright Page.

        Tries saved session first; falls back to prompting the user to login.

        Args:
            headless:       Override the default headless setting.
            force_visible:  Always open a visible browser (e.g. for login).
        """
        use_headless = headless if headless is not None else self.headless
        if force_visible:
            use_headless = False

        with sync_playwright() as pw:
            session_file = self._session_file if self.session_exists() else None
            browser, ctx = self._launch_context(
                pw, headless=use_headless, session_file=session_file
            )
            page = ctx.new_page()
            try:
                yield page
            finally:
                # Persist any updated cookies/storage back to disk
                if session_file:
                    self._save_session(ctx)
                browser.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _launch_context(
        self,
        pw: Playwright,
        *,
        headless: bool,
        session_file: Path | None,
    ) -> tuple[Browser, BrowserContext]:
        browser = pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx_kwargs: dict[str, Any] = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "ignore_https_errors": True,
        }
        if session_file and session_file.exists():
            with open(session_file) as f:
                ctx_kwargs["storage_state"] = json.load(f)
            logger.debug("Loaded session from %s", session_file)

        ctx = browser.new_context(**ctx_kwargs)
        return browser, ctx

    def _save_session(self, ctx: BrowserContext) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        state = ctx.storage_state()
        with open(self._session_file, "w") as f:
            json.dump(state, f, indent=2)
        # Restrict permissions — session file contains sensitive cookies
        self._session_file.chmod(0o600)
        logger.debug("Session saved to %s", self._session_file)

    def _is_authenticated_url(self, url: str) -> bool:
        """Heuristic: return True if the URL looks like a post-login ServiceNow page."""
        if "login.do" in url or "login_with_sso.do" in url:
            return False
        for pattern in SN_HOME_PATTERNS:
            if pattern in url:
                return True
        # If the URL is on the instance and doesn't look like a login page, assume ok
        if self.instance_url.lower() in url.lower():
            return True
        return False
