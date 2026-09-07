#!/usr/bin/env python3
"""Keep one VNC-visible Firefox session alive for Canvas ClassLink access.

Run this with ``DISPLAY=:1`` after starting VNC.  Sign into ClassLink manually
in the Firefox window; the normal scraper then sends read-only requests to this
process over a localhost-only HTTP endpoint.  Passwords, cookies, and browser
storage never leave Firefox.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.canvas_scraper import (  # noqa: E402
    CANVAS_API_URL,
    CLASSLINK_URL,
    CanvasBrowserClient,
    CanvasSessionError,
    CanvasSignInRequired,
)
import config  # noqa: E402
from config import get_setting  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("canvas_browser_daemon")

CLASSLINK_APP_URL = "https://myapps.classlink.com/home"
CLASSLINK_HOSTS = {"launchpad.classlink.com", "myapps.classlink.com"}
CLASSLINK_NON_APP_LABELS = {
    "add apps", "add & share apps", "edit mode", "help", "home", "log out",
    "logout", "my apps", "notifications", "profile", "search", "settings",
    "sign out", "switch account",
}


class VirtualDisplay:
    """Provide a regular Firefox display for unattended system-service use."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        if os.environ.get("DISPLAY"):
            return
        binary = shutil.which("Xvfb")
        if not binary:
            raise RuntimeError("DISPLAY is not set and Xvfb is not installed.")
        display = get_setting("CANVAS_VIRTUAL_DISPLAY", ":99")
        disp_num = display.lstrip(":")
        lock_file = Path(f"/tmp/.X{disp_num}-lock")
        if lock_file.exists():
            try:
                pid = int(lock_file.read_text().strip())
                os.kill(pid, 0)
            except OSError:
                try:
                    lock_file.unlink()
                except OSError:
                    pass
            except ValueError:
                pass
        self.process = subprocess.Popen(
            [binary, display, "-screen", "0", "1440x900x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.4)
        if self.process.poll() is not None:
            raise RuntimeError("Could not start the Canvas virtual display.")
        os.environ["DISPLAY"] = display

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class BrowserDaemon:
    def __init__(self) -> None:
        self.client = CanvasBrowserClient(headless=False, use_daemon=False)
        self.lock = threading.Lock()
        self.was_authenticated = False
        self.last_reauth_attempt = 0.0
        self.reauth_cooldown = int(get_setting("CANVAS_REAUTH_COOLDOWN_SECONDS", "900"))

    def start(self) -> None:
        self.client._start_browser()
        assert self.client.driver is not None
        self.client.driver.get(CLASSLINK_URL)

    def _session_alive(self) -> bool:
        """Cheap probe: is the CURRENT browsing context still usable?

        ``window_handles`` is browser-level and keeps succeeding after the
        tab the driver is parked on gets discarded (Firefox memory
        pressure), so probe something that touches the current context.
        """
        driver = self.client.driver
        if driver is None:
            return False
        try:
            driver.current_url
            return True
        except Exception:
            return False

    def restart_browser(self) -> None:
        """Relaunch Firefox after the Selenium session dies (crash, OOM).

        Cookies persist in the profile, so Canvas/ClassLink/OneNote sign-ins
        restore silently on the next crawl. Caller must hold self.lock (or be
        the sole operator) — this swaps self.client wholesale.
        """
        logger.warning("Browser session dead — relaunching Firefox")
        try:
            self.client.close()
        except Exception:
            pass
        self.client = CanvasBrowserClient(headless=False, use_daemon=False)
        self.start()
        logger.info("Browser relaunched")

    def location(self) -> str:
        assert self.client.driver is not None
        return self.client._safe_browser_location()

    def _select_canvas_tab(self) -> bool:
        """Select the Canvas tab when ClassLink opens it in a new window/tab."""
        assert self.client.driver is not None
        driver = self.client.driver
        original = driver.current_window_handle
        canvas_host = urlsplit(CANVAS_API_URL).netloc
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if urlsplit(driver.current_url).netloc == canvas_host:
                return True
        driver.switch_to.window(original)
        return False

    def _select_classlink_tab(self) -> bool:
        """Select a ClassLink tab, opening only the app dashboard if needed."""
        assert self.client.driver is not None
        driver = self.client.driver
        original = driver.current_window_handle
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if urlsplit(driver.current_url).netloc in CLASSLINK_HOSTS:
                return True
        # Canvas may have opened in a new tab and replaced the LaunchPad tab.
        # Opening the dashboard is read-only and reuses the existing ClassLink
        # session; no app itself is opened.
        try:
            driver.switch_to.new_window("tab")
            driver.get(CLASSLINK_APP_URL)
            return urlsplit(driver.current_url).netloc in CLASSLINK_HOSTS
        except Exception:
            try:
                driver.switch_to.window(original)
            except Exception:
                pass
            return False

    @staticmethod
    def _clean_app_entries(entries: object) -> list[dict[str, str | None]]:
        """Remove dashboard chrome and de-duplicate visible app labels."""
        if not isinstance(entries, list):
            return []
        apps: list[dict[str, str | None]] = []
        seen: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = " ".join(str(entry.get("name") or "").split())
            if not name or len(name) > 140 or name.lower() in CLASSLINK_NON_APP_LABELS:
                continue
            # Dashboard navigation controls normally have no app-like parent
            # class and no destination. Keep actual applications even when
            # ClassLink launches them with JavaScript instead of an href.
            href = entry.get("href")
            class_name = str(entry.get("className") or "").lower()
            if not href and "app" not in class_name and "tile" not in class_name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            apps.append({"name": name, "url": str(href) if href else None})
        return apps

    def list_classlink_apps(self) -> dict[str, object]:
        """List visible ClassLink app tiles without opening any application."""
        assert self.client.driver is not None
        with self.lock:
            if not self._select_classlink_tab():
                raise CanvasSignInRequired("ClassLink is not available in the persistent Firefox session.")
            driver = self.client.driver
            deadline = time.monotonic() + 10
            entries: object = []
            while time.monotonic() < deadline:
                entries = driver.execute_script(
                    """
                    return Array.from(document.querySelectorAll(
                      'a, button, [role="link"], [role="button"]'
                    )).map((element) => ({
                      name: element.getAttribute('aria-label') || element.getAttribute('title') || element.innerText || '',
                      href: element.href || element.getAttribute('data-url') || null,
                      className: [
                        element.className || '',
                        element.parentElement?.className || '',
                        element.closest('[class*="app" i], [class*="tile" i]')?.className || ''
                      ].join(' ')
                    }));
                    """
                )
                apps = self._clean_app_entries(entries)
                if apps:
                    return {"apps": apps, "location": self.location()}
                time.sleep(0.5)
            return {"apps": [], "location": self.location()}

    def health(self) -> dict[str, object]:
        with self.lock:
            if not self._session_alive():
                self.restart_browser()
            assert self.client.driver is not None
            self._select_canvas_tab()
            host = urlsplit(self.client.driver.current_url).netloc
            if not host.endswith("instructure.com"):
                return {"authenticated": False, "location": self.location()}
            try:
                user = self.client.get_current_user()
                authenticated = bool(user.get("id"))
                self.was_authenticated = self.was_authenticated or authenticated
                return {"authenticated": authenticated, "location": self.location()}
            except CanvasSessionError:
                return {"authenticated": False, "location": self.location()}

    def auto_reauthenticate(self) -> None:
        """Run the ordinary ClassLink → ADFS → Canvas flow without a manual bootstrap."""
        if not get_setting("CLASSLINK_USERNAME") or not get_setting("CLASSLINK_PASSWORD"):
            logger.warning("Automatic ClassLink sign-in is disabled: credentials are not configured")
            return
        if time.monotonic() - self.last_reauth_attempt < self.reauth_cooldown:
            return

        self.last_reauth_attempt = time.monotonic()
        logger.info("Attempting normal ClassLink → ADFS → Canvas authentication")
        try:
            with self.lock:
                self.client._sign_in_via_classlink()
                if not self.client._is_canvas_authenticated():
                    logger.warning("Automatic ClassLink authentication did not reach Canvas; inspect the VNC browser window")
        except CanvasSessionError as exc:
            logger.warning("Automatic ClassLink authentication needs attention in VNC: %s", exc)
        except Exception:
            logger.exception("Automatic ClassLink reauthentication failed")

    def request(self, path_or_url: str) -> tuple[object, str]:
        target = urlsplit(path_or_url)
        canvas_host = urlsplit(CANVAS_API_URL).netloc
        if target.netloc and target.netloc != canvas_host:
            raise CanvasSessionError("Only the configured Canvas domain may be requested.")
        if not target.path.startswith("/api/v1/"):
            raise CanvasSessionError("Only Canvas API v1 paths may be requested.")
        with self.lock:
            if not self._select_canvas_tab():
                raise CanvasSignInRequired("Canvas is not open in the persistent Firefox session.")
            return self.client._request_json(path_or_url)

    def download_canvas_file(self, file_id: str) -> tuple[bytes, str, str]:
        """Download a bounded Canvas file through Firefox, never via copied cookies."""
        if not file_id.isdigit():
            raise CanvasSessionError("Canvas file IDs must be numeric.")
        max_bytes = max(1, int(get_setting("CANVAS_STUDY_FILE_MAX_MB", "15"))) * 1024 * 1024
        with self.lock:
            if not self._select_canvas_tab():
                raise CanvasSignInRequired("Canvas is not open in the persistent Firefox session.")
            metadata = self.client.get_json(f"/api/v1/files/{file_id}")
            if not isinstance(metadata, dict) or not metadata.get("url"):
                raise CanvasSessionError("Canvas did not provide a downloadable file URL.")
            result = self.client.driver.execute_async_script(
                """
                const target = arguments[0];
                const maxBytes = arguments[1];
                const done = arguments[arguments.length - 1];
                fetch(target, {credentials: 'include', redirect: 'follow'}).then(async (response) => {
                  const declaredSize = Number(response.headers.get('content-length') || 0);
                  if (!response.ok) throw new Error(`HTTP ${response.status}`);
                  if (declaredSize && declaredSize > maxBytes) throw new Error('File is larger than the configured limit.');
                  const buffer = await response.arrayBuffer();
                  if (buffer.byteLength > maxBytes) throw new Error('File is larger than the configured limit.');
                  const bytes = new Uint8Array(buffer);
                  let binary = '';
                  const chunkSize = 0x8000;
                  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
                    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
                  }
                  done({
                    data: btoa(binary),
                    contentType: response.headers.get('content-type') || 'application/octet-stream'
                  });
                }).catch((error) => done({error: String(error)}));
                """,
                metadata["url"],
                max_bytes,
            )
            if not isinstance(result, dict) or result.get("error") or not result.get("data"):
                raise CanvasSessionError(
                    f"Canvas file download failed: {result.get('error', 'unknown error') if isinstance(result, dict) else 'unknown error'}"
                )
            try:
                content = base64.b64decode(result["data"], validate=True)
            except (TypeError, ValueError) as exc:
                raise CanvasSessionError("Canvas returned invalid file data.") from exc
            if len(content) > max_bytes:
                raise CanvasSessionError("Canvas file is larger than the configured limit.")
            filename = str(metadata.get("display_name") or metadata.get("filename") or f"canvas-{file_id}")
            return content, str(result.get("contentType") or "application/octet-stream"), filename

    def _find_clickable(self, driver, needles: list[str], exact: bool = False,
                        exclude: list[str] | None = None):
        """Deepest clickable element whose label matches a needle and none of
        the exclusions.

        Searches light DOM and shadow roots (ClassLink renders tiles inside
        web components). Prefers the candidate with the shortest matching
        label — tile nodes over their wrappers.
        """
        return driver.execute_script(
            """
            const needles = arguments[0].map((n) => n.toLowerCase());
            const exact = arguments[1];
            const exclude = (arguments[2] || []).map((n) => n.toLowerCase());
            const norm = (el) => [
                el.innerText, el.textContent,
                el.getAttribute && el.getAttribute('aria-label'),
                el.getAttribute && el.getAttribute('title'),
                el.getAttribute && el.getAttribute('alt')
            ].filter(Boolean).join(' ').replace(/\\s+/g, ' ').trim().toLowerCase();
            let best = null;
            let bestLen = Infinity;
            function consider(el) {
                const target = el.closest('a, button, [role="button"], [role="link"], .app-icon, .app-tile') || el;
                const label = norm(target);
                if (!label) return;
                if (exclude.some((n) => label.includes(n))) return;
                const hit = exact
                    ? needles.some((n) => label === n)
                    : needles.some((n) => label.includes(n));
                if (!hit || label.length >= bestLen) return;
                best = target;
                bestLen = label.length;
            }
            function walk(root) {
                for (const el of root.querySelectorAll('*')) {
                    if (el.shadowRoot) walk(el.shadowRoot);
                    consider(el);
                }
            }
            walk(document);
            return best;
            """,
            needles,
            exact,
            exclude or [],
        )

    def _click_follow(self, driver, element) -> str:
        """Click an element and follow the outcome.

        Returns 'new_tab' after switching into a freshly opened tab, or
        'same' when the click navigated in place. Raises on obvious failure.
        """
        from selenium.webdriver.common.action_chains import ActionChains

        handles_before = set(driver.window_handles)
        url_before = driver.current_url
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            ActionChains(driver).move_to_element(element).pause(0.2).click().perform()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            handles = driver.window_handles
            fresh = [h for h in handles if h not in handles_before]
            if fresh:
                driver.switch_to.window(fresh[-1])
                return "new_tab"
            try:
                if driver.current_url != url_before:
                    return "same"
            except Exception:
                pass
            time.sleep(1)
        return "same"

    def _wait_off_auth_hosts(self, driver, timeout: float = 45) -> bool:
        """Wait until the current tab leaves login/classlink/adfs hosts."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                host = urlsplit(driver.current_url).netloc.lower()
            except Exception:
                time.sleep(2)
                continue
            if host and not any(
                fragment in host
                for fragment in ("login.microsoftonline", "login.live", "classlink", "adfs")
            ):
                return True
            time.sleep(2)
        return False

    def _microsoft_sign_in(self) -> tuple[bool, str]:
        """Complete the Microsoft sign-in form with stored school credentials.

        The ClassLink SSO tile does not federate into M365 for this tenant, so
        the first sign-in is a normal form flow: UPN (MICROSOFT_UPN) → ADFS →
        school password (CLASSLINK_PASSWORD) → "Stay signed in". Returns
        (success, detail).
        """
        assert self.client.driver is not None
        driver = self.client.driver
        upn = get_setting("MICROSOFT_UPN") or get_setting("CLASSLINK_USERNAME")
        password = get_setting("CLASSLINK_PASSWORD")
        if not upn or not password:
            return False, "MICROSOFT_UPN/CLASSLINK_PASSWORD not configured"

        def _wait_css(selector: str, timeout: float) -> Any | None:
            from selenium.webdriver.support.ui import WebDriverWait

            try:
                return WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script(
                        "const el = document.querySelector(arguments[0]);"
                        "return el ? el : null;",
                        selector,
                    )
                )
            except Exception:
                return None

        # 1. Click the "Sign in" affordance on the anonymous shell. When the
        # crawl already landed mid-auth (pick-account / form), skip straight
        # to the credential steps.
        on_login_page = driver.execute_script(
            "return location.host.includes('login.microsoftonline')"
            " || location.host.includes('login.live');"
        )
        clicked = on_login_page
        if not clicked:
            clicked = driver.execute_script(
                """
                const candidates = Array.from(
                    document.querySelectorAll('a, button, [role="button"]')
                );
                const norm = (el) => (el.innerText || el.getAttribute('aria-label') || '')
                    .trim().toLowerCase();
                const btn = candidates.find((el) => norm(el) === 'sign in')
                    || candidates.find((el) => norm(el).includes('sign in'))
                    || document.querySelector('a[href*="signin"], a[href*="login"]');
                if (btn) { btn.click(); return true; }
                return false;
                """
            )
        if not clicked:
            return False, "no Sign in button found"

        # 2a. "Pick an account" — the profile remembers the school UPN; click
        # its tile when present (skips the email form entirely). Uses a
        # Selenium-native click: JS .click() on the row's inner nodes does not
        # trigger the picker's event handlers.
        picker_detail = "picker never appeared"
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                tiles = driver.find_elements(
                    "xpath",
                    "//*[contains(translate(normalize-space(.), "
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
                    "'" + upn.lower() + "')]",
                )
            except Exception:
                tiles = []
            if tiles:
                try:
                    tiles[-1].click()  # deepest match
                    picker_detail = f"clicked {tiles[-1].tag_name}"
                    break
                except Exception as exc:
                    picker_detail = f"click failed: {type(exc).__name__}"
            elif driver.execute_script(
                "return !!document.querySelector("
                "\"input[type='email'], input[name='loginfmt'], input[type='password']\");"
            ):
                picker_detail = "form shown instead of picker"
                break
            time.sleep(1)

        # 2b. UPN step (login.microsoftonline.com / login.live.com), when the
        # picker did not short-circuit it.
        email_input = _wait_css("input[type='email'], input[name='loginfmt']", 12)
        if email_input:
            email_input.clear()
            email_input.send_keys(upn)
            driver.execute_script(
                """
                const next = document.querySelector('input[type=submit], #idSIButton9')
                    || Array.from(document.querySelectorAll('button'))
                        .find((b) => (b.innerText || '').trim().toLowerCase() === 'next');
                if (next) next.click();
                """
            )

        # 2c. Settle: the session may already be valid (picker → straight to
        # the app, no password), or the federated ADFS form appears — in the
        # main document OR inside an iframe, so search frames before giving up.
        def _find_password_input(timeout: float):
            from selenium.webdriver.support.ui import WebDriverWait

            def poll(_d):
                try:
                    return _d.find_element(
                        "css selector",
                        "input[type='password'], input[name='passwd'], #passwordInput",
                    )
                except Exception:
                    pass
                try:
                    for frame in _d.find_elements("tag name", "iframe"):
                        try:
                            _d.switch_to.frame(frame)
                            return _d.find_element(
                                "css selector",
                                "input[type='password'], input[name='passwd'], #passwordInput",
                            )
                        except Exception:
                            _d.switch_to.default_content()
                except Exception:
                    pass
                return None

            try:
                return WebDriverWait(driver, timeout).until(poll)
            except Exception:
                driver.switch_to.default_content()
                return None

        def _on_login_domain() -> bool:
            try:
                host = urlsplit(driver.current_url).netloc.lower()
            except Exception:
                return True
            return "login.microsoftonline" in host or "login.live" in host

        deadline = time.monotonic() + 45
        password_input = None
        while time.monotonic() < deadline:
            if not _on_login_domain():
                return True, "signed in (existing session, no password needed)"
            password_input = _find_password_input(2)
            if password_input is not None:
                break
            time.sleep(2)

        if password_input is None:
            if not _on_login_domain():
                return True, "signed in (existing session, no password needed)"
            driver.switch_to.default_content()
            return False, f"password step did not appear (picker: {picker_detail})"
        password_input.clear()
        password_input.send_keys(password)
        in_frame = False
        try:
            password_input.parent.switch_to.default_content()
        except Exception:
            pass
        driver.switch_to.default_content()
        driver.execute_script(
            """
            const go = document.querySelector(
                'input[type=submit], #idSIButton9, #submitButton, span#submitButton'
            ) || Array.from(document.querySelectorAll('button')).find(
                (b) => ['sign in', 'next'].includes((b.innerText || '').trim().toLowerCase())
            );
            if (go) go.click();
            """
        )
        # 4. "Stay signed in?" prompt — accept so the session persists.
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            time.sleep(2)
            url = driver.current_url
            if "login.microsoftonline" not in url and "login.live" not in url:
                return True, "signed in"
            driver.execute_script(
                """
                const kmsi = document.querySelector('#idSIButton9, #acceptButton')
                    || Array.from(document.querySelectorAll('button')).find(
                        (b) => (b.innerText || '').trim().toLowerCase() === 'yes'
                    );
                if (kmsi) kmsi.click();
                """
            )
        return False, "sign-in did not settle (MFA prompt?)"

    def open_tabs(self) -> list[dict[str, str]]:
        """Return every open tab (title + URL) for SSO-chain diagnostics."""
        assert self.client.driver is not None
        driver = self.client.driver
        current = driver.current_window_handle
        tabs: list[dict[str, str]] = []
        for handle in driver.window_handles:
            try:
                driver.switch_to.window(handle)
                tabs.append({"title": driver.title[:80], "url": driver.current_url[:120]})
            except Exception:
                continue
        try:
            driver.switch_to.window(current)
        except Exception:
            pass
        return tabs
    def crawl_onenote_web(self, target: str = "") -> dict[str, Any]:
        """Reach OneNote through the working manual path:

        ClassLink LaunchPad → Drives folder → Microsoft 365 tile → Copilot
        shell → waffle (app launcher) → More apps → OneNote. If OneNote asks
        to sign in, click its "Sign in" — the org session SSOs silently;
        otherwise fall back to the full stored-credential form flow.
        """
        trace: list[str] = []

        def note(step: str) -> None:
            trace.append(step)
            logger.info("OneNote crawl: %s", step)

        with self.lock:
            if not self._session_alive():
                self.restart_browser()
            assert self.client.driver is not None
            driver = self.client.driver

            # 1. ClassLink entry — same bootstrap the Canvas auth flow uses.
            if not self._select_classlink_tab():
                return {"status": "error", "message": "ClassLink tab not found"}
            try:
                host = urlsplit(driver.current_url).netloc.lower()
            except Exception:
                host = ""
            if "launchpad.classlink.com" in host or "/login" in driver.current_url:
                note("ClassLink session dead; running Canvas ClassLink sign-in flow")
                try:
                    self.client._sign_in_via_classlink()
                except Exception as exc:
                    return {"status": "needs_manual_sign_in", "location": driver.current_url,
                            "message": f"ClassLink sign-in failed: {exc}"}
                if not self._select_classlink_tab():
                    return {"status": "error", "message": "ClassLink tab not found after sign-in"}
            note("on ClassLink LaunchPad")
            # Always reload the ROOT grid — a folder view (e.g. "LCS
            # Databases & Resources") hides the Drives folder tile.
            driver.get(CLASSLINK_APP_URL)
            time.sleep(5)

            drives = None
            for _ in range(10):
                # "OneDrive" also contains "drive" — exclude it.
                drives = self._find_clickable(driver, ["drives"], exclude=["onedrive"])
                if drives is not None:
                    break
                time.sleep(1)
            if drives is None:
                return {"status": "error", "message": "Drives folder not found on LaunchPad",
                        "path": trace}
            self._click_follow(driver, drives)
            time.sleep(3)
            note("opened Drives")

            # 3. Click the Microsoft 365 tile inside Drives; it opens Copilot
            # in a new tab and federates automatically.
            m365 = None
            for _ in range(10):
                m365 = self._find_clickable(
                    driver,
                    ["microsoft 365", "office 365", "o365", "m365"],
                    exclude=["onedrive", "outlook"],
                )
                if m365 is not None:
                    break
                time.sleep(1)
            if m365 is None:
                return {"status": "error", "message": "Microsoft 365 tile not found in Drives",
                        "path": trace}
            self._click_follow(driver, m365)
            if not self._wait_off_auth_hosts(driver):
                return {"status": "needs_manual_sign_in", "location": driver.current_url,
                        "message": "M365 redirect chain did not settle", "path": trace}
            time.sleep(5)  # let the Copilot/M365 shell render
            note(f"M365 shell loaded at {driver.current_url[:80]}")

            # 4. Waffle (app launcher) → More apps.
            waffle = None
            for _ in range(15):
                waffle = self._find_clickable(
                    driver,
                    ["app launcher", "open the app", "launcher", "waffle"],
                )
                if waffle is not None:
                    break
                time.sleep(2)
            if waffle is None:
                return {"status": "error", "message": "App launcher (waffle) not found",
                        "path": trace}
            # The flyout may fail to open on the first click (animation or
            # wrong node); re-click the waffle and re-search up to 3 rounds.
            more = None
            for _round in range(3):
                self._click_follow(driver, waffle)
                for _ in range(5):
                    more = self._find_clickable(
                        driver,
                        ["more apps", "all apps", "explore all your apps", "all my apps"],
                        exclude=["onenote"],
                    )
                    if more is not None:
                        break
                    time.sleep(2)
                if more is not None:
                    break
            if more is None:
                # Flyout wording varies; the "More apps" link simply leads to
                # the all-apps grid, so go there directly.
                note("flyout 'More apps' not found; opening the apps grid directly")
                driver.get("https://m365.cloud.microsoft/apps")
                time.sleep(6)
            else:
                self._click_follow(driver, more)
                time.sleep(5)  # all-apps grid render
            note("opened More apps")

            # 5. OneNote tile. The grid may launch directly or open a detail
            # pane with an Open button — handle both. Include-match: labels
            # concatenate several attributes, so exact equality never hits.
            onenote = self._find_clickable(driver, ["onenote"])
            if onenote is None:
                return {"status": "error", "message": "OneNote tile not found in More apps",
                        "path": trace}
            self._click_follow(driver, onenote)
            time.sleep(4)
            opener = self._find_clickable(
                driver,
                ["open onenote", "launch onenote", "open in browser", "open"],
                exclude=["app launcher", "launcher"],
            )
            host = urlsplit(driver.current_url).netloc.lower()
            if opener is not None and "onenote.cloud.microsoft" not in host:
                self._click_follow(driver, opener)
            if not self._wait_off_auth_hosts(driver):
                return {"status": "needs_manual_sign_in", "location": driver.current_url,
                        "message": "OneNote launch did not settle", "path": trace}
            time.sleep(8)
            note(f"OneNote opened at {driver.current_url[:80]}")

            # 6. Sign-in gate. The marketing shell shows "Sign in"; clicking
            # it SSOs silently through the org session established above.
            def _anonymous() -> bool:
                return bool(driver.execute_script(
                    """
                    if (location.host.includes('login.microsoftonline')
                        || location.host.includes('login.live')) {
                        return true;  // mid-auth: picker or form page
                    }
                    const body = document.body.innerText || '';
                    const byText = body.toLowerCase().includes('sign in');
                    const byHref = !!document.querySelector(
                        'a[href*="signin"], a[href*="login"], a[data-testid*="signin"]'
                    );
                    return byText || byHref;
                    """
                ))

            if _anonymous():
                note("OneNote anonymous; clicking its Sign in for silent SSO")
                sign_in_btn = self._find_clickable(driver, ["sign in"])
                if sign_in_btn is not None:
                    self._click_follow(driver, sign_in_btn)
                    self._wait_off_auth_hosts(driver, timeout=60)
                    time.sleep(8)
            if _anonymous():
                note("silent SSO insufficient; running stored-credential form flow")
                signed_in, detail = self._microsoft_sign_in()
                if not signed_in:
                    return {
                        "status": "needs_manual_sign_in",
                        "m365_tile_opened": True,
                        "location": driver.current_url,
                        "message": f"Automated M365 sign-in failed: {detail}",
                        "path": trace,
                    }
                time.sleep(5)

            # 7. Optional explicit destination once authenticated.
            if target:
                driver.get(target)
                time.sleep(8)

            discovered = driver.execute_script(
                """
                return Array.from(document.querySelectorAll(
                    'a, button, [role="link"], [role="option"], [data-automationid], [role="row"]'
                )).map((el) => ({
                    title: (el.innerText || el.getAttribute('aria-label') || el.title || '').trim(),
                    url: el.href || ''
                })).filter(n => n.title.length > 2);
                """
            )
            return {
                "status": "authenticated_and_navigated",
                "m365_tile_opened": True,
                "location": driver.current_url,
                "title": driver.title,
                "discovered": discovered[:25],
                "path": trace,
            }

    # ------------------------------------------------------------------
    # OneNote content harvest

    def harvest_onenote(self, notebooks: list[str] | None = None,
                        max_pages: int = 40) -> dict[str, Any]:
        """Walk notebooks → sections → pages in the web app and extract tasks.

        Reaches the signed-in /notebooks view via crawl_onenote_web, then for
        every notebook opens the SharePoint-hosted editor (inside iframe
        #WebApplicationFrame), clicks each section and page, and feeds the
        live page HTML to extract_tasks_from_page.  Ink pages are rendered
        from the live editor (element screenshot) for the vision model.
        Results are written to CACHE_DIR/onenote_page_extractions.json in the
        same {page_key: [tasks]} shape the canvas cache uses, so
        collect_assignments can pick them up.
        """
        import hashlib

        from scrapers.onenote_page_extractor import extract_tasks_from_page

        trace: list[str] = []
        errors: list[str] = []

        def note(msg: str) -> None:
            trace.append(msg)
            logger.info("OneNote harvest: %s", msg)

        try:
            res = self.crawl_onenote_web()
        except Exception as exc:
            logger.warning("harvest crawl failed (%s); relaunching browser once", type(exc).__name__)
            self.restart_browser()
            res = self.crawl_onenote_web()
        if res.get("status") != "authenticated_and_navigated":
            res["message"] = f"could not reach OneNote: {res.get('message', res.get('status'))}"
            return res

        with self.lock:
            assert self.client.driver is not None
            driver = self.client.driver
            # Background threads (Canvas auto-reauth) may have switched tabs
            # while the crawl held the lock; always re-guarantee the grid.
            if not self._ensure_notebooks_view(driver):
                return {"status": "needs_manual_sign_in",
                        "message": "could not reach authenticated notebooks grid"}

            if not notebooks:
                notebooks = self._detect_notebooks(driver)
            if not notebooks:
                return {"status": "error", "message": "no notebooks detected", "path": trace}
            note(f"notebooks: {notebooks}")

            cache_path = config.CACHE_DIR / "onenote_page_extractions.json"
            previous_cache = None
            if cache_path.exists():
                try:
                    previous_cache = json.loads(cache_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    previous_cache = None
            good_before = isinstance(previous_cache, dict) and bool(previous_cache)

            cache_data: dict[str, list[dict]] = {}
            # Scope seen titles per-notebook: within the same notebook (especially
            # Class Notebooks where teacher content is duplicated across student sections),
            # skip duplicate page titles. Scoping per-notebook prevents common titles
            # (e.g. "Unit 1", "Syllabus") in one notebook from colliding with another.
            seen_titles_by_nb: dict[str, set[str]] = {}
            for nb in notebooks:
                nb_seen = {k.rsplit("/", 1)[-1] for k in cache_data if k.startswith(f"{nb}/")}
                if previous_cache:
                    for k in previous_cache:
                        if k.startswith(f"{nb}/") and k.count("/") == 2:
                            nb_seen.add(k.rsplit("/", 1)[-1])
                seen_titles_by_nb[nb] = nb_seen
            pages_scanned = 0
            tasks_total = 0

            for i, nb_name in enumerate(notebooks):
                if pages_scanned >= max_pages:
                    note("page budget reached; stopping")
                    break
                remaining_nbs = len(notebooks) - i
                nb_budget = max(1, (max_pages - pages_scanned) // remaining_nbs)
                seen_titles = seen_titles_by_nb.setdefault(nb_name, set())
                nb_pages_start = pages_scanned
                for attempt in range(3):
                    pages_before = len(cache_data)
                    tasks_before = sum(len(v) for v in cache_data.values())
                    nb_remaining = max(1, nb_budget - (pages_scanned - nb_pages_start))
                    try:
                        stats = self._harvest_notebook(
                            driver, nb_name, cache_data, trace, errors,
                            extract_tasks_from_page,
                            remaining=nb_remaining,
                            seen_titles=seen_titles,
                        )
                        pages_scanned += stats["pages"]
                        tasks_total += stats["tasks"]
                        break
                    except Exception as exc:
                        # Pages harvested before the failure are already in
                        # cache_data — keep them instead of losing the walk.
                        pages_gained = len(cache_data) - pages_before
                        tasks_gained = sum(len(v) for v in cache_data.values()) - tasks_before
                        msg = str(exc).lower()
                        transient = (
                            "discarded" in msg
                            or "nosuchwindow" in msg
                            or "no such window" in msg
                            or "invalid session id" in msg
                            or "no browsable context" in msg
                            or "already closed" in msg
                        )
                        if pages_gained > 0 or tasks_gained > 0:
                            logger.warning(
                                "notebook %s partially harvested: %d pages, %d tasks kept (%s)",
                                nb_name, pages_gained, tasks_gained, exc,
                            )
                            errors.append(
                                f"{nb_name}: partial, kept {pages_gained} pages, {tasks_gained} tasks ({exc})"
                            )
                            pages_scanned += pages_gained
                            tasks_total += tasks_gained
                        else:
                            logger.exception("notebook %s failed (attempt %d)", nb_name, attempt + 1)
                            errors.append(f"{nb_name} (attempt {attempt + 1}): {exc}")
                        # Recover the session, then retry — Firefox discards
                        # tabs nondeterministically under session churn, and
                        # seen_titles makes the retry resume where it died.
                        recovery = self._recover_harvest_session(driver)
                        if recovery == "relaunched":
                            # self.client was swapped; the stale local driver
                            # reference must not be reused.
                            driver = self.client.driver
                            # A fresh browser needs its SSO chain to finish
                            # before the walk can resume; retrying immediately
                            # burns attempts on 120s grid timeouts.
                            if self._wait_for_grid(driver):
                                note("browser relaunched and re-authenticated; retrying notebook")
                            else:
                                note("browser relaunched but grid never re-authenticated; stopping")
                                errors.append("post-relaunch re-auth timeout")
                                break
                        if (pages_gained > 0 or tasks_gained > 0) or recovery == "dead" or not transient or attempt == 2:
                            break

            try:
                config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
                if cache_data:
                    # Merge instead of replace: a session that dies mid-walk
                    # (or a page budget that stops before every notebook)
                    # must not silently drop last-known-good entries this run
                    # never reached.  Keys are notebook/section/page, so a
                    # re-extracted page overwrites its own stale entry.  A
                    # wholly empty harvest (cache_data falsy) still never
                    # overwrites a good cache with "{}".
                    merged = dict(previous_cache) if good_before else {}
                    merged.update(cache_data)
                    cache_path.write_text(json.dumps(merged, indent=1), encoding="utf-8")
                    if good_before and (pages_scanned == 0 or any("partial" in str(e) for e in errors)):
                        note(f"session died mid-harvest; merged {len(cache_data)} "
                             f"partial entries into the cache")
                elif good_before:
                    note("harvest produced 0 pages; keeping the previous cache intact")
                    errors.append("harvest produced 0 pages; kept last-known-good cache")
                # else: nothing harvested and nothing to preserve — no write.
            except OSError as exc:
                errors.append(f"cache write failed: {exc}")

        partial = bool(cache_data and (any("partial" in str(e) for e in errors) or pages_scanned == 0))
        result = {
            "status": "ok" if tasks_total or pages_scanned or cache_data else "empty",
            "pages_scanned": pages_scanned,
            "tasks_extracted": tasks_total,
            "notebooks": notebooks,
            "cache": str(cache_path),
            "errors": errors,
            "path": trace,
        }
        if partial:
            result["partial"] = True
        return result

    def _recover_harvest_session(self, driver) -> str:
        """Best-effort recovery after a notebook harvest failure.

        Must be called while holding self.lock (harvest_onenote's `with`).
        Returns "alive" when the existing session is usable again,
        "relaunched" when the browser was swapped (caller must re-read
        self.client.driver), and "dead" when recovery failed.
        """
        if self._session_alive():
            try:
                self._ensure_notebooks_view(driver)
                return "alive"
            except Exception:
                pass
        logger.warning("harvest session dead — relaunching Firefox")
        try:
            self.restart_browser()
            return "relaunched"
        except Exception:
            logger.exception("browser relaunch during harvest failed")
            return "dead"

    def _wait_for_grid(self, driver, budget: float = 420.0) -> bool:
        """Wait for a freshly relaunched browser to re-authenticate.

        A relaunch drops the session; the ClassLink → ADFS → OneNote SSO
        chain takes tens of seconds to minutes.  Poll the notebooks grid
        until it is authenticated or the time budget is exhausted.
        """
        deadline = time.monotonic() + budget
        while time.monotonic() < deadline:
            try:
                if self._ensure_notebooks_view(driver):
                    return True
            except Exception:
                pass
            time.sleep(20)
        return False

    def _detect_notebooks(self, driver) -> list[str]:
        """Notebook names from ONENOTE_NOTEBOOKS, else auto-detect tiles."""
        configured = get_setting("ONENOTE_NOTEBOOKS", "")
        if configured:
            return [n.strip() for n in configured.split(",") if n.strip()]
        return driver.execute_script(
            """
            const seen = new Set();
            for (const el of document.querySelectorAll('div, a')) {
                const t = (el.textContent || '').trim();
                if (t.length < 5 || t.length > 70) continue;
                if (!el.querySelector('img, svg')) continue;
                if (el.querySelector('div, a')) {
                    // keep only leafmost labelled cards
                    const inner = Array.from(el.querySelectorAll('div, a'))
                        .some((c) => { const ct=(c.textContent||'').trim();
                                       return ct.length>=5 && ct.length<=70 && c.querySelector('img, svg'); });
                    if (inner) continue;
                }
                seen.add(t);
            }
            return Array.from(seen);
            """
        ) or []

    def _authenticated_grid(self, driver) -> bool:
        """True when the active tab shows a usable notebooks grid.

        The signed-in shell still contains stray "Sign in" strings (header
        overflow), so text-probing for them is unreliable; the configured
        notebook names are the strongest signal, with marketing-page
        markers as the negative check.
        """
        try:
            url = driver.current_url.lower()
            body = (driver.execute_script(
                "return document.body ? document.body.innerText : '';") or "").lower()
        except Exception:
            return False
        if "onenote.cloud.microsoft" not in url:
            return False
        names = [n.strip().lower() for n in (get_setting("ONENOTE_NOTEBOOKS", "") or "").split(",") if n.strip()]
        if names:
            return any(n in body for n in names)
        return ("all notebooks" in body or "recent" in body) and "see plans & pricing" not in body

    # ------------------------------------------------------------------
    # Editor-frame resilience.  OneNote's web app RECREATES the
    # WebApplicationFrame iframe after section/page clicks; any Selenium
    # call parked on the old context then throws "Browsing context has been
    # discarded" even though every tab is alive.  Re-anchor instead of
    # declaring the session dead.

    @staticmethod
    def _focus_live_tab(driver) -> bool:
        """Switch onto any readable tab after the parked context is orphaned.

        Prioritizes SharePoint/editor tabs if still open.
        """
        try:
            handles = list(driver.window_handles)
        except Exception:
            return False
        # Prioritize SharePoint/editor tabs
        for handle in handles:
            try:
                driver.switch_to.window(handle)
                url = (driver.current_url or "").lower()
                if "sharepoint.com" in url and "doc" in url:
                    return True
            except Exception:
                continue
        # Fall back to any readable tab
        for handle in handles:
            try:
                driver.switch_to.window(handle)
                _ = driver.current_url
                return True
            except Exception:
                continue
        return False

    @staticmethod
    def _reanchor_editor(driver) -> bool:
        """Re-enter the editor iframe after OneNote rebuilds it."""
        try:
            driver.switch_to.default_content()
        except Exception:
            if not BrowserDaemon._focus_live_tab(driver):
                return False
            try:
                driver.switch_to.default_content()
            except Exception:
                return False
        try:
            frame_el = driver.find_element("id", "WebApplicationFrame")
            driver.switch_to.frame(frame_el)
            return True
        except Exception:
            return False

    def _editor_js(self, driver, script: str, *args, tries: int = 4):
        """execute_script inside the editor, tolerating iframe rebuilds."""
        last: Exception | None = None
        for _ in range(tries):
            try:
                return driver.execute_script(script, *args)
            except Exception as exc:
                last = exc
                msg = str(exc).lower()
                if ("discarded" in msg or "no browsable context" in msg
                        or "NoSuchWindowException" in type(exc).__name__):
                    if not self._reanchor_editor(driver):
                        time.sleep(3)
                    continue
                raise
        assert last is not None
        raise last

    def _ensure_notebooks_view(self, driver) -> bool:
        """Guarantee the active tab sits on an AUTHENTICATED /notebooks grid.

        A cold navigation to /notebooks can land on the anonymous marketing
        shell (the app reports APPHOME-WEB.UNAUTH); clicking its "Sign in"
        then SSOs silently through the org session.  So never trust the
        URL — verify the grid content and drive the sign-in gate whenever
        needed.  Also closes stale SharePoint editor tabs, which self-close
        or get discarded and poison later handle switches.
        """
        try:
            driver.switch_to.default_content()
        except Exception:
            # The parked context may be an iframe OneNote has since rebuilt;
            # re-anchor onto any live tab before scanning handles.
            if not self._focus_live_tab(driver):
                raise
            driver.switch_to.default_content()
        keep: list[tuple[str, str]] = []
        for handle in list(driver.window_handles):
            try:
                driver.switch_to.window(handle)
                url = driver.current_url.lower()
            except Exception:
                continue  # already discarded
            # Stale editors AND heavyweight M365/Copilot SPAs get closed:
            # this machine discards tabs under memory pressure, and each
            # discarded context poisons the Selenium session.
            heavy = ("sharepoint.com", "m365.cloud.microsoft", "www.office.com",
                     "word.cloud.microsoft", "excel.cloud.microsoft",
                     "powerpoint.cloud.microsoft", "copilot.microsoft.com")
            if any(h in url for h in heavy):
                try:
                    driver.close()
                except Exception:
                    pass
            else:
                keep.append((handle, url))

        for handle, _url in keep:
            try:
                driver.switch_to.window(handle)
            except Exception:
                continue
            if self._authenticated_grid(driver):
                return True

        deadline = time.monotonic() + 120
        form_attempts = 0
        while time.monotonic() < deadline:
            try:
                url = driver.current_url.lower()
                if "onenote.cloud.microsoft" not in url and "login." not in url:
                    driver.get("https://onenote.cloud.microsoft/notebooks")
                    time.sleep(6)
                elif self._authenticated_grid(driver):
                    return True
                elif url.startswith("https://onenote.cloud.microsoft") and not self._onenote_midauth(url):
                    # Marketing/anonymous shell: click its Sign in for a
                    # silent SSO through the existing org session.
                    btn = self._find_clickable(driver, ["sign in"])
                    if btn is not None:
                        self._click_follow(driver, btn)
                        self._wait_off_auth_hosts(driver, timeout=60)
                        time.sleep(6)
                    else:
                        driver.get("https://onenote.cloud.microsoft/notebooks")
                        time.sleep(6)
                elif self._onenote_midauth(url) and form_attempts < 2:
                    # Stuck on the login picker/form: the silent SSO through
                    # the org cookie never lands once the M365 session has
                    # expired — the redirect this loop used to wait for will
                    # not come.  Complete the stored-credential form flow
                    # (picker tile → UPN → ADFS password → stay signed in).
                    form_attempts += 1
                    try:
                        if self._microsoft_sign_in()[0]:
                            time.sleep(6)
                    except Exception:
                        logger.exception("credential sign-in during notebooks recovery failed")
                    time.sleep(4)
                # else: mid-auth after exhausting form attempts — keep waiting
            except Exception:
                time.sleep(3)
        return False

    @staticmethod
    def _onenote_midauth(url: str) -> bool:
        return "login.microsoftonline" in url or "login.live" in url
    def _harvest_notebook(self, driver, nb_name: str, cache_data: dict,
                          trace: list[str], errors: list[str],
                          extract_fn, remaining: int,
                          seen_titles: set[str] | None = None) -> dict[str, int]:
        """Open one notebook and harvest every section's pages."""
        import hashlib

        def note(msg: str) -> None:
            # Mirror into the journal: the HTTP response dies whenever the
            # triggering client times out, and the trace must survive that.
            trace.append(msg)
            logger.info("OneNote harvest: %s", msg)

        driver.switch_to.default_content()
        if not self._ensure_notebooks_view(driver):
            raise RuntimeError("could not reach authenticated notebooks grid")
        time.sleep(3)

        # Click the notebook card: the deepest exact-text node carries the
        # click handler.
        clicked = None
        for _ in range(6):
            clicked = driver.execute_script(
                """
                const want = arguments[0].toLowerCase();
                const cands = Array.from(document.querySelectorAll('div, a'))
                    .filter((el) => (el.textContent || '').trim().toLowerCase() === want);
                if (!cands.length) return false;
                cands[cands.length - 1].click();
                return true;
                """,
                nb_name,
            )
            if clicked:
                break
            time.sleep(2)
        if not clicked:
            raise RuntimeError(f"notebook tile not found (at {driver.current_url[:80]})")

        # Wait for the editor tab. OneNote may open a NEW tab or focus an
        # existing one (singleton per notebook), so scan every handle by URL
        # and title instead of only watching for fresh handles.
        deadline = time.monotonic() + 75
        found_editor = False
        while time.monotonic() < deadline and not found_editor:
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    url = driver.current_url.lower()
                    title = (driver.title or "").lower()
                except Exception:
                    continue
                if ("sharepoint.com" in url and "doc.aspx" in url) or nb_name.lower() in title:
                    found_editor = True
                    break
            if not found_editor:
                time.sleep(2)
        if not found_editor:
            raise RuntimeError("editor tab never opened")

        driver.switch_to.default_content()
        frame_el = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and frame_el is None:
            try:
                frame_el = driver.find_element("id", "WebApplicationFrame")
            except Exception:
                time.sleep(2)
        if frame_el is None:
            raise RuntimeError("WebApplicationFrame never appeared")
        driver.switch_to.frame(frame_el)

        # Cold SharePoint loads can take >40s before the section rail
        # renders; give it a full minute before declaring the notebook empty.
        # Poll group expansion and leaf section discovery until sections are found
        # or the deadline expires.
        deadline = time.monotonic() + 60
        total_expanded = 0
        sections: list[str] = []

        while time.monotonic() < deadline:
            # Class Notebooks nest sections inside collapsed section groups
            # ("_Content Library", per-student spaces, unit resources, etc.).
            # Handle section groups (role="treeitem" with child containers / aria-expanded):
            # clicking each group toggles aria-expanded="true" and recurses into nested child sections.
            for _pass in range(4):
                expanded = self._editor_js(
                    driver,
                    """
                    const isGroup = (el) => {
                        if (!el) return false;
                        if (el.hasAttribute('aria-expanded') || el.getAttribute('aria-expanded') !== null) return true;
                        const label = (el.getAttribute('aria-label') || '').toLowerCase();
                        if (label.includes('section group')) return true;
                        const cls = (el.className || '').toString().toLowerCase();
                        if (cls.includes('sectiongroup') || cls.includes('groupitemwrap')) return true;
                        if (el.getAttribute('role') === 'treeitem') {
                            if (el.querySelector('[role="group"], [class*="childContainer" i], [class*="groupItems" i], [class*="chevron" i], [class*="expander" i]')) return true;
                            const next = el.nextElementSibling;
                            if (next && next.getAttribute('role') === 'group') return true;
                        }
                        return false;
                    };
                    const candidates = Array.from(document.querySelectorAll(
                        '[role="treeitem"], .sectionListItem, [aria-label*="Section Group" i], [class*="sectionGroup"]'
                    ));
                    let count = 0;
                    const seen = new Set();
                    for (const el of candidates) {
                        if (!isGroup(el)) continue;
                        if (seen.has(el)) continue;
                        seen.add(el);
                        if (el.getAttribute('aria-expanded') === 'false') {
                            const target = el.querySelector('[class*="chevron" i], [class*="expander" i], [data-icon-name*="Chevron" i], [aria-expanded]') || el;
                            const targets = [target, ...Array.from(target.querySelectorAll('*'))];
                            const opts = {bubbles: true, cancelable: true, view: window};
                            for (const t of targets) {
                                t.dispatchEvent(new MouseEvent('mousedown', opts));
                                t.dispatchEvent(new MouseEvent('mouseup', opts));
                                t.dispatchEvent(new MouseEvent('click', opts));
                            }
                            count++;
                        }
                    }
                    return count;
                    """
                ) or 0
                if not expanded:
                    break
                total_expanded += expanded
                time.sleep(2)

            # Query only leaf sections — never section group headers.
            sections = self._editor_js(
                driver,
                """
                const isGroup = (el) => {
                    if (!el) return false;
                    if (el.hasAttribute('aria-expanded') || el.getAttribute('aria-expanded') !== null) return true;
                    const label = (el.getAttribute('aria-label') || '').toLowerCase();
                    if (label.includes('section group')) return true;
                    const cls = (el.className || '').toString().toLowerCase();
                    if (cls.includes('sectiongroup') || cls.includes('groupitemwrap')) return true;
                    if (el.getAttribute('role') === 'treeitem') {
                        if (el.querySelector('[role="group"], [class*="childContainer" i], [class*="groupItems" i], [class*="chevron" i], [class*="expander" i]')) return true;
                        const next = el.nextElementSibling;
                        if (next && next.getAttribute('role') === 'group') return true;
                    }
                    return false;
                };
                const els = Array.from(document.querySelectorAll('.sectionListItem, [role="treeitem"]'));
                const leaves = [];
                const seen = new Set();
                for (const el of els) {
                    if (isGroup(el)) continue;  // Never treat section group headers as leaf sections
                    const name = ((el.querySelector('content') || {}).textContent || el.innerText || '').trim();
                    if (!name || name.length < 2 || seen.has(name)) continue;
                    seen.add(name);
                    leaves.push(name);
                }
                return leaves;
                """
            ) or []

            if sections:
                break
            time.sleep(3)

        if total_expanded:
            trace.append(f"{nb_name}: expanded {total_expanded} section group(s)")
            note(f"{nb_name}: expanded {total_expanded} section group(s)")

        trace.append(f"{nb_name}: sections {sections}")
        note(f"{nb_name}: sections {sections}")

        pages_done = 0
        tasks_done = 0

        def _snapshot(_page, _html):
            last: Exception | None = None
            for _ in range(3):
                try:
                    panel = driver.find_element("css selector", "#WACViewPanel")
                    return panel.screenshot_as_png
                except Exception as exc:  # iframe rebuilt under us
                    last = exc
                    if not self._reanchor_editor(driver):
                        time.sleep(3)
            assert last is not None
            raise last

        for sec in sections:
            if pages_done >= remaining:
                break
            try:
                sec_el = self._editor_js(
                    driver,
                    """
                    const want = arguments[0];
                    const isGroup = (el) => {
                        if (!el) return false;
                        if (el.hasAttribute('aria-expanded') || el.getAttribute('aria-expanded') !== null) return true;
                        const label = (el.getAttribute('aria-label') || '').toLowerCase();
                        if (label.includes('section group')) return true;
                        const cls = (el.className || '').toString().toLowerCase();
                        if (cls.includes('sectiongroup') || cls.includes('groupitemwrap')) return true;
                        if (el.getAttribute('role') === 'treeitem') {
                            if (el.querySelector('[role="group"], [class*="childContainer" i], [class*="groupItems" i], [class*="chevron" i], [class*="expander" i]')) return true;
                            const next = el.nextElementSibling;
                            if (next && next.getAttribute('role') === 'group') return true;
                        }
                        return false;
                    };
                    const els = Array.from(document.querySelectorAll('.sectionListItem, [role="treeitem"]'));
                    const hit = els.find(e => !isGroup(e) && (((e.querySelector('content') || {}).textContent || e.innerText || '').trim() === want));
                    if (!hit) return false;
                    // Fabric trees select on mousedown; a bare .click() can
                    // succeed without selecting (2026-09-06 Biology probe).
                    const targets = [hit, ...Array.from(hit.querySelectorAll('*'))];
                    const opts = {bubbles: true, cancelable: true, view: window};
                    for (const t of targets) {
                        t.dispatchEvent(new MouseEvent('mousedown', opts));
                        t.dispatchEvent(new MouseEvent('mouseup', opts));
                        t.dispatchEvent(new MouseEvent('click', opts));
                    }
                    return true;
                    """,
                    sec,
                )
                if not sec_el:
                    errors.append(f"{nb_name}/{sec}: section click failed")
                    continue
                time.sleep(2)
                deadline = time.monotonic() + 10  # 10s maximum timeout on page list queries
                while time.monotonic() < deadline:
                    if self._editor_js(driver,
                                       "return document.querySelectorAll('.pageListItem').length;"):
                        break
                    time.sleep(2)
                else:
                    # Fallback: keyboard activation (probe strategy C).
                    self._editor_js(
                        driver,
                        """
                        const want = arguments[0];
                        const els = Array.from(document.querySelectorAll('.sectionListItem, [role="treeitem"]'));
                        const s = els.find(e => (((e.querySelector('content') || {}).textContent || e.innerText || '').trim() === want));
                        if (!s) return 'not-found';
                        s.focus();
                        s.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', bubbles: true, cancelable: true}));
                        s.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', code: 'Enter', bubbles: true, cancelable: true}));
                        return 'enter dispatched';
                        """,
                        sec,
                    )
                    deadline = time.monotonic() + 6
                    while time.monotonic() < deadline:
                        if self._editor_js(driver,
                                           "return document.querySelectorAll('.pageListItem').length;"):
                            break
                        time.sleep(2)

                pages = self._editor_js(
                    driver,
                    "return Array.from(document.querySelectorAll('.pageListItem'))"
                    ".map(e => (e.innerText||'').trim()).filter(t => t.length > 0);"
                ) or []

                for pg in pages:
                    if pages_done >= remaining:
                        break
                    if seen_titles and pg in seen_titles:
                        continue  # same shared notebook page in another section
                    try:
                        hit = self._editor_js(
                            driver,
                            """
                            const want = arguments[0];
                            const els = Array.from(document.querySelectorAll('.pageListItem'));
                            const p = els.find(e => (e.innerText||'').trim() === want);
                            if (!p) return false;
                            const targets = [p, ...Array.from(p.querySelectorAll('*'))];
                            const opts = {bubbles: true, cancelable: true, view: window};
                            for (const t of targets) {
                                t.dispatchEvent(new MouseEvent('mousedown', opts));
                                t.dispatchEvent(new MouseEvent('mouseup', opts));
                                t.dispatchEvent(new MouseEvent('click', opts));
                            }
                            return true;
                            """,
                            pg,
                        )
                        if not hit:
                            continue
                        time.sleep(3)  # let the page canvas render
                        html = self._editor_js(
                            driver,
                            "const p = document.querySelector('#WACViewPanel');"
                            "return p ? p.outerHTML : '';"
                        )
                        if not html:
                            continue
                        page_id = hashlib.md5(f"{nb_name}|{sec}|{pg}".encode()).hexdigest()[:12]
                        page_meta = {"id": page_id, "title": pg, "links": {}}
                        tasks = extract_fn(page_meta, html, render_snapshot=_snapshot)
                        # Retain the reading-order text as markdown so the
                        # embedding indexer can make the notebook searchable
                        # (Phase 1 RAG).  Ink-only pages yield no text here;
                        # ink transcription is the Phase 3 pipeline.
                        try:
                            from scrapers.onenote_page_extractor import parse_spatial_layout, strip_page_header_lines
                            from scrapers.onenote_web_scraper import save_harvested_page

                            text = parse_spatial_layout(html)
                            clean_text = strip_page_header_lines(text, pg) or text
                            if clean_text:
                                save_harvested_page(nb_name, sec, pg, clean_text)
                        except Exception as exc:
                            errors.append(f"{nb_name}/{sec}/{pg}: retention failed ({exc})")
                        for t in tasks:
                            t["course"] = nb_name
                        cache_data[f"{nb_name}/{sec}/{pg}"] = tasks
                        if seen_titles is not None:
                            seen_titles.add(pg)
                        pages_done += 1
                        tasks_done += len(tasks)
                        trace.append(f"  {nb_name}/{sec}/{pg}: {len(tasks)} tasks")
                        note(f"{nb_name}/{sec}/{pg}: {len(tasks)} tasks")
                    except Exception as exc:
                        errors.append(f"{nb_name}/{sec}/{pg}: {exc}")
            except Exception as exc:
                errors.append(f"{nb_name}/{sec}: {exc}")

        # Close the editor tab and go back to the list for the next notebook.
        # The parked context may be an orphaned iframe; find the editor tab by
        # URL instead of trusting the current switch, then re-anchor on the
        # notebooks grid.
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        editor_closed = False
        for handle in list(driver.window_handles):
            try:
                driver.switch_to.window(handle)
                url = driver.current_url.lower()
            except Exception:
                continue  # discarded handle — skip it
            if "sharepoint.com" in url and "doc.aspx" in url:
                try:
                    driver.close()
                    editor_closed = True
                except Exception:
                    pass
                break
        if not editor_closed:
            self._focus_live_tab(driver)
        self._ensure_notebooks_view(driver)
        trace.append(f"{nb_name}: {pages_done} pages, {tasks_done} tasks")
        note(f"{nb_name}: {pages_done} pages, {tasks_done} tasks")
        return {"pages": pages_done, "tasks": tasks_done}

    def run_js(self, expr: str, tab: str = "", frame: str = ""):
        """Run JS in a tab (diagnostics only); ``tab`` matches URL/title."""
        with self.lock:
            assert self.client.driver is not None
            driver = self.client.driver
            if tab:
                found = False
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    if tab.lower() in driver.current_url.lower() or tab.lower() in driver.title.lower():
                        found = True
                        break
                if not found:
                    raise LookupError(f"no tab matching {tab!r}")
            if frame:
                def _find_frame(d, fid, depth=0):
                    try:
                        for f in d.find_elements("tag name", "iframe"):
                            if (f.get_attribute("id") or "") == fid or (f.get_attribute("name") or "") == fid:
                                d.switch_to.frame(f)
                                return True
                            try:
                                d.switch_to.frame(f)
                            except Exception:
                                continue
                            if depth < 3 and _find_frame(d, fid, depth + 1):
                                return True
                            d.switch_to.default_content()
                            # restore outer chain on failure
                    except Exception:
                        pass
                    return False

                driver.switch_to.default_content()
                if not _find_frame(driver, frame):
                    raise LookupError(f"no iframe matching {frame!r}")
            else:
                driver.switch_to.default_content()
            return driver.execute_script(expr)

    def screenshot(self, tab: str = "", frame: str = "",
                   selector: str = "") -> bytes:
        """PNG of a page element (or the viewport) — diagnostics."""
        with self.lock:
            assert self.client.driver is not None
            driver = self.client.driver
            self.run_js("return true;", tab=tab, frame=frame)
            if selector:
                el = driver.find_element("css selector", selector)
                return el.screenshot_as_png
            return driver.get_screenshot_as_png()

    def close(self) -> None:
        self.client.close()


class DaemonHandler(BaseHTTPRequestHandler):
    server: "CanvasDaemonServer"

    def do_GET(self) -> None:  # noqa: N802
        route = urlsplit(self.path)
        if route.path == "/health":
            self._send(200, self.server.daemon.health())
            return
        if route.path == "/js":
            # Localhost-only diagnostic: run JS in the active tab to explore
            # SPA DOM (OneNote editor structure) during crawler development.
            try:
                expr = parse_qs(route.query).get("expr", [""])[0]
                tab = parse_qs(route.query).get("tab", [""])[0]
                frame = parse_qs(route.query).get("frame", [""])[0]
                if not expr:
                    self._send(400, {"error": "expr required"})
                    return
                res = self.server.daemon.run_js(expr, tab=tab, frame=frame)
                self._send(200, {"result": repr(res)[:4000]})
            except Exception as exc:
                logger.exception("JS debug failed")
                self._send(500, {"error": str(exc)})
            return
        if route.path == "/onenote/crawl":
            try:
                target = parse_qs(route.query).get("target", [""])[0]
                if target and not urlsplit(target).netloc.lower().endswith(
                    (".microsoft.com", ".cloud.microsoft", ".microsoft", ".office.com", ".onenote.com", ".sharepoint.com")
                ):
                    self._send(400, {"error": "target must be a Microsoft domain"})
                    return
                res = self.server.daemon.crawl_onenote_web(target=target)
                # Diagnostic: report every open tab so tab-mechanics bugs in
                # the SSO chain are visible from the outside.
                res["tabs"] = self.server.daemon.open_tabs()
                self._send(200, res)
            except Exception as exc:
                logger.exception("OneNote web crawl failed")
                self._send(500, {"error": str(exc)})
            return
        if route.path == "/onenote/harvest":
            try:
                qs = parse_qs(route.query)
                notebooks = [n for n in qs.get("notebooks", [""])[0].split(",") if n.strip()] or None
                max_pages = int(qs.get("max_pages", ["40"])[0])
                res = self.server.daemon.harvest_onenote(notebooks=notebooks, max_pages=max_pages)
                self._send(200, res)
            except Exception as exc:
                logger.exception("OneNote harvest failed")
                self._send(500, {"error": str(exc)})
            return
        if route.path == "/screenshot":
            try:
                qs = parse_qs(route.query)
                png = self.server.daemon.screenshot(
                    tab=qs.get("tab", [""])[0],
                    frame=qs.get("frame", [""])[0],
                    selector=qs.get("selector", [""])[0],
                )
                self._send(200, {"png_b64": base64.b64encode(png).decode()})
            except Exception as exc:
                logger.exception("Screenshot failed")
                self._send(500, {"error": str(exc)})
            return
        if route.path == "/apps":
            try:
                self._send(200, self.server.daemon.list_classlink_apps())
            except CanvasSignInRequired as exc:
                self._send(401, {"error": str(exc)})
            except Exception:
                logger.exception("ClassLink app listing failed")
                self._send(500, {"error": "Could not list ClassLink apps."})
            return
        if route.path == "/request":
            value = parse_qs(route.query).get("path", [""])[0]
            try:
                data, link = self.server.daemon.request(value)
            except CanvasSignInRequired as exc:
                self._send(401, {"error": str(exc)})
            except CanvasSessionError as exc:
                self._send(400, {"error": str(exc)})
            except Exception:
                logger.exception("Canvas browser request failed")
                self._send(500, {"error": "Canvas browser request failed."})
            else:
                self._send(200, {"data": data, "link": link})
            return
        if route.path == "/download":
            file_id = parse_qs(route.query).get("file_id", [""])[0]
            try:
                content, content_type, filename = self.server.daemon.download_canvas_file(file_id)
            except CanvasSignInRequired as exc:
                self._send(401, {"error": str(exc)})
            except CanvasSessionError as exc:
                self._send(400, {"error": str(exc)})
            except Exception:
                logger.exception("Canvas file download failed")
                self._send(500, {"error": "Canvas file download failed."})
            else:
                self._send_binary(200, content, content_type, filename)
            return
        self._send(404, {"error": "Not found."})

    def _send(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_binary(self, status: int, body: bytes, content_type: str, filename: str) -> None:
        safe_filename = filename.replace('"', "'").replace("\r", "").replace("\n", "")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{safe_filename}"')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class CanvasDaemonServer(ThreadingHTTPServer):
    daemon: BrowserDaemon


def monitor_session(daemon: BrowserDaemon, stop_event: threading.Event) -> None:
    """Check the live browser periodically without blocking local scraper requests."""
    interval = max(60, int(get_setting("CANVAS_REAUTH_CHECK_SECONDS", "300")))
    while not stop_event.wait(interval):
        try:
            if not daemon.health().get("authenticated"):
                daemon.auto_reauthenticate()
        except Exception:
            logger.exception("Canvas session monitor failed")


def main() -> None:
    display = VirtualDisplay()
    display.start()
    daemon = BrowserDaemon()
    daemon.start()
    server = CanvasDaemonServer(("127.0.0.1", 8976), DaemonHandler)
    server.daemon = daemon
    logger.info("Canvas browser daemon listening on 127.0.0.1:8976 and beginning automatic ClassLink sign-in.")
    stop_event = threading.Event()
    initial_auth = threading.Thread(target=daemon.auto_reauthenticate, daemon=True)
    initial_auth.start()
    monitor = threading.Thread(target=monitor_session, args=(daemon, stop_event), daemon=True)
    monitor.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping Canvas browser daemon")
    finally:
        stop_event.set()
        server.server_close()
        daemon.close()
        display.close()


if __name__ == "__main__":
    main()
