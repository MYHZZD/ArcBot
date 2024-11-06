import asyncio
import random
import os
import json
from nonebot import require, get_bot, get_driver, on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent


scheduler = require("nonebot_plugin_apscheduler").scheduler

checkdir = os.path.exists("data/Morning")
if checkdir == False:
    os.makedirs("data/Morning")
checkdoc = os.path.exists("data/Morning/group.json")
if checkdoc == False:
    datag = {'group': '114514'}
    with open("data/Morning/group.json", "w", encoding='utf8') as writegroup:
        json.dump(datag, writegroup, ensure_ascii=False)


async def morning():
    await asyncio.sleep(random.randint(1, 5))
    with open("data/Morning/group.json", "r", encoding='utf8') as readgroup:
        jsondata: str = readgroup.read()
        groupdata = json.loads(jsondata)
        group = groupdata['group']
        grouplist = group.split()
    for i in range(len(grouplist)):
        if i != 0:
            await get_bot().send_group_msg(group_id=grouplist[i], message="早上好喵~新的一天也要开开心心喵~")
            await asyncio.sleep(random.randint(1, 5))

scheduler.add_job(morning, "cron", hour="7", minute="0", id="morning")


async def noon():
    await asyncio.sleep(random.randint(1, 5))
    with open("data/Morning/group.json", "r", encoding='utf8') as readgroup:
        jsondata: str = readgroup.read()
        groupdata = json.loads(jsondata)
        group = groupdata['group']
        grouplist = group.split()
    for i in range(len(grouplist)):
        if i != 0:
            await get_bot().send_group_msg(group_id=grouplist[i], message="午安喵~该吃午饭了喵~")
            await asyncio.sleep(random.randint(1, 5))

scheduler.add_job(noon, "cron", hour="11", minute="30", id="noon")


async def evening():
    await asyncio.sleep(random.randint(1, 5))
    with open("data/Morning/group.json", "r", encoding='utf8') as readgroup:
        jsondata: str = readgroup.read()
        groupdata = json.loads(jsondata)
        group = groupdata['group']
        grouplist = group.split()
    for i in range(len(grouplist)):
        if i != 0:
            await get_bot().send_group_msg(group_id=grouplist[i], message="十二点了喵，大家要早睡早起喵~")
            await asyncio.sleep(random.randint(1, 5))

scheduler.add_job(evening, "cron", hour="0", minute="0", id="evening")

matcher = on_command("Morning")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)

    with open("data/Morning/group.json", "r", encoding='utf8') as readgroup:
        jsondata: str = readgroup.read()
        groupdata = json.loads(jsondata)
        group = str(groupdata['group'])
        if gid not in group:
            group = group+" "+gid
    with open("data/Morning/group.json", "w", encoding='utf8') as writegroup:
        datag = {'group': group}
        json.dump(datag, writegroup, ensure_ascii=False)
    await matcher.send('已开启')

matcher = on_command("disMorning")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)

    with open("data/Morning/group.json", "r", encoding='utf8') as readgroup:
        jsondata: str = readgroup.read()
        groupdata = json.loads(jsondata)
        group = str(groupdata['group'])
        if gid in group:
            group = group.replace(' '+gid, '')
            group = group.replace('  ', ' ')
    with open("data/Morning/group.json", "w", encoding='utf8') as writegroup:
        datag = {'group': group}
        json.dump(datag, writegroup, ensure_ascii=False)
    await matcher.send('已关闭')