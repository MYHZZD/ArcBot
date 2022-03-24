import json
import time
import math
from datetime import datetime
from nonebot import get_driver, on_message, on_command
from nonebot.params import EventPlainText, Command, CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config
global_config = get_driver().config
config = Config.parse_obj(global_config)

matcher = on_command("课程添加")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    uid = str(event.user_id)
    mess: str = str(foo)
    mess_list = mess.split()

    import os
    checkexdoc = os.path.exists("scheduledata/"+uid+".json")
    if checkexdoc == False:
        a = open("scheduledata/"+uid+".json", 'w')
        a.write('{}')
        a.close()

    name = mess_list[0]
    week_s = mess_list[1]
    week_e = mess_list[2]
    date = mess_list[3]
    loca = mess_list[4]

    classdata = {'起始周数': week_s, '结束周数': week_e,
                 '课程时间': date, '教室地址': loca}

    classhit = {name: classdata}

    datab = {}

    with open("scheduledata/"+uid+".json", "r", encoding='utf8') as readjson:
        dataa = readjson.readline()
        datab = json.loads(dataa)

    classhit.update(datab)

    with open("scheduledata/"+uid+".json", "w", encoding='utf8') as writejson:
        json.dump(classhit, writejson, ensure_ascii=False)
    await matcher.send("已记录课程 "+name+"")

matcher = on_message(priority=99)


@matcher.handle()
async def _(event: GroupMessageEvent, foo: str = EventPlainText()):
    uid = str(event.user_id)
    mess: str = str(foo)
    if mess != '今日课表':
        return

    t = '20220221'
    startday = int(time.mktime(time.strptime(t, "%Y%m%d")))

    today = time.time()
    weekpass = math.ceil((today-startday)/(7*24*3600))
    week = weekpass
    day = datetime.now().isoweekday()
    if day == 1:
        dayth = '一'
    if day == 2:
        dayth = '二'
    if day == 3:
        dayth = '三'
    if day == 4:
        dayth = '四'
    if day == 5:
        dayth = '五'
    if day == 6:
        dayth = '六'
    if day == 7:
        dayth = '日'
    output = '今天是星期%s，本学期第%s周 \n' % (dayth, week)

    import os
    checkexdoc = os.path.exists("scheduledata/"+uid+".json")
    if checkexdoc == True:
        with open("scheduledata/"+uid+".json", "r", encoding='utf8') as readjson:
            dataa = readjson.readline()
            datab = json.loads(dataa)

        pos = 1
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 2
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 3
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 4
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 5
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        await matcher.send(output)

matcher = on_message(priority=99)


@matcher.handle()
async def _(event: GroupMessageEvent, foo: str = EventPlainText()):
    uid = str(event.user_id)
    mess: str = str(foo)
    if mess != '明日课表':
        return

    t = '20220221'
    startday = int(time.mktime(time.strptime(t, "%Y%m%d")))

    today = time.time()
    weekpass = math.ceil((today-startday)/(7*24*3600))
    week = weekpass
    day = datetime.now().isoweekday()+1
    if day == 8:
        day = 1

    if day == 1:
        dayth = '一'
    if day == 2:
        dayth = '二'
    if day == 3:
        dayth = '三'
    if day == 4:
        dayth = '四'
    if day == 5:
        dayth = '五'
    if day == 6:
        dayth = '六'
    if day == 7:
        dayth = '日'
    output = '明天是星期%s，本学期第%s周 \n' % (dayth, week)

    import os
    checkexdoc = os.path.exists("scheduledata/"+uid+".json")
    if checkexdoc == True:
        with open("scheduledata/"+uid+".json", "r", encoding='utf8') as readjson:
            dataa = readjson.readline()
            datab = json.loads(dataa)

        pos = 1
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 2
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 3
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 4
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        pos = 5
        for key in datab:
            classdata = datab[""+key+""]
            classpos = '%s.%s' % (day, pos)
            if classpos in str(classdata['课程时间']) and week >= int(classdata['起始周数']) and week <= int(classdata['结束周数']):
                output += '第%s节大课 %s %s \n' % (pos,
                                               key, str(classdata['教室地址']))

        await matcher.send(output)