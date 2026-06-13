import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Callable
from typing import Any, TypeVar

from playwright.sync_api import Browser, Playwright, sync_playwright

from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_executor: concurrent.futures.ThreadPoolExecutor | None = None
_executor_guard = threading.Lock()
_playwright: Playwright | None = None
_browser: Browser | None = None


def _get_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _executor_guard:
            if _executor is None:
                _executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="douyin-browser"
                )
    return _executor


def _ensure_browser() -> Browser:
    global _playwright, _browser
    if _browser is not None and _browser.is_connected():
        return _browser
    if _playwright is None:
        _playwright = sync_playwright().start()
    headless = get_settings().PLAYWRIGHT_HEADLESS
    _browser = _playwright.chromium.launch(headless=headless)
    logger.info("douyin browser launched headless=%s", headless)
    return _browser


def _call_with_browser(fn: Callable[..., T], args: tuple) -> T:
    browser = _ensure_browser()
    return fn(browser, *args)


async def run_browser_task(fn: Callable[..., T], *args: Any) -> T:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_get_executor(), _call_with_browser, fn, args)


async def run_in_browser_thread(fn: Callable[..., T], *args: Any) -> T:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_get_executor(), fn, *args)


def _shutdown_sync() -> None:
    global _playwright, _browser
    try:
        if _browser is not None:
            _browser.close()
    except Exception:
        pass
    _browser = None
    try:
        if _playwright is not None:
            _playwright.stop()
    except Exception:
        pass
    _playwright = None


async def shutdown_browser_runtime() -> None:
    global _executor
    executor = _executor
    if executor is None:
        return
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(executor, _shutdown_sync)
    finally:
        executor.shutdown(wait=True)
        _executor = None
