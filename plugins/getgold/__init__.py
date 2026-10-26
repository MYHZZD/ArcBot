from nonebot import require, get_bot, on_command
from playwright.async_api import async_playwright, Page, Frame
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageSegment
import re, os, json, time
from typing import Optional, Tuple, Callable, Awaitable, Any

scheduler = require("nonebot_plugin_apscheduler").scheduler

USER_DATA_DIR = "D://data//myUserData"
os.makedirs("data/getgold", exist_ok=True)
checkdoc = os.path.exists("data/getgold/group.json")
if not os.path.exists("data/getgold/group.json"):
    with open("data/getgold/group.json", "w", encoding="utf8") as f:
        json.dump({"group": "114514"}, f, ensure_ascii=False)


async def scrape_website(url: str, redata: dict) -> Any:
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            channel="msedge",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        result = None
        for attempt in range(5):
            result = await search_gold(page, redata)
            if result is not None:
                break
            if attempt < 4:  # 前四次尝试失败后等待2秒
                await page.wait_for_timeout(2000)

        await context.close()
        return result


async def get_gold_screenshot() -> bytes:
    """获取黄金价格行情截图（固定参数）"""
    return await screenshot_website(
        url="https://www.cngold.org/img_date/livegoldcn_rmb.html",
        scroll_y=200,
        clip={"x": 710, "y": 110, "width": 730, "height": 690},
    )


async def screenshot_website(
    url: str,
    scroll_y: int = 500,  # 向下滚动的像素值
    clip: Optional[dict] = None,  # 截图区域，格式: {"x": int, "y": int, "width": int, "height": int}
) -> bytes:
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            channel="msedge",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--force-device-scale-factor=1",
            ],
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.evaluate(f"window.scrollBy(0, {scroll_y})")
        await page.wait_for_timeout(500)  # 简单延迟
        screenshot = await page.screenshot(type="png", clip=clip)
        await context.close()
        return screenshot


async def search_in_frames(frame: Frame, predicate: Callable[[str], Optional[Any]]) -> Optional[Any]:
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
            m = re.search(redata["value"], html)
            if m:
                return float(m.group(1))
        return None

    for frame in page.frames:
        price = await search_in_frames(frame, predicate)
        if price is not None:
            return price
    return None


async def check_gold1() -> Optional[float]:
    return await scrape_website(
        "https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp?serviceId=PBL200603",
        {"key": r"人民币账户黄金", "value": r'id="buyprice_901".*?>(\d+\.\d+)</div>'},
    )


async def check_gold2() -> Tuple[Optional[float], Optional[float]]:
    return await scrape_website(
        "https://www.sge.com.cn/sjzx/yshqbg/",
        {
            "key": r"Au99.99",
            "value": r"<td[^>]*>Au99.99[^<]*</td>\s*<td[^>]*><span[^>]*>([\d.]+)</span>",
        },
    )


async def check_gold3() -> Tuple[Optional[float], Optional[float]]:
    return await scrape_website(
        "https://www.sge.com.cn/sjzx/yshqbg/",
        {
            "key": r"Au(T+D)",
            "value": r"<td[^>]*>Au\(T\+D\)[^<]*?</td>\s*<td[^>]*><span[^>]*>([\d.]+)</span>",
        },
    )


async def check_gold4() -> Optional[float]:
    return await scrape_website(
        "https://gold3.ccb.com/chn/home/gold_new/cpjs/index.shtml",
        {
            "key": r"主动积存价",
            "value": r'<td id="initiativeBuyPrice">([\d.]+)\s*元/克\s*</td>',
        },
    )


async def check_gold5() -> Optional[float]:
    return await scrape_website(
        "https://quote.cngold.org/gjs/gjhj_xhhj.html",
        {
            "key": r"realtime_price",
            "value": r'<b id="now_price"[^>]*>([\d.]+)</b></h1>',
        },
    )


