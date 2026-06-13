import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page

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
class ValidateSessionResult:
    valid: bool
    storage_state: dict | None = None


@dataclass
class SendDmResult:
    success: bool
    error_message: str | None = None
    screenshot_base64: str | None = None
    storage_state: dict | None = None


@dataclass
class RecentContact:
    display_name: str


@dataclass
class FetchRecentContactsResult:
    success: bool
    contacts: list[RecentContact]
    error_message: str | None = None
    storage_state: dict | None = None


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


_BLOCKED_RESOURCE_TYPES = frozenset({"media", "image", "font"})


def _headless() -> bool:
    return get_settings().PLAYWRIGHT_HEADLESS


def _block_heavy_resources(route: Any) -> None:
    try:
        if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
            route.abort()
        else:
            route.continue_()
    except Exception:
        try:
            route.continue_()
        except Exception:
            pass


def _new_context(browser: Browser, storage_state: dict | None = None) -> BrowserContext:
    kwargs: dict[str, Any] = {
        "viewport": {"width": 1280, "height": 800},
        "user_agent": USER_AGENT,
        "locale": "zh-CN",
    }
    if storage_state:
        kwargs["storage_state"] = storage_state
    context = browser.new_context(**kwargs)
    context.route("**/*", _block_heavy_resources)
    return context


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
    for attempt in range(120):
        loc = page.locator('[id^="login-full-panel"]')
        if loc.count():
            logger.info("douyin_qr: login panel ready attempt=%s", attempt)
            return loc.first
        for sel in (
            'header button:has-text("登录")',
            '[data-e2e="login-button"]',
            'header span:has-text("登录")',
        ):
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=200):
                    btn.click(force=True)
                    logger.info("douyin_qr: clicked header login via %s", sel)
                    break
            except Exception:
                continue
        page.wait_for_timeout(150)
    raise RuntimeError("登录弹窗未加载，请稍后重试")


def _open_login_qrcode_panel(page: Page) -> None:
    panel = _wait_login_panel(page)
    for text in ("扫码登录", "扫码"):
        try:
            tab = panel.get_by_text(text, exact=False).first
            tab.click(force=True, timeout=5000)
            page.wait_for_timeout(300)
            logger.info("douyin_qr: switched login tab to %s", text)
            return
        except Exception as exc:
            logger.warning("douyin_qr: switch tab %s failed: %s", text, exc)
    page.get_by_text("扫码登录", exact=False).first.click(force=True, timeout=5000)
    page.wait_for_timeout(300)
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
    for attempt in range(40):
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
        page.wait_for_timeout(200)
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
    t0 = time.perf_counter()
    _open_login_qrcode_panel(page)
    t1 = time.perf_counter()
    el, meta = _find_qr_element(page)
    t2 = time.perf_counter()
    if not el:
        logger.error("douyin_qr: qr element not found after waiting")
        raise RuntimeError("未找到登录二维码，请稍后重试")

    data = el.screenshot()
    t3 = time.perf_counter()
    logger.info(
        "douyin_qr timing capture: open_panel=%.2fs find_el=%.2fs screenshot=%.2fs",
        t1 - t0,
        t2 - t1,
        t3 - t2,
    )
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


def _open_im_panel(page: Page) -> bool:
    """只读：点击首页右上角私信图标，等待右上角私信弹窗出现。不发送任何消息。"""
    for sel in (
        '[data-e2e="im-entry"]',
        '[aria-label*="私信"]',
        '[title*="私信"]',
        'header :text("私信")',
        'text=私信',
    ):
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                loc.scroll_into_view_if_needed(timeout=2000)
                loc.click()
                page.wait_for_timeout(2500)
                logger.warning("recent_contacts: im entry matched sel=%s", sel)
                return True
        except Exception:
            continue
    logger.warning("recent_contacts: im entry NOT found by any selector")
    return False


