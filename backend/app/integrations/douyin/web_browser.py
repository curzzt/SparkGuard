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


@dataclass
class RecentContact:
    display_name: str


@dataclass
class FetchRecentContactsResult:
    success: bool
    contacts: list[RecentContact]
    error_message: str | None = None


_SKIP_CONTACT_LABELS = frozenset(
    {
        "陌生人消息",
        "互动消息",
        "系统通知",
        "消息",
        "私信",
        "搜索",
        "登录",
        "扫码登录",
        "验证码登录",
        "暂无消息",
        "加载中",
        "发送消息",
    }
)


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
    loc = page.locator('[id^="login-full-panel"]')
    if loc.count():
        return loc.first
    return page.locator("body")


def _wait_login_panel(page: Page) -> object:
    for attempt in range(30):
        loc = page.locator('[id^="login-full-panel"]')
        if loc.count():
            logger.info("douyin_qr: login panel ready attempt=%s", attempt)
            return loc.first
        if attempt in (0, 3, 6):
            for sel in (
                'header button:has-text("登录")',
                '[data-e2e="login-button"]',
                'header span:has-text("登录")',
            ):
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=1000):
                        btn.click(force=True)
                        logger.info("douyin_qr: clicked header login via %s", sel)
                        break
                except Exception:
                    continue
        page.wait_for_timeout(500)
    raise RuntimeError("登录弹窗未加载，请稍后重试")


def _open_login_qrcode_panel(page: Page) -> None:
    panel = _wait_login_panel(page)
    for text in ("扫码登录", "扫码"):
        try:
            tab = panel.get_by_text(text, exact=False).first
            tab.click(force=True, timeout=5000)
            page.wait_for_timeout(2000)
            logger.info("douyin_qr: switched login tab to %s", text)
            return
        except Exception as exc:
            logger.warning("douyin_qr: switch tab %s failed: %s", text, exc)
    page.get_by_text("扫码登录", exact=False).first.click(force=True, timeout=5000)
    page.wait_for_timeout(2000)
    logger.info("douyin_qr: switched login tab via page fallback")


def _qr_box_score(box: dict) -> float | None:
    w = box.get("width") or 0
    h = box.get("height") or 0
    if w < 140 or h < 140 or w > 360 or h > 360:
        return None
    ratio = w / h if h else 0
    if ratio < 0.85 or ratio > 1.15:
        return None
    area = w * h
    square_penalty = abs(w - h)
    return area - square_penalty * 20


def _find_qr_element(page: Page):
    panel = _login_panel(page)
    scopes = [panel]
    if page.locator('[class*="login"]').count():
        scopes.append(page.locator('[class*="login"]').first)
    best = None
    best_meta = None
    for attempt in range(16):
        for scope in scopes:
            for sel in ("img", "canvas"):
                loc = scope.locator(sel)
                for i in range(loc.count()):
                    el = loc.nth(i)
                    try:
                        box = el.bounding_box()
                        if not box:
                            continue
                        score = _qr_box_score(box)
                        if score is None:
                            continue
                        meta = {"selector": sel, "index": i, "box": box, "score": score, "attempt": attempt}
                        if best is None or score > best_meta["score"]:
                            best = el
                            best_meta = meta
                    except Exception:
                        continue
        if best is not None:
            return best, best_meta
        page.wait_for_timeout(500)
    return None, None


def validate_qr_image_base64(payload: str) -> tuple[bool, str]:
    try:
        raw = base64.b64decode(payload)
    except Exception:
        return False, "invalid_base64"
    if len(raw) < 3000:
        return False, f"too_small_bytes={len(raw)}"
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return False, "not_png"
    w, h = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
    if w < 140 or h < 140 or w > 360 or h > 360:
        return False, f"bad_png_size={w}x{h}"
    ratio = w / h if h else 0
    if ratio < 0.85 or ratio > 1.15:
        return False, f"bad_png_ratio={ratio:.2f}"
    return True, f"{w}x{h}"