async def getgold0():
    bot = get_bot()
    # price1 = await check_gold1()
    # price2 = await check_gold2()
    # price3 = await check_gold3()
    price4 = await check_gold4()
    price5 = await check_gold5()
    screenshot = await get_gold_screenshot()
    with open("data/getgold/group.json", "r", encoding="utf8") as readgroup:
        jsondata: str = readgroup.read()
        groupdata = json.loads(jsondata)
        group = groupdata["group"]
        grouplist = group.split()
    if grouplist[0] == "on":
        for i in range(len(grouplist) - 1):
            message = Message(
                [
                    MessageSegment.text(
                        # f"当前工商银行人民币账户黄金的银行买入价为 {price1} 元。\n"
                        f"建设银行主动积存价 {price4} 元。\n"
                        # f"上海黄金交易所Au99.99为 {price2} 元; Au(T+D)为 {price3} 元。\n"
                        f"现货黄金价格为 {price5}"
                    ),
                    MessageSegment.image(screenshot),
                ]
            )
            await bot.send_group_msg(group_id=grouplist[i + 1], message=message)


scheduler.add_job(getgold0, "cron", minute=0, second=0, hour="0-23", day_of_week="1-4", id="getgold_weekday")
scheduler.add_job(getgold0, "cron", minute=0, second=0, hour="9-23", day_of_week="0", id="getgold_monday")
scheduler.add_job(getgold0, "cron", minute=0, second=0, hour="0-2", day_of_week="5", id="getgold_saturday")

matcher = on_command("今日金价")


@matcher.handle()
async def _(event: GroupMessageEvent):
    bot = get_bot()
    gid = event.group_id
    await bot.send_group_msg(group_id=gid, message="正在查询黄金价格......")
    # price1 = await check_gold1()
    # price2 = await check_gold2()
    # price3 = await check_gold3()
    price4 = await check_gold4()
    price5 = await check_gold5()
    screenshot = await get_gold_screenshot()
    message = Message(
        [
            MessageSegment.text(
                # f"当前工商银行人民币账户黄金的银行买入价为 {price1} 元。\n"
                f"建设银行主动积存价 {price4} 元。\n"
                # f"上海黄金交易所Au99.99为 {price2} 元; Au(T+D)为 {price3} 元。\n"
                f"现货黄金价格为 {price5}"
            ),
            MessageSegment.image(screenshot),
        ]
    )
    await bot.send_group_msg(group_id=gid, message=message)


# 价格历史文件路径
PRICE_HISTORY_FILE = "data/getgold/price_history.json"

# 波动阈值
SHORT_TERM_THRESHOLD = 0.2  # 单次变化 触发剧烈波动预警
INTERVAL_WINDOW = 15  # 区间检测窗口长度
INTERVAL_THRESHOLD = 0.5  # 区间整体变化 触发趋势预警


async def send_warning(text: str):
    """向 group.json 中配置的所有群发送警告消息"""
    bot = get_bot()
    try:
        screenshot = await get_gold_screenshot()
    except Exception as e:
        print(f"预警截图获取失败: {e}")
        screenshot = None
    with open("data/getgold/group.json", "r", encoding="utf8") as f:
        data = json.load(f)
        group_str = data.get("group", "")
        grouplist = group_str.split()
        if grouplist and grouplist[0] == "on":
            for gid in grouplist[1:]:
                msg = Message([MessageSegment.text(text)])
                if screenshot:
                    msg.append(MessageSegment.image(screenshot))
                await bot.send_group_msg(group_id=int(gid), message=msg)