def _dump_im_entry_candidates(page: Page) -> None:
    """只读：私信入口没点开时，输出头部可点击候选元素，便于定位正确选择器。"""
    try:
        cands = page.evaluate(
            """() => {
                const out = [];
                const nodes = document.querySelectorAll('a,button,span,div,svg,i,[role="button"]');
                for (const el of nodes) {
                    const aria = el.getAttribute ? (el.getAttribute('aria-label') || '') : '';
                    const title = el.getAttribute ? (el.getAttribute('title') || '') : '';
                    const e2e = el.getAttribute ? (el.getAttribute('data-e2e') || '') : '';
                    const text = (el.innerText || '').trim().slice(0, 20);
                    const hit = /私信|消息|im/i.test(aria + ' ' + title + ' ' + e2e + ' ' + text);
                    if (!hit) continue;
                    const r = el.getBoundingClientRect ? el.getBoundingClientRect() : {x:0,y:0,width:0,height:0};
                    const cls = (el.className && el.className.toString) ? el.className.toString() : '';
                    out.push({
                        tag: el.tagName, e2e, aria, title, text,
                        cls: cls.slice(0, 60),
                        x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
                    });
                    if (out.length >= 30) break;
                }
                return out;
            }"""
        )
        logger.warning("recent_contacts: im entry candidates (read-only): %s", cands)
    except Exception as exc:
        logger.warning("dump im entry candidates failed: %s", exc)


