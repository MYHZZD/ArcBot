"""getgold 常驻浏览器管理器。

- 浏览器和持久化 context 只启动一次，任务之间不关闭；
- 每次任务复用固定的标签页（price / ccb / shot）；
- 标签页被手动关闭时自动重建；
- 浏览器/context 被关闭或崩溃时，下一次任务自动重启；
- 开启 CDP 端口，jmcomic 可以 connect_over_cdp 复用同一登录态。
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Awaitable, Callable, Optional

from nonebot.log import logger
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import Error as PlaywrightError

PROFILE_DIR = os.getenv("GETGOLD_PROFILE", r"D:\data\myUserData")
HEADLESS = os.getenv("GETGOLD_HEADLESS", "false").lower() in ("1", "true", "yes")
CDP_PORT = int(os.getenv("GETGOLD_DEBUG_PORT", "9222"))
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

PAGE_URLS = {
    "price": "https://quote.cngold.org/gjs/gjhj_xhhj.html",
    "ccb": "https://gold3.ccb.com/chn/home/gold_new/cpjs/index.shtml",
    "shot": "https://www.cngold.org/img_date/livegoldcn_rmb.html",
}

DEFAULT_TIMEOUT = 30_000


class BrowserManager:
    def __init__(self) -> None:
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._owned = False
        self._pages: dict[str, Page] = {}
        self._lock = asyncio.Lock()
        self._start_lock = asyncio.Lock()
        self.proxy: Optional[str] = None
        self.proxy_bypass: str = "*.cngold.org;*.ccb.com;*.icbc.com.cn;localhost;127.0.0.1"

    # ---------------- lifecycle ----------------
    async def start(self) -> None:
        async with self._start_lock:
            await self._start_locked()

    async def _start_locked(self) -> None:
        if self._context is not None:
            return
        if self._pw is None:
            self._pw = await async_playwright().start()

        # 1) 先尝试连接已经存在、带调试端口的 Edge（崩溃/重启后的孤儿进程）
        try:
            browser = await self._pw.chromium.connect_over_cdp(CDP_URL, timeout=3000)
            contexts = browser.contexts
            if contexts:
                self._browser = browser
                self._context = contexts[0]
                self._owned = False
                logger.info("getgold: 已连接到现有 Edge 浏览器 (CDP)")
        except Exception:
            self._browser = None
            self._context = None

        # 2) 没有可连接的浏览器就启动一个常驻 context
        if self._context is None:
            try:
                args = [
                    "--disable-blink-features=AutomationControlled",
                    f"--remote-debugging-port={CDP_PORT}",
                    "--remote-debugging-address=127.0.0.1",
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
                proxy = None
                if self.proxy:
                    args.append(f"--proxy-server={self.proxy}")
                    args.append(f"--proxy-bypass-list={self.proxy_bypass}")
                    proxy = {"server": self.proxy}

                self._context = await self._pw.chromium.launch_persistent_context(
                    PROFILE_DIR,
                    channel="msedge",
                    headless=HEADLESS,
                    args=args,
                    proxy=proxy,
                    viewport={"width": 1920, "height": 1080},
                    device_scale_factor=1,
                )
                self._browser = self._context.browser
                self._owned = True
                logger.info("getgold: 已启动常驻 Edge 浏览器")
            except Exception as exc:
                logger.exception("getgold: 启动 Edge 失败（可能是 profile 被其他 Edge 占用）")
                raise RuntimeError(
                    f"无法启动/连接 Edge: {exc}；请确认 {PROFILE_DIR} 没有被其他浏览器占用"
                ) from exc

        assert self._context is not None
        self._context.on("close", self._on_context_close)
        logger.info("getgold: 浏览器已就绪")

    def _on_context_close(self, *_: Any) -> None:
        logger.warning("getgold: 浏览器/context 被关闭，将在下次任务时自动重启")
        self._context = None
        self._browser = None
        self._pages.clear()

    async def stop(self) -> None:
        async with self._start_lock:
            for page in list(self._pages.values()):
                try:
                    if not page.is_closed():
                        await page.close()
                except Exception:
                    pass
            self._pages.clear()
            if self._owned and self._context is not None:
                try:
                    await self._context.close()
                except Exception:
                    pass
            self._context = None
            self._browser = None
            if self._pw is not None:
                try:
                    await self._pw.stop()
                except Exception:
                    pass
            self._pw = None

    # ---------------- pages ----------------
    async def _ensure_started_locked(self) -> None:
        if self._context is None:
            await self._start_locked()

    async def _page_locked(self, kind: str) -> Page:
        await self._ensure_started_locked()
        assert self._context is not None
        page = self._pages.get(kind)
        if page is not None and not page.is_closed():
            return page

        page = await self._context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT)
        page.set_default_navigation_timeout(DEFAULT_TIMEOUT)
        page.on(
            "dialog",
            lambda dialog: asyncio.create_task(_safe_dismiss(dialog)),
        )
        page.on("close", lambda _: self._pages.pop(kind, None))
        self._pages[kind] = page
        logger.debug(f"getgold: 新建标签页 {kind}")
        return page

    async def run(
        self,
        kind: str,
        url: str,
        handler: Callable[[Page], Awaitable[Any]],
        *,
        wait_until: str = "domcontentloaded",
        reload: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Any:
        """在固定标签页上打开 url 并执行 handler；页面/浏览器关闭时自动恢复一次。"""
        async with self._lock:
            last_exc: Optional[Exception] = None
            for attempt in (1, 2):
                try:
                    page = await self._page_locked(kind)
                    if reload and page.url == url:
                        await page.reload(wait_until=wait_until, timeout=timeout)
                    else:
                        await page.goto(url, wait_until=wait_until, timeout=timeout)
                    return await handler(page)
                except PlaywrightError as exc:
                    last_exc = exc
                    logger.warning(f"getgold: 页面操作失败({kind}, attempt={attempt}): {exc}")
                    self._pages.pop(kind, None)
                    if attempt == 1:
                        await self._restart_locked()
            assert last_exc is not None
            raise last_exc

    async def _restart_locked(self) -> None:
        logger.warning("getgold: 重启浏览器")
        if self._owned and self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
        self._context = None
        self._browser = None
        self._pages.clear()
        await self._start_locked()

    # ---------------- convenience ----------------
    async def new_page_for_cdp(self) -> Page:
        """给 jmcomic 之类的外部插件用：在现有 context 新建一个页。"""
        async with self._lock:
            await self._ensure_started_locked()
            assert self._context is not None
            return await self._context.new_page()

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context


async def _safe_dismiss(dialog: Any) -> None:
    try:
        await dialog.dismiss()
    except Exception:
        pass


browser = BrowserManager()