def _capture_qrcode_image(page: Page) -> tuple[str, dict]:
    _open_login_qrcode_panel(page)
    el, meta = _find_qr_element(page)
    if not el:
        logger.error("douyin_qr: qr element not found after waiting")
        raise RuntimeError("未找到登录二维码，请稍后重试")

    data = el.screenshot()
    meta = {**meta, "bytes": len(data)}
    logger.info("douyin_qr: captured element %s", meta)
    encoded = base64.b64encode(data).decode()
    ok, reason = validate_qr_image_base64(encoded)
    if not ok:
        logger.error("douyin_qr: invalid qr image %s meta=%s", reason, meta)
        raise RuntimeError("登录二维码无效，请稍后重试")
    return encoded, {**meta, "png": reason}


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


def _normalize_contact_label(text: str) -> str | None:
    line = (text or "").strip().split("\n")[0].strip()
    if not line or len(line) > 50:
        return None
    if line in _SKIP_CONTACT_LABELS:
        return None
    lower = line.lower()
    if lower.startswith("http") or "@" in line:
        return None
    return line


def _collect_contact_labels(page: Page, limit: int) -> list[str]:
    page.wait_for_timeout(2500)
    names: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        if len(names) >= limit:
            return
        label = _normalize_contact_label(raw or "")
        if not label or label in seen:
            return
        seen.add(label)
        names.append(label)

    try:
        js_names = page.evaluate(
            """(limit) => {
                const skip = new Set([
                    "陌生人消息", "互动消息", "系统通知", "消息", "私信", "搜索",
                    "登录", "扫码登录", "验证码登录", "暂无消息", "加载中", "发送消息",
                ]);
                const out = [];
                const seen = new Set();
                const selectors = [
                    '[data-e2e*="conversation"]',
                    '[data-e2e*="chat-item"]',
                    '[class*="Conversation"]',
                    '[class*="conversation"]',
                    'aside [class*="item"]',
                    '[class*="list"] [class*="item"]',
                ];
                for (const sel of selectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        const text = (el.innerText || "").trim().split("\\n")[0].trim();
                        if (!text || text.length > 50 || skip.has(text) || seen.has(text)) continue;
                        seen.add(text);
                        out.push(text);
                        if (out.length >= limit) return out;
                    }
                }
                return out;
            }""",
            limit,
        )
        if isinstance(js_names, list):
            for item in js_names:
                if isinstance(item, str):
                    add(item)
    except Exception as exc:
        logger.warning("collect contacts via evaluate failed: %s", exc)

    if len(names) >= limit:
        return names[:limit]

    for sel in (
        '[data-e2e*="conversation"]',
        '[data-e2e*="chat-item"]',
        '[class*="ConversationItem"]',
        '[class*="conversation-item"]',
        'aside li',
        '[class*="list"] > div',
    ):
        loc = page.locator(sel)
        count = min(loc.count(), 40)
        for i in range(count):
            try:
                add(loc.nth(i).inner_text())
            except Exception:
                continue
            if len(names) >= limit:
                return names[:limit]

    return names[:limit]


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
    logger.info("douyin_qr: capture ok meta=%s", meta)
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


def fetch_recent_contacts_sync(storage_state_json: str, limit: int = 10) -> FetchRecentContactsResult:
    try:
        state = json.loads(storage_state_json)
    except json.JSONDecodeError:
        return FetchRecentContactsResult(success=False, contacts=[], error_message="登录态数据无效")

    cap = max(1, min(limit, 10))
    playwright = sync_playwright().start()
    browser = None
    try:
        browser, context = _new_context(playwright, storage_state=state)
        page = context.new_page()
        page.goto(DOUYIN_MESSAGE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        if not _is_logged_in(page):
            return FetchRecentContactsResult(
                success=False,
                contacts=[],
                error_message="登录态已失效，请重新扫码关联抖音号",
            )

        if page.url.find("/message") < 0 and not _click_im_entry(page):
            return FetchRecentContactsResult(success=False, contacts=[], error_message="无法打开抖音私信页面")

        labels = _collect_contact_labels(page, cap)
        if not labels:
            return FetchRecentContactsResult(
                success=False,
                contacts=[],
                error_message="未能读取最近联系人，请确认私信列表中有会话",
            )
        return FetchRecentContactsResult(
            success=True,
            contacts=[RecentContact(display_name=n) for n in labels],
        )
    except Exception as exc:
        logger.exception("fetch_recent_contacts failed")
        return FetchRecentContactsResult(success=False, contacts=[], error_message=str(exc)[:500])
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
