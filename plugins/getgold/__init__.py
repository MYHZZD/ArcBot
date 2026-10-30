from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Optional

from nonebot import get_bot, get_driver, on_command, require
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.log import logger
from playwright.async_api import Frame, Page

from . import storage
from .browser import PAGE_URLS, browser

scheduler = require("nonebot_plugin_apscheduler").scheduler

storage.init_db()
GROUP_JSON = storage.GETGOLD_DIR / "group.json"

_config = get_driver().config
_proxy = getattr(_config, "proxy", None)
browser.proxy = os.getenv("GETGOLD_PROXY") or (str(_proxy) if _proxy else None)
browser.proxy_bypass = os.getenv("GETGOLD_PROXY_BYPASS", browser.proxy_bypass)

SHORT_TERM_THRESHOLD = 0.2   # 单次变化百分比
INTERVAL_WINDOW = 15         # 分钟
INTERVAL_THRESHOLD = 0.5     # 区间变化百分比
TREND_MIN_POINTS = 10


# ---------------- 群配置（保留 group.json 原样） ----------------
def load_groups() -> tuple[bool, list[str]]:
    try:
        raw = json.loads(GROUP_JSON.read_text(encoding="utf8")).get("group", "")
    except Exception:
        logger.exception("读取 group.json 失败")
        return False, []

    parts = str(raw).split()
    if not parts or parts[0] != "on":
        return False, []
    return True, [part for part in parts[1:] if part]


# ---------------- 抓取 ----------------
async def search_in_frames(
    frame: Frame, predicate: Callable[[str], Optional[Any]]
) -> Optional[Any]:
    try:
        html = await frame.evaluate("document.documentElement.outerHTML")
    except Exception:
        html = ""

    result = predicate(html)
    if result is not None:
        return result

    for child in frame.child_frames:
        result = await search_in_frames(child, predicate)
        if result is not None:
            return result
    return None


async def search_gold(page: Page, redata: dict) -> Optional[float]:
    def predicate(html: str) -> Optional[float]:
        if redata["key"] in html:
            match = re.search(redata["value"], html)
            if match:
                try:
                    return float(match.group(1))
                except (TypeError, ValueError):
                    return None
        return None

    for frame in page.frames:
        price = await search_in_frames(frame, predicate)
        if price is not None:
            return price
    return None


async def scrape_website(
    url: str,
    redata: dict,
    *,
    kind: str = "price",
    selector: Optional[str] = None,
) -> Optional[float]:
    async def handler(page: Page) -> Optional[float]:
        if selector:
            try:
                await page.wait_for_selector(
                    selector, timeout=8000, state="attached"
                )
            except Exception:
                pass
        for attempt in range(5):
            result = await search_gold(page, redata)
            if result is not None:
                return result
            if attempt < 4:
                await page.wait_for_timeout(2000)
        return None

    return await browser.run(kind, url, handler)


async def check_gold4() -> Optional[float]:
    return await scrape_website(
        PAGE_URLS["ccb"],
        {
            "key": r"主动积存价",
            "value": r'<td id="initiativeBuyPrice">([\d.]+)\s*元/克\s*</td>',
        },
        kind="ccb",
        selector="#initiativeBuyPrice",
    )


async def check_gold5() -> Optional[float]:
    return await scrape_website(
        PAGE_URLS["price"],
        {
            "key": r"realtime_price",
            "value": r'<b id="now_price"[^>]*>([\d.]+)</b></h1>',
        },
        kind="price",
        selector="#now_price",
    )


async def get_gold_screenshot() -> bytes:
    async def handler(page: Page) -> bytes:
        await page.evaluate("window.scrollBy(0, 200)")
        await page.wait_for_timeout(800)
        return await page.screenshot(
            type="png",
            clip={"x": 710, "y": 110, "width": 730, "height": 690},
        )

    return await browser.run(
        "shot",
        PAGE_URLS["shot"],
        handler,
        wait_until="domcontentloaded",
    )


async def fetch_quotes() -> tuple[Optional[float], Optional[float], Optional[bytes]]:
    price4 = price5 = None
    screenshot: Optional[bytes] = None

    try:
        price4 = await check_gold4()
    except Exception:
        logger.exception("获取建行积存价失败")
    try:
        price5 = await check_gold5()
    except Exception:
        logger.exception("获取现货黄金价格失败")
    try:
        screenshot = await get_gold_screenshot()
    except Exception:
        logger.exception("获取黄金行情截图失败")

    return price4, price5, screenshot


def quote_message(
    price4: Optional[float], price5: Optional[float], screenshot: Optional[bytes]
) -> Message:
    text4 = f"{price4} 元" if price4 is not None else "获取失败"
    text5 = f"{price5}" if price5 is not None else "获取失败"
    segments = [
        MessageSegment.text(
            f"建设银行主动积存价 {text4}。\n现货黄金价格为 {text5}"
        )
    ]
    if screenshot:
        segments.append(MessageSegment.image(screenshot))
    return Message(segments)


# ---------------- 定时播报 ----------------
async def getgold0() -> None:
    enabled, groups = load_groups()
    if not enabled or not groups:
        return

    price4, price5, screenshot = await fetch_quotes()
    if price4 is None and price5 is None and screenshot is None:
        return

    message = quote_message(price4, price5, screenshot)
    bot = get_bot()
    for group_id in groups:
        try:
            await bot.send_group_msg(group_id=int(group_id), message=message)
        except Exception:
            logger.exception(f"向群 {group_id} 播报金价失败")


