from nonebot import get_driver, on_message, on_command, on_keyword
from nonebot.params import EventMessage, EventPlainText, Command, CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config
global_config = get_driver().config
config = Config.parse_obj(global_config)

matcher = on_command("学习")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    mess: str = str(foo)
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    import os
    checkexdir = os.path.exists("replydata/"+gid)
    if checkexdir == False:
        os.makedirs("replydata/"+gid)
    checkexdoc = os.path.exists("replydata/"+gid+"/"+mess_list[0]+".json")
    if checkexdoc == True:
        await matcher.send("已经存在由 "+mess_list[0]+" 启动的对话，请删除原对话后添加~")
        return
    with open("replydata/"+gid+"/"+mess_list[0]+".json", "w") as writemess:
        writemess.write(""+mess_list[1]+"")
    await matcher.send('爱尔学会啦~')

matcher = on_command("删除")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    mess: str = str(foo)
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    import os
    checkexdoc = os.path.exists("replydata/"+gid+"/"+mess_list[0]+".json")
    if checkexdoc == False:
        await matcher.send("笨蛋!不存在这种对话哦")
        return
    os.remove("replydata/"+gid+"/"+mess_list[0]+".json")
    await matcher.send('已删除对话')

matcher = on_message()


@matcher.handle()
async def _(event: GroupMessageEvent, foo: str = EventPlainText()):
    mess: str = str(foo)
    gid = str(event.group_id)
    import os
    checkex: str = os.path.exists("replydata/"+gid+"/"+mess+".json")
    if checkex == True:
        with open("replydata/"+gid+"/"+mess+".json", "r") as readmess:
            mess2: str = readmess.read()
        await matcher.send(mess2)

matcher = on_message()


@matcher.handle()
async def _(mess: str = EventPlainText()):
    if mess == '老婆':
        await matcher.send('老公！')
    if mess == '和我结婚':
        await matcher.send('支持')
    if mess == '支持':
        await matcher.send('不行')
    if mess == '不行':
        await matcher.send('支持')


matcher = on_command("关键词")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    mess: str = str(foo)
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    import os
    checkexdir = os.path.exists("replydata/"+gid+"/keyword")
    if checkexdir == False:
        os.makedirs("replydata/"+gid+"/keyword")
    checkexdoc = os.path.exists(
        "replydata/"+gid+"/keyword/"+mess_list[0]+".json")
    if checkexdoc == True:
        await matcher.send("已经存在由 "+mess_list[0]+" 为关键词的对话，请删除原对话后添加~")
        return
    with open("replydata/"+gid+"/keyword/"+mess_list[0]+".json", "w") as writemess:
        writemess.write(""+mess_list[1]+"")
    await matcher.send('爱尔学会啦~')

matcher = on_command("关键词删除")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    mess: str = str(foo)
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    import os
    checkexdoc = os.path.exists(
        "replydata/"+gid+"/keyword/"+mess_list[0]+".json")
    if checkexdoc == False:
        await matcher.send("笨蛋!不存在这种对话哦")
        return
    os.remove("replydata/"+gid+"/keyword/"+mess_list[0]+".json")
    await matcher.send('已删除对话')

matcher = on_message()


@matcher.handle()
async def _(event: GroupMessageEvent, foo: str = EventPlainText()):
    mess: str = str(foo)
    gid = str(event.group_id)
    import os
    checkexdir = os.path.exists("replydata/"+gid+"/keyword")
    if checkexdir == True:
        keylist = os.listdir("replydata/"+gid+"/keyword")
        for i in range(len(keylist)):
            keystr = str(keylist[i])
            keystr2 = keystr.rstrip('json')
            keystr3 = keystr2.rstrip('.')
            checkdel = '/关键词删除'
            if keystr3 in mess and checkdel not in mess:
                with open("replydata/"+gid+"/keyword/"+keystr+"", "r") as readmess:
                    mess2: str = readmess.read()
                await matcher.send(mess2)
