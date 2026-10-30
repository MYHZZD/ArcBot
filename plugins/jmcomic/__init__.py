"""jmcomic：复用 getgold 的常驻 Edge 浏览器（CDP），不再启动第二个 profile。"""

from __future__ import annotations

import os

from nonebot import get_bot, on_command
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.params import CommandArg
from playwright.async_api import async_playwright

CDP_PORT = int(os.getenv("GETGOLD_DEBUG_PORT", "9222"))
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"


async def check_html(url: str) -> str | None:
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL, timeout=5000)
        except Exception as exc:
            return f"无法连接 getgold 常驻浏览器，请确认 getgold 已启动：{exc}"

        contexts = browser.contexts
        if not contexts:
            return "getgold 浏览器没有可用的 context"

        try:
            page = await contexts[0].new_page()
        except Exception as exc:
            return f"打开标签页失败：{exc}"

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(15000)

            comic_name = None
            for frame in page.frames:
                try:
                    element = await frame.wait_for_selector(
                        "h1.book-name.mb-0#book-name",
                        timeout=5000,
                        state="attached",
                    )
                    if element:
                        comic_name = await element.text_content()
                        break
                except Exception:
                    continue

            if comic_name:
                return comic_name.strip()
            return "未找到漫画名称，可能页面结构已变化"
        except Exception as exc:
            return f"获取失败：{exc}"
        finally:
            try:
                await page.close()
            except Exception:
                pass


matcher = on_command("jm", aliases={"JM"}, priority=5, block=True)


@matcher.handle()
async def _(event: GroupMessageEvent, Mes: Message = CommandArg()):
    bot = get_bot()
    gid = event.group_id
    url = f"https://jm18c-oec.cc/album/{str(Mes).strip()}"
    result = await check_html(url)
    await bot.send_group_msg(group_id=gid, message=result)
