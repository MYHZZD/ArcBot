import re
import json
import os
from nonebot import on_command, get_bot, require
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU

scheduler = require("nonebot_plugin_apscheduler").scheduler


def parse_reminder(input_str):
    time_match = re.search(r"(凌晨|上午|下午|晚上|晚)?\d{1,2}点$", input_str)
    if not time_match:
        raise ValueError("未找到有效时间部分")
    time_str = time_match.group()
    date_str = input_str[: time_match.start()].strip()
    hour = parse_time(time_str)
    target_date = parse_date(date_str)
    target_datetime = datetime(
        target_date.year, target_date.month, target_date.day, hour
    )
    formatted_time = target_datetime.strftime("%Y年%m月%d日%H时")
    unix_time = int(target_datetime.timestamp())
    return formatted_time, unix_time


def parse_time(time_str):
    match = re.match(r"^(凌晨|上午|下午|晚上|晚)?(\d{1,2})点$", time_str)
    if not match:
        raise ValueError(f"无效的时间格式: {time_str}")
    period, hour_str = match.groups()
    hour = int(hour_str)

    if period in ("下午", "晚上", "晚"):
        if hour == 12:
            return 12
        return hour + 12
    elif period in ("上午", "凌晨"):
        if hour == 12 and period == "凌晨":
            return 0
        return hour
    else:
        if 0 <= hour < 24:
            return hour
        raise ValueError(f"无效的小时数: {hour}")


def parse_date(date_str):
    now = datetime.now()
    if not date_str:
        return now.date()

    # 绝对日期（优先匹配长形式）
    if m := re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$", date_str):
        return datetime(int(m[1]), int(m[2]), int(m[3])).date()
    if m := re.match(r"^(\d{1,2})月(\d{1,2})日$", date_str):
        return datetime(now.year, int(m[1]), int(m[2])).date()
    if m := re.match(r"^(\d{1,2})日$", date_str):
        return datetime(now.year, now.month, int(m[1])).date()

    # 相对年 + 月日
    if m := re.match(r"^(今年|明年)(\d{1,2})月(\d{1,2})日$", date_str):
        year = now.year + (1 if m[1] == "明年" else 0)
        return datetime(year, int(m[2]), int(m[3])).date()

    # 相对月 + 日
    if m := re.match(r"^(本月|下个月|下下个月)(\d{1,2})日$", date_str):
        months = {"本月": 0, "下个月": 1, "下下个月": 2}[m[1]]
        target = now + relativedelta(months=months)
        return datetime(target.year, target.month, int(m[2])).date()

    # 相对日期（包括星期）
    weekday_map = {
        "一": MO,
        "二": TU,
        "三": WE,
        "四": TH,
        "五": FR,
        "六": SA,
        "日": SU,
        "天": SU,
    }

    if m := re.match(r"^(本周|下周|下下周)([一二三四五六日天])$", date_str):
        base = {"本周": 0, "下周": 1, "下下周": 2}[m[1]]
        weekday = weekday_map[m[2]]
        # 找到本周一
        monday_this_week = now - timedelta(days=now.weekday())
        return (
            monday_this_week + relativedelta(weeks=base, weekday=weekday(+1))
        ).date()

    if m := re.match(r"^(今天|明天|后天|大后天)$", date_str):
        days = {"今天": 0, "明天": 1, "后天": 2, "大后天": 3}[m[1]]
        return (now + relativedelta(days=days)).date()

    raise ValueError(f"无法识别的日期格式: {date_str}")


def check_time(unixtime, now):
    dt_target = datetime.fromtimestamp(unixtime)

    # 要求目标时间必须大于现在时间，五分钟余量
    if dt_target + TOLERANCE <= now:
        return "none", 0

    for y in range(1, 5):
        expected = now + relativedelta(years=y)
        if abs(expected - dt_target) <= TOLERANCE:
            return "年", y

    for m in range(1, 12):
        expected = now + relativedelta(months=m)
        if abs(expected - dt_target) <= TOLERANCE:
            return "个月", m

    for w in range(1, 52):
        expected = now + timedelta(weeks=w)
        if abs(expected - dt_target) <= TOLERANCE:
            return "周", w

    for d in range(1, 14):
        expected = now + timedelta(days=d)
        if abs(expected - dt_target) <= TOLERANCE:
            return "天", d

    for h in range(1, 5):
        expected = now + timedelta(hours=h)
        if abs(expected - dt_target) <= TOLERANCE:
            return "小时", h

    if abs(now - dt_target) <= TOLERANCE:
        return "now", 0

    return "none", 0


helpdata = "/ddl 时间 事件\n记录仅精确到小时,标准输入格式示例:\n/ddl 2025年5月7日17点 B站发布静希草十郎节目\n事件可以使用12小时制:\n上午(凌晨)5点&下午(晚上/晚)5点\n日期同时接受以下写法:\n绝对日期(支持“5日”,“5月5日”,“2025年5月5日”)\n相对年(今年、明年)+月日\n相对月(本月、下个月、下下个月)+日\n相对日期(今天、明天、后天、大后天、本周一、下周三、下下周日)"
jsonname = "data/ddl/ddl.json"
os.makedirs(os.path.dirname(jsonname), exist_ok=True)
TOLERANCE = timedelta(minutes=5)


matcher = on_command("ddlhelp")


@matcher.handle()
async def _():
    await matcher.send(helpdata)


matcher = on_command("ddl")


@matcher.handle()
async def _(event: GroupMessageEvent, Mes: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    Mess = str(Mes).split(" ", 1)  # 只分割一次
    if len(Mess) < 2:
        Mess.append("未确定")

    try:
        formatted, unix = parse_reminder(Mess[0])
        for_time = f"{Mess[0]}({formatted}, Unix时间戳:{unix})"
        entry = {"unixtime": unix, "gid": gid, "uid": uid, "event": str(Mess[1])}

        if os.path.exists(jsonname):
            with open(jsonname, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []
        data.append(entry)

        with open(jsonname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    except Exception as e:
        for_time = f"{Mess[0]}(错误！{e})"

    await get_bot().send_group_msg(
        group_id=gid, message=Mess[1] + " 事件的DDL时间已被设置为" + for_time
    )


async def ddl():
    if os.path.exists(jsonname):
        now = datetime.now()
        with open(jsonname, "r", encoding="utf-8") as f:
            try:
                entries = json.load(f)
                for ent in entries:
                    ymwh, y_i = check_time(ent["unixtime"], now)
                    if ymwh == "now":
                        await get_bot().send_group_msg(
                            group_id=int(ent["gid"]),
                            message="事件 "
                            + ent["event"]
                            + " 的DDL到了喵!有没有完成呢~",
                        )
                    elif ymwh != "none":
                        await get_bot().send_group_msg(
                            group_id=int(ent["gid"]),
                            message="距离事件 "
                            + ent["event"]
                            + " 的DDL仅剩"
                            + str(y_i)
                            + str(ymwh)
                            + "了喵~加油！",
                        )

            except json.JSONDecodeError:
                data = []


scheduler.add_job(ddl, "cron", minute="0", id="ddl")
