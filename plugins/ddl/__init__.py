import re
import json
import os
from nonebot import on_command, get_bot, require
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO

scheduler = require("nonebot_plugin_apscheduler").scheduler


def parse_reminder(input_str):
    # 用正则表达式分割时间部分（支持"13点"/"下午3点"/"上午10点"等格式）
    time_match = re.search(
        r"((\d{1,2}点(上午|下午)?)|((上午|下午)\d{1,2}点))$", input_str
    )
    if not time_match:
        raise ValueError("未找到有效时间部分")
    time_str = time_match.group()
    date_str = input_str[: time_match.start()].strip()  # 提取日期部分

    # 解析时间部分为24小时制的小时数
    hour = parse_time(time_str)

    # 解析日期部分为datetime.date对象
    target_date = parse_date(date_str)

    # 组合日期和时间生成最终结果
    target_datetime = datetime(
        target_date.year, target_date.month, target_date.day, hour
    )
    formatted_time = target_datetime.strftime("%Y年%m月%d日%H时")  # 格式化为标准输出
    unix_time = int(target_datetime.timestamp())  # 转换为Unix时间戳
    return formatted_time, unix_time


def parse_time(time_str):
    # 匹配两种格式：1) 数字+点+上午/下午  2) 上午/下午+数字+点
    hour_pattern = re.compile(r"^(?:(\d{1,2})点(上午|下午)?|(上午|下午)(\d{1,2})点)$")
    match = hour_pattern.match(time_str)
    if not match:
        raise ValueError(f"无效的时间格式: {time_str}")

    groups = match.groups()
    hour_str, am_pm_before, am_pm_after, hour_str_after = groups

    # 根据匹配结果提取小时和上午/下午标识
    if hour_str:
        hour = int(hour_str)
        am_pm = am_pm_before  # 第一种格式（如"3点下午"）
    else:
        hour = int(hour_str_after)
        am_pm = am_pm_after  # 第二种格式（如"下午3点"）

    # 处理上午/下午转换为24小时制
    if am_pm == "下午":
        if hour == 12:  # 下午12点转为0点
            return 0
        else:  # 其他下午时间加12
            return hour + 12
    elif am_pm == "上午":
        if hour == 12:  # 上午12点保持12
            return 12
        else:  # 其他上午时间保持不变
            return hour
    else:  # 没有上午/下午说明是24小时制
        if 0 <= hour < 24:
            return hour
        raise ValueError(f"无效的小时: {hour}")


def parse_date(date_str):
    now = datetime.now()
    if not date_str:  # 无日期部分默认为今天
        return now.date()

    # 模式1：绝对日期（如"2025年6月1日"）
    if match := re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$", date_str):
        year, month, day = map(int, match.groups())
        try:
            return datetime(year, month, day).date()
        except ValueError:
            raise ValueError(f"无效的日期: {date_str}")

    # 模式2：相对年/月+具体月日（如"明年5月10日"）
    if match := re.match(r"^(明年|下个月|下下个月)(\d{1,2})月(\d{1,2})日$", date_str):
        relative_term, month, day = (
            match.group(1),
            int(match.group(2)),
            int(match.group(3)),
        )
        base_date = now
        # 计算基准年/月
        if relative_term == "明年":
            base_date += relativedelta(years=1)
        elif relative_term == "下个月":
            base_date += relativedelta(months=1)
        elif relative_term == "下下个月":
            base_date += relativedelta(months=2)
        try:
            # 注意：这里使用replace确保不跨年（如12月+1个月时）
            return base_date.replace(month=month, day=day).date()
        except:
            raise ValueError(f"无效的日期: {month}月{day}日")

    # 模式3：相对月+日（如"下个月5日"）
    if match := re.match(r"^(下个月|下下个月)(\d{1,2})日$", date_str):
        relative_term, day = match.group(1), int(match.group(2))
        months = 1 if relative_term == "下个月" else 2
        try:
            return (now + relativedelta(months=months, day=day)).date()
        except:
            raise ValueError(f"无效的日期: {day}日")

    # 模式4：相对日期关键词（新增下下周一、后天、大后天）
    if match := re.match(r"^(下周一|下下周一|明天|今天|后天|大后天)$", date_str):
        relative_term = match.group(1)
        if relative_term == "下周一":
            return (now + relativedelta(weekday=MO(+1))).date()  # 找到下一个周一
        elif relative_term == "下下周一":
            return (now + relativedelta(weekday=MO(+2))).date()  # 找到下下个周一
        elif relative_term == "明天":
            return (now + relativedelta(days=1)).date()
        elif relative_term == "今天":
            return now.date()
        elif relative_term == "后天":
            return (now + relativedelta(days=2)).date()
        elif relative_term == "大后天":
            return (now + relativedelta(days=3)).date()

    # 模式5：简单相对月（如"下个月"）
    if match := re.match(r"^(下个月|下下个月)$", date_str):
        months = 1 if match.group(1) == "下个月" else 2
        return (now + relativedelta(months=months)).date()

    raise ValueError(f"无法识别的日期格式: {date_str}")


def check_time(unixtime, now):
    dt_target = datetime.fromtimestamp(unixtime)

    # 要求目标时间必须大于现在时间
    if dt_target <= now:
        return "none", 0

    for y in range(1, 11):
        expected = now + relativedelta(years=y)
        if abs(expected - dt_target) <= TOLERANCE:
            return "年", y

    for m in range(1, 12):
        expected = now + relativedelta(months=m)
        if abs(expected - dt_target) <= TOLERANCE:
            return "个月", m

    for w in range(1, 5):
        expected = now + timedelta(weeks=w)
        if abs(expected - dt_target) <= TOLERANCE:
            return "周", w

    for d in range(1, 7):
        expected = now + timedelta(days=d)
        if abs(expected - dt_target) <= TOLERANCE:
            return "天", d

    for h in range(1, 23):
        expected = now + timedelta(hours=h)
        if abs(expected - dt_target) <= TOLERANCE:
            return "小时", h

    if abs(now - dt_target) <= TOLERANCE:
        return "now", 0

    return "none", 0


helpdata = "记录仅精确到小时，标准输入格式示例：2025年5月7日17点。\n可以使用12小时制：上午5点&下午5点\n日期同时接受以下写法：明年、下个月、下下个月、下周一、下下周三、明天、后天、大后天"
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
        Mess.append("未确定")  # 补全为空字符串

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


async def ddl():  # 固定间隔触发
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
                            message="事件" + ent["event"] + "的DDL到了喵!有没有完成呢~",
                        )
                    if ymwh != "none":
                        await get_bot().send_group_msg(
                            group_id=int(ent["gid"]),
                            message="距离事件"
                            + ent["event"]
                            + "的DDL仅剩"
                            + str(y_i)
                            + str(ymwh)
                            + "了喵~加油！",
                        )

            except json.JSONDecodeError:
                data = []


scheduler.add_job(ddl, "cron", minute="0", id="ddl")