scheduler.add_job(
    getgold0, "cron", minute=0, second=0, hour="0-23", day_of_week="1-4",
    id="getgold_weekday",
)
scheduler.add_job(
    getgold0, "cron", minute=0, second=0, hour="9-23", day_of_week="0",
    id="getgold_monday",
)
scheduler.add_job(
    getgold0, "cron", minute=0, second=0, hour="0-2", day_of_week="5",
    id="getgold_saturday",
)


query = on_command("今日金价", priority=5, block=True)


@query.handle()
async def _handle_query(event: GroupMessageEvent) -> None:
    bot = get_bot()
    gid = event.group_id
    await bot.send_group_msg(group_id=gid, message="正在查询黄金价格......")

    price4, price5, screenshot = await fetch_quotes()
    if price4 is None and price5 is None and screenshot is None:
        await bot.send_group_msg(group_id=gid, message="行情获取失败，请稍后再试")
        return

    await bot.send_group_msg(
        group_id=gid, message=quote_message(price4, price5, screenshot)
    )


# ---------------- 预警 ----------------
async def send_warning(text: str) -> None:
    enabled, groups = load_groups()
    if not enabled or not groups:
        return

    screenshot: Optional[bytes] = None
    try:
        screenshot = await get_gold_screenshot()
    except Exception:
        logger.exception("预警截图获取失败")

    bot = get_bot()
    for group_id in groups:
        segments = [MessageSegment.text(text)]
        if screenshot:
            segments.append(MessageSegment.image(screenshot))
        try:
            await bot.send_group_msg(
                group_id=int(group_id), message=Message(segments)
            )
        except Exception:
            logger.exception(f"向群 {group_id} 发送预警失败")


async def analyze_price(price_id: int) -> None:
    rows = storage.last_prices(16)
    if len(rows) <= 15:
        return

    last = rows[-1]
    prev = rows[-2]
    if not prev["price"]:
        return
    change_percent = (last["price"] - prev["price"]) / prev["price"] * 100

    last_push_row = storage.last_push()
    last_push = None
    if last_push_row is not None and last_push_row["ts"] >= rows[0]["ts"]:
        last_push = last_push_row["push"]

    # 1. 短期剧烈波动（两条记录间隔过长时不按“一分钟”判断）
    if (
        last["ts"] - prev["ts"] <= 300
        and abs(change_percent) > SHORT_TERM_THRESHOLD
    ):
        direction = 1 if change_percent > 0 else -1
        if last_push is None or direction * last_push < 0:
            direction_text = "暴涨" if change_percent > 0 else "暴跌"
            await send_warning(
                f"⚠️ 黄金价格一分钟内{direction_text}"
                f"{abs(change_percent):.2f}％，当前价格{last['price']}美元/盎司"
            )
            storage.set_push(price_id, change_percent)
        return

    # 2. 最近 15 分钟趋势
    prices = storage.prices_since(last["ts"] - INTERVAL_WINDOW * 60)
    if len(prices) < TREND_MIN_POINTS:
        return

    values = [row["price"] for row in prices]
    min_price = min(values)
    max_price = max(values)
    start_price = values[0]
    end_price = values[-1]
    rise_from_low = (end_price - min_price) / min_price * 100
    drop_from_high = (max_price - end_price) / max_price * 100

    if start_price < end_price and rise_from_low > INTERVAL_THRESHOLD:
        if last_push is None or last_push < 0:
            await send_warning(
                f"📈 黄金价格15分钟内从最低点上涨{rise_from_low:.2f}％，"
                f"当前价格{end_price}美元/盎司，最低价格{min_price}美元/盎司"
            )
            storage.set_push(price_id, rise_from_low)
    elif start_price > end_price and drop_from_high > INTERVAL_THRESHOLD:
        if last_push is None or last_push > 0:
            await send_warning(
                f"📉 黄金价格15分钟内从最高点下跌{drop_from_high:.2f}％，"
                f"当前价格{end_price}美元/盎司，最高价格{max_price}美元/盎司"
            )
            storage.set_push(price_id, -drop_from_high)


def is_allowed_time() -> bool:
    now = time.localtime()
    wday = now.tm_wday
    hour = now.tm_hour
    if wday in (1, 2, 3, 4):
        return True
    if wday == 0 and 9 <= hour <= 23:
        return True
    if wday == 5 and 0 <= hour <= 2:
        return True
    return False


async def record_price5() -> None:
    if not is_allowed_time():
        return

    try:
        price = await check_gold5()
    except Exception:
        logger.exception("采集现货黄金价格失败")
        return
    if price is None:
        return

    price_id = storage.insert_price(time.time(), price)
    try:
        await analyze_price(price_id)
    except Exception:
        logger.exception("黄金价格预警分析失败")


scheduler.add_job(record_price5, "cron", second=30, id="record_price5")


# ---------------- 生命周期 ----------------
async def _start_browser() -> None:
    try:
        await browser.start()
    except Exception:
        logger.exception("getgold: 浏览器启动失败，将在首次任务时重试")


async def _stop_browser() -> None:
    try:
        await browser.stop()
    except Exception:
        logger.exception("getgold: 关闭浏览器失败")


_driver = get_driver()
_driver.on_startup(_start_browser)
_driver.on_shutdown(_stop_browser)
