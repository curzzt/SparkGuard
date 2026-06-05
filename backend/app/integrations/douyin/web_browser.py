import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DOUYIN_HOME = "https://www.douyin.com/"
DOUYIN_MESSAGE = "https://www.douyin.com/message"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class QrStartResult:
    qrcode_base64: str
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page
    already_logged_in: bool = False
    storage_state: dict | None = None
    profile: dict | None = None


@dataclass
class QrPollResult:
    status: str
    storage_state: dict | None = None
    profile: dict | None = None
    error_message: str | None = None


@dataclass
class SendDmResult:
    success: bool
    error_message: str | None = None
    screenshot_base64: str | None = None


def _headless() -> bool:
    return get_settings().PLAYWRIGHT_HEADLESS


def _new_context(playwright: Playwright, storage_state: dict | None = None) -> tuple[Browser, BrowserContext]:
    browser = playwright.chromium.launch(headless=_headless())
    kwargs: dict[str, Any] = {
        "viewport": {"width": 1280, "height": 800},
        "user_agent": USER_AGENT,
        "locale": "zh-CN",
    }
    if storage_state:
        kwargs["storage_state"] = storage_state
    context = browser.new_context(**kwargs)
    return browser, context


def _is_logged_in(page: Page) -> bool:
    cookies = page.context.cookies()
    names = {c.get("name", "") for c in cookies}
    if "sessionid" in names or "sid_tt" in names:
        return True
    login_hints = ["登录", "扫码登录", "验证码登录"]
    for hint in login_hints:
        try:
            if page.get_by_text(hint, exact=False).first.is_visible(timeout=800):
                return False
        except Exception:
            continue
    try:
        if page.locator('[data-e2e="user-avatar"], header img, .avatar').first.is_visible(timeout=2000):
            return True
    except Exception:
        pass
    return False


def _extract_profile(page: Page) -> dict:
    nickname = None
    avatar_url = None
    for sel in ('[data-e2e="user-name"]', 'header [class*="name"]', '.account-name'):
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                nickname = (el.inner_text() or "").strip() or None
                if nickname:
                    break
        except Exception:
            continue
    try:
        img = page.locator('[data-e2e="user-avatar"] img, header img').first
        if img.is_visible(timeout=1500):
            avatar_url = img.get_attribute("src")
    except Exception:
        pass
    uid = f"web_{int(time.time())}"
    for c in page.context.cookies():
        if c.get("name") == "uid_tt" and c.get("value"):
            uid = f"web_{c['value'][:32]}"
            break
    return {"open_id": uid, "nickname": nickname or "抖音用户", "avatar_url": avatar_url}


def _login_panel(page: Page):
    panel = page.locator('[id^="login-full-panel"]')
    if panel.count():
        return panel.first
    return page.locator("body")


def _open_login_qrcode_panel(page: Page) -> None:
    panel = _login_panel(page)
    try:
        if not panel.is_visible(timeout=1500):
            for text in ("登录",):
                btn = page.get_by_text(text, exact=False).first
                if btn.is_visible(timeout=2000):
                    btn.click(force=True)
                    page.wait_for_timeout(1500)
                    logger.info("douyin_qr: clicked %s to open login panel", text)
                    break
    except Exception as exc:
        logger.warning("douyin_qr: open login panel failed: %s", exc)

    for text in ("扫码登录", "扫码"):
        try:
            tab = page.get_by_text(text, exact=False).first
            if tab.is_visible(timeout=2500):
                tab.click(force=True)
                page.wait_for_timeout(2000)
                logger.info("douyin_qr: switched login tab to %s", text)
                return
        except Exception as exc:
            logger.warning("douyin_qr: switch tab %s failed: %s", text, exc)


def _is_square_qr_box(box: dict) -> bool:
    w = box.get("width") or 0
    h = box.get("height") or 0
    if w < 120 or h < 120:
        return False
    ratio = w / h if h else 0
    return 0.75 <= ratio <= 1.33


def _capture_qrcode_image(page: Page) -> tuple[str, dict]:
    _open_login_qrcode_panel(page)
    scope = _login_panel(page)
    element_selectors = (
        'img[alt*="二维码"]',
        'img[src*="qrcode"]',
        '[class*="qrcode"] img',
        "canvas",
        "img",
    )
    candidates: list[tuple[float, object, str, int, dict]] = []
    for sel in element_selectors:
        loc = scope.locator(sel)
        count = loc.count()
        for i in range(count):
            el = loc.nth(i)
            try:
                if not el.is_visible(timeout=800):
                    continue
                box = el.bounding_box()
                if not box or not _is_square_qr_box(box):
                    continue
                area = box["width"] * box["height"]
                square_penalty = abs(box["width"] - box["height"])
                score = area - square_penalty * 10
                candidates.append((score, el, sel, i, box))
            except Exception:
                continue

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        score, el, sel, index, box = candidates[0]
        data = el.screenshot()
        meta = {
            "selector": sel,
            "index": index,
            "box": box,
            "bytes": len(data),
            "score": score,
        }
        logger.info("douyin_qr: captured element %s", meta)
        return base64.b64encode(data).decode(), meta

    logger.warning("douyin_qr: no square qr element, fallback to login panel screenshot")
    try:
        data = scope.screenshot()
        return base64.b64encode(data).decode(), {"fallback": "login_panel"}
    except Exception:
        data = page.screenshot(full_page=False)
        return base64.b64encode(data).decode(), {"fallback": "full_page"}