async def analyze_price(history: list):
    """分析价格历史，触发预警"""
    if len(history) <= INTERVAL_WINDOW:
        return

    last_push = None
    for h in reversed(history[-INTERVAL_WINDOW:]):
        if "推送" in h:
            last_push = h["推送"]  # 存储的是带符号的涨跌幅（正：涨，负：跌）
            break

    # 最近两次价格
    last = history[-1]["price"]
    prev = history[-2]["price"]
    change_percent = (last - prev) / prev * 100

    # 1. 短期剧烈波动
    if abs(change_percent) > SHORT_TERM_THRESHOLD:
        direction = 1 if change_percent > 0 else -1
        # 上次无推送 或 方向相反时触发
        if last_push is None or direction * last_push < 0:
            direction_text = "暴涨" if change_percent > 0 else "暴跌"
            msg = f"⚠️ 黄金价格一分钟内{direction_text}{abs(change_percent):.2f}％，当前价格{last}美元/盎司"
            await send_warning(msg)
            history[-1]["推送"] = change_percent  # 记录本次涨跌幅（带符号）
        return

    # 2. 持续同向趋势（最近 TREND_WINDOW 条记录）
    prices = [h["price"] for h in history[-INTERVAL_WINDOW:]]
    min_price = min(prices)
    max_price = max(prices)
    start_price = prices[0]
    rise_from_low = (last - min_price) / min_price * 100
    drop_from_high = (max_price - last) / max_price * 100
    change_15 = (max_price - min_price) / min_price * 100

    if start_price < last:  # 整体上涨趋势
        # 只允许上涨预警（即使下跌条件满足也忽略）
        if rise_from_low > INTERVAL_THRESHOLD:
            # 上涨方向
            if last_push is None or last_push < 0:  # 上次无推送 或 上次是下跌方向
                msg = f"📈 黄金价格15分钟内从最低点上涨{rise_from_low:.2f}％，当前价格{last}美元/盎司，最低价格{min_price}美元/盎司"
                await send_warning(msg)
                history[-1]["推送"] = rise_from_low  # 存正数（上涨）
    if start_price > last:  # 整体下跌趋势
        if drop_from_high > INTERVAL_THRESHOLD:
            # 下跌方向
            if last_push is None or last_push > 0:  # 上次无推送 或 上次是上涨方向
                msg = f"📉 黄金价格15分钟内从最高点下跌{drop_from_high:.2f}％，当前价格{last}美元/盎司，最高价格{max_price}美元/盎司"
                await send_warning(msg)
                history[-1]["推送"] = -drop_from_high  # 存负数（下跌）


def is_allowed_time() -> bool:
    """判断当前时间是否在允许抓取和预警的时间段内"""
    now = time.localtime()
    wday = now.tm_wday  # 0=周一, 6=周日
    hour = now.tm_hour

    # 周二至周五 (1,2,3,4) 全天
    if wday in (1, 2, 3, 4):
        return True
    # 周一 的 9-23 点
    if wday == 0 and 9 <= hour <= 23:
        return True
    # 周六 的 0-2 点
    if wday == 5 and 0 <= hour <= 2:
        return True
    # 其余时间（周六等）不允许
    return False


async def record_price5():
    """每分钟执行：获取价格、存储、分析波动"""
    if not is_allowed_time():
        return  # 不在活跃时间段，直接跳过

    price = await check_gold5()
    if price is None:
        return

    # 读取历史
    if os.path.exists(PRICE_HISTORY_FILE):
        with open(PRICE_HISTORY_FILE, "r", encoding="utf8") as f:
            history = json.load(f)
    else:
        history = []

    history.append({"time": time.time(), "price": price})

    # 波动分析
    await analyze_price(history)

    # 追加新记录
    with open(PRICE_HISTORY_FILE, "w", encoding="utf8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


scheduler.add_job(record_price5, "cron", second=30, id="record_price5")


async def archive_price_history():
    """
    将现有 price_history.json 按日期归档，并创建新的空文件。
    仅在周六凌晨执行，避免干扰正常运行。
    """
    if not os.path.exists(PRICE_HISTORY_FILE):
        # 若文件不存在，则创建一个空文件
        with open(PRICE_HISTORY_FILE, "w", encoding="utf8") as f:
            json.dump([], f, ensure_ascii=False)
        return

    # 生成归档文件名：price_history_YYYYMMDD.json
    archive_name = f"price_history_{time.strftime('%Y%m%d')}.json"
    archive_path = os.path.join("data/getgold", archive_name)

    # 如果归档文件已存在（防止意外），则添加时间戳避免覆盖
    if os.path.exists(archive_path):
        archive_name = f"price_history_{time.strftime('%Y%m%d_%H%M%S')}.json"
        archive_path = os.path.join("data/getgold", archive_name)

    # 重命名当前文件
    os.rename(PRICE_HISTORY_FILE, archive_path)

    # 创建新的空历史文件
    with open(PRICE_HISTORY_FILE, "w", encoding="utf8") as f:
        json.dump([], f, ensure_ascii=False)

    print(f"已归档历史价格文件至 {archive_path}，并创建新文件。")


# 添加每周六凌晨 00:00 执行归档任务（周六无其他任务，安全）
scheduler.add_job(archive_price_history, "cron", day_of_week="6", hour=12, minute=0, id="archive_price_history")
