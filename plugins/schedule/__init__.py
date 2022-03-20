import json
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
        a = open("scheduledata/"+uid+".json",'w')
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
        dataa=readjson.readline()
        datab = json.loads(dataa)

    classhit.update(datab)

    with open("scheduledata/"+uid+".json", "w", encoding='utf8') as writejson:
        json.dump(classhit, writejson, ensure_ascii=False)
    await matcher.send("已记录课程 "+name+"")