def _click_im_entry(page: Page) -> bool:
    for sel in ('text=私信', '[data-e2e="im-entry"]', 'a:has-text("私信")'):
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=4000):
                loc.click()
                page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    try:
        page.goto(DOUYIN_MESSAGE, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        return True
    except Exception:
        return False


def _send_in_chat(page: Page, message: str) -> None:
    for sel in (
        'div[contenteditable="true"]',
        "textarea",
        '[placeholder*="发送"]',
        '[placeholder*="消息"]',
        '[data-e2e="chat-input"]',
    ):
        try:
            inp = page.locator(sel).last
            if inp.is_visible(timeout=4000):
                inp.click()
                inp.fill(message)
                page.keyboard.press("Enter")
                page.wait_for_timeout(1200)
                return
        except Exception:
            continue
    raise RuntimeError("未找到私信输入框")


def start_qr_login_sync() -> QrStartResult:
    playwright = sync_playwright().start()
    browser, context = _new_context(playwright)
    page = context.new_page()
    logger.info("douyin_qr: navigating to %s headless=%s", DOUYIN_HOME, _headless())
    page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    logger.info("douyin_qr: landed url=%s title=%s", page.url, page.title())

    if _is_logged_in(page):
        logger.info("douyin_qr: already logged in")
        state = context.storage_state()
        profile = _extract_profile(page)
        return QrStartResult(
            qrcode_base64="",
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
            already_logged_in=True,
            storage_state=state,
            profile=profile,
        )

    qrcode_b64, meta = _capture_qrcode_image(page)
    if not qrcode_b64:
        logger.error("douyin_qr: empty qrcode capture meta=%s", meta)
        raise RuntimeError("未能截取登录二维码")
    try:
        raw = base64.b64decode(qrcode_b64)
        if len(raw) < 3000:
            logger.warning("douyin_qr: suspicious small image bytes=%s meta=%s", len(raw), meta)
    except Exception as exc:
        logger.warning("douyin_qr: invalid base64 payload: %s", exc)

    return QrStartResult(
        qrcode_base64=qrcode_b64,
        playwright=playwright,
        browser=browser,
        context=context,
        page=page,
    )


def poll_qr_login_sync(page: Page) -> QrPollResult:
    try:
        if page.locator('text=已扫描').first.is_visible(timeout=500):
            return QrPollResult(status="scanned")
    except Exception:
        pass

    if _is_logged_in(page):
        state = page.context.storage_state()
        profile = _extract_profile(page)
        return QrPollResult(status="confirmed", storage_state=state, profile=profile)

    return QrPollResult(status="pending")


def close_browser_session(playwright: Playwright | None, browser: Browser | None) -> None:
    try:
        if browser:
            browser.close()
    except Exception:
        pass
    try:
        if playwright:
            playwright.stop()
    except Exception:
        pass


def validate_session_sync(storage_state_json: str) -> bool:
    try:
        state = json.loads(storage_state_json)
    except json.JSONDecodeError:
        return False
    playwright = sync_playwright().start()
    browser = None
    try:
        browser, context = _new_context(playwright, storage_state=state)
        page = context.new_page()
        page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        return _is_logged_in(page)
    except Exception as exc:
        logger.warning("validate_session failed: %s", exc)
        return False
    finally:
        close_browser_session(playwright, browser)


def send_private_message_sync(storage_state_json: str, friend_label: str, message: str) -> SendDmResult:
    try:
        state = json.loads(storage_state_json)
    except json.JSONDecodeError:
        return SendDmResult(success=False, error_message="登录态数据无效")

    playwright = sync_playwright().start()
    browser = None
    try:
        browser, context = _new_context(playwright, storage_state=state)
        page = context.new_page()
        page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        if not _is_logged_in(page):
            return SendDmResult(success=False, error_message="登录态已失效，请重新扫码关联抖音号")

        if not _click_im_entry(page):
            return SendDmResult(success=False, error_message="无法打开抖音私信页面")

        label = (friend_label or "").strip()
        if not label:
            return SendDmResult(success=False, error_message="好友标识为空")

        friend = page.get_by_text(label, exact=False).first
        friend.click(timeout=20000)
        page.wait_for_timeout(1500)
        _send_in_chat(page, message)
        shot = page.screenshot(full_page=False)
        return SendDmResult(success=True, screenshot_base64=base64.b64encode(shot).decode())
    except Exception as exc:
        logger.exception("send_private_message failed")
        return SendDmResult(success=False, error_message=str(exc)[:500])
    finally:
        close_browser_session(playwright, browser)