def _wait_im_list(page: Page, timeout_ms: int = 18000) -> bool:
    """只读：私信弹窗打开后，轮询等待会话列表异步加载完成（暂无私信消失/出现会话项）。"""
    steps = max(1, timeout_ms // 1000)
    for _ in range(steps):
        try:
            empty = page.locator("text=暂无私信").first.is_visible(timeout=400)
        except Exception:
            empty = False
        if not empty:
            page.wait_for_timeout(800)
            return True
        page.wait_for_timeout(1000)
    logger.warning("recent_contacts: im list still empty (暂无私信) after %dms", timeout_ms)
    return False


def _dump_im_panel_html(page: Page) -> None:
    """只读：输出私信弹窗容器的结构片段，便于定位会话项选择器。"""
    try:
        snippet = page.evaluate(
            """() => {
                const marker = [...document.querySelectorAll('*')].find(
                    el => (el.innerText || '').includes('私信') && el.querySelectorAll('*').length < 200
                );
                let node = marker;
                for (let i = 0; i < 4 && node && node.parentElement; i++) node = node.parentElement;
                if (!node) return null;
                return (node.outerHTML || '').slice(0, 3000);
            }"""
        )
        logger.warning("recent_contacts: im panel html (read-only): %s", snippet)
    except Exception as exc:
        logger.warning("dump im panel html failed: %s", exc)


def _dump_page_state(page: Page) -> None:
    """只读：输出页面整体渲染状态，判断是空白页/反爬页/内容在 iframe。"""
    try:
        logger.warning(
            "recent_contacts: page url=%s title=%r frames=%d",
            page.url, page.title(), len(page.frames)
        )
    except Exception as exc:
        logger.warning("dump page url/title failed: %s", exc)
    try:
        info = page.evaluate(
            """() => ({
                bodyTextLen: ((document.body && document.body.innerText) || '').length,
                elementCount: document.querySelectorAll('*').length,
                iframeCount: document.querySelectorAll('iframe').length,
                hasNav: !!document.querySelector('nav,header,[class*="nav"],[class*="header"]'),
                bodyHead: ((document.body && document.body.innerText) || '').trim().slice(0, 200).replace(/\\n/g, ' | '),
            })"""
        )
        logger.warning("recent_contacts: page state %s", info)
    except Exception as exc:
        logger.warning("dump page state failed: %s", exc)


def _dump_im_dom(page: Page) -> None:
    """只读：抓取不到联系人时，输出弹窗候选容器结构到日志，便于离线调试选择器。"""
    try:
        outline = page.evaluate(
            """() => {
                const out = [];
                const nodes = document.querySelectorAll('div,ul,aside,section');
                for (const el of nodes) {
                    const kids = el.children ? el.children.length : 0;
                    if (kids < 3 || kids > 60) continue;
                    const cls = (el.className && el.className.toString) ? el.className.toString() : '';
                    const e2e = el.getAttribute ? (el.getAttribute('data-e2e') || '') : '';
                    const text = (el.innerText || '').trim().slice(0, 60).replace(/\\n/g, ' | ');
                    if (!text) continue;
                    out.push({ cls: cls.slice(0, 70), e2e, kids, text });
                    if (out.length >= 40) break;
                }
                return out;
            }"""
        )
        logger.warning("im panel dom outline (read-only): %s", outline)
    except Exception as exc:
        logger.warning("dump im dom failed: %s", exc)


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
    try:
        page.evaluate(
            """() => {
                const sels = ['[class*="conversation"]', '[class*="Conversation"]', 'aside', '[class*="list"]'];
                for (const s of sels) {
                    const el = document.querySelector(s);
                    if (el && el.scrollHeight > el.clientHeight) { el.scrollTop = 0; return; }
                }
            }"""
        )
    except Exception:
        pass
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


def start_qr_login_sync(browser: Browser) -> QrStartResult:
    t0 = time.perf_counter()
    context = _new_context(browser)
    page = context.new_page()
    logger.info("douyin_qr: navigating to %s headless=%s", DOUYIN_HOME, _headless())
    page.goto(DOUYIN_HOME, wait_until="commit", timeout=60000)
    t1 = time.perf_counter()
    logger.info("douyin_qr: landed url=%s", page.url)

    logged_in = _is_logged_in(page)
    t2 = time.perf_counter()
    logger.info(
        "douyin_qr timing start: new_ctx_goto=%.2fs login_check=%.2fs",
        t1 - t0,
        t2 - t1,
    )

    if logged_in:
        logger.info("douyin_qr: already logged in")
        state = context.storage_state()
        profile = _extract_profile(page)
        return QrStartResult(
            qrcode_base64="",
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


def close_context(context: BrowserContext | None) -> None:
    try:
        if context:
            context.close()
    except Exception:
        pass


_AUTH_COOKIE_NAMES = frozenset({"sessionid", "sessionid_ss", "sid_tt", "uid_tt"})


def _capture_storage_state(context: BrowserContext | None) -> dict | None:
    try:
        if not context:
            return None
        state = context.storage_state()
        names = {c.get("name", "") for c in (state.get("cookies") or [])}
        if names & _AUTH_COOKIE_NAMES:
            return state
        logger.warning("skip storage_state persist: no auth cookie present")
    except Exception:
        logger.warning("capture storage_state failed", exc_info=True)
    return None


def validate_session_sync(browser: Browser, storage_state_json: str) -> ValidateSessionResult:
    try:
        state = json.loads(storage_state_json)
    except json.JSONDecodeError:
        return ValidateSessionResult(valid=False)
    context = None
    try:
        context = _new_context(browser, storage_state=state)
        page = context.new_page()
        page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        if _is_logged_in(page):
            return ValidateSessionResult(valid=True, storage_state=_capture_storage_state(context))
        return ValidateSessionResult(valid=False)
    except Exception as exc:
        logger.warning("validate_session failed: %s", exc)
        return ValidateSessionResult(valid=False)
    finally:
        close_context(context)


def fetch_recent_contacts_sync(browser: Browser, storage_state_json: str, limit: int = 10) -> FetchRecentContactsResult:
    try:
        state = json.loads(storage_state_json)
    except json.JSONDecodeError:
        return FetchRecentContactsResult(success=False, contacts=[], error_message="登录态数据无效")

    cap = max(1, min(limit, 10))
    context = None
    try:
        context = _new_context(browser, storage_state=state)
        page = context.new_page()
        page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        if not _is_logged_in(page):
            return FetchRecentContactsResult(
                success=False,
                contacts=[],
                error_message="登录态已失效，请重新扫码关联抖音号",
            )

        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        if not _open_im_panel(page):
            _dump_page_state(page)
            _dump_im_entry_candidates(page)
            return FetchRecentContactsResult(success=False, contacts=[], error_message="无法打开抖音私信弹窗")

        list_ready = _wait_im_list(page)

        labels = _collect_contact_labels(page, cap)
        logger.warning("recent_contacts: collected %d labels (list_ready=%s)", len(labels), list_ready)
        if not labels:
            _dump_im_panel_html(page)
            _dump_im_dom(page)
            return FetchRecentContactsResult(
                success=False,
                contacts=[],
                error_message="未能读取最近联系人，请确认私信列表中有会话",
            )
        return FetchRecentContactsResult(
            success=True,
            contacts=[RecentContact(display_name=n) for n in labels],
            storage_state=_capture_storage_state(context),
        )
    except Exception as exc:
        logger.exception("fetch_recent_contacts failed")
        return FetchRecentContactsResult(success=False, contacts=[], error_message=str(exc)[:500])
    finally:
        close_context(context)


def send_private_message_sync(browser: Browser, storage_state_json: str, friend_label: str, message: str) -> SendDmResult:
    try:
        state = json.loads(storage_state_json)
    except json.JSONDecodeError:
        return SendDmResult(success=False, error_message="登录态数据无效")

    context = None
    try:
        context = _new_context(browser, storage_state=state)
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
        return SendDmResult(
            success=True,
            screenshot_base64=base64.b64encode(shot).decode(),
            storage_state=_capture_storage_state(context),
        )
    except Exception as exc:
        logger.exception("send_private_message failed")
        return SendDmResult(success=False, error_message=str(exc)[:500])
    finally:
        close_context(context)
