from nonebot import get_bot, on_command, get_driver
from playwright.async_api import async_playwright
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.adapters import Message
import random
import asyncio

user_data_dir = "D://data//myUserData"
proxy_config = get_driver().config.proxy

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
]

VIEWPORT_SIZES = [
    {"width": 1920, "height": 1080},
    {"width": 1280, "height": 720},
]


async def check_html(url: str) -> str | None:
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            channel="msedge",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            viewport=random.choice(VIEWPORT_SIZES),
            user_agent=random.choice(USER_AGENTS),
            proxy={"server": proxy_config},
        )

        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(15000)

        try:
            comic_name = None
            for frame in page.frames:
                try:
                    element = await frame.wait_for_selector(
                        "h1.book-name.mb-0#book-name", timeout=5000, state="attached"
                    )
                    if element:
                        comic_name = await element.text_content()
                        break
                except:
                    continue

            if comic_name:
                return comic_name.strip()
            else:
                return "未找到漫画名称，可能页面结构已变化"
        except Exception as e:
            return f"获取失败：{str(e)}"


matcher = on_command("jm", aliases={"JM"})


@matcher.handle()
async def _(event: GroupMessageEvent, Mes: Message = CommandArg()):
    bot = get_bot()
    gid = event.group_id
    url = f"https://jm18c-oec.cc/album/{Mes}"
    result = await check_html(url)
    await bot.send_group_msg(group_id=gid, message=result)
