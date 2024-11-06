import json
import os
from nonebot import get_driver, on_message, on_command, on_keyword
from nonebot.params import EventMessage, EventPlainText, Command, CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

matcher = on_command("学习")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        await matcher.send("本群未启用此功能，详情请查阅BOT文档！")
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        await matcher.send('您已被封禁，无权使用此功能')
        return

    mess: str = str(foo)
    if mess == '':
        return
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    checkexdir = os.path.exists("replydata/"+gid)
    if checkexdir == False:
        os.makedirs("replydata/"+gid)
    checkexdoc = os.path.exists("replydata/"+gid+"/"+mess_list[0]+".json")
    if checkexdoc == True:
        await matcher.send("已经存在由 "+mess_list[0]+" 启动的对话，请删除原对话后添加~")
        return
    messwin = ''
    for i in range(len(mess_list)):
        if i != 0:
            messwin2 = messwin+mess_list[i]+' '
            messwin = messwin2
    messwin2 = messwin2.rstrip(' ')
    mess_dic = {'message': messwin2, 'uploader': uid}
    with open("replydata/"+gid+"/"+mess_list[0]+".json", "w", encoding='utf8') as writemess:
        json.dump(mess_dic, writemess, ensure_ascii=False)
    await matcher.send('爱尔学会啦~')

matcher = on_command("删除")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        await matcher.send("本群未启用此功能，详情请查阅BOT文档！")
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        await matcher.send('您已被封禁，无权使用此功能')
        return

    mess: str = str(foo)
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    checkexdoc = os.path.exists("replydata/"+gid+"/"+mess_list[0]+".json")
    if checkexdoc == False:
        await matcher.send("笨蛋!不存在这种对话哦")
        return
    os.remove("replydata/"+gid+"/"+mess_list[0]+".json")
    await matcher.send('已删除对话')

matcher = on_message(priority=99)


@matcher.handle()
async def _(event: GroupMessageEvent, foo: str = EventPlainText()):
    mess: str = str(foo)
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        return

    checkex: str = os.path.exists("replydata/"+gid+"/"+mess+".json")
    if checkex == True:
        with open("replydata/"+gid+"/"+mess+".json", "r", encoding='utf8') as readmess:
            mess2: str = readmess.read()
            mess_dic = json.loads(mess2)
            mess3 = mess_dic['message']

            if mess_dic['uploader'] in bannedlist:
                return

        await matcher.send(mess3)

matcher = on_message(priority=99)


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
    if mess == 'bot使用说明':
        await matcher.send('前往gayhub https://github.com/MYHZZD/ArcBot/blob/main/README.md 欢迎提issue哦')


matcher = on_command("关键词")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        await matcher.send("本群未启用此功能，详情请查阅BOT文档！")
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        await matcher.send('您已被封禁，无权使用此功能')
        return

    mess: str = str(foo)
    if mess == '':
        return
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    checkexdir = os.path.exists("replydata/"+gid+"/keyword")
    if checkexdir == False:
        os.makedirs("replydata/"+gid+"/keyword")
    checkexdoc = os.path.exists(
        "replydata/"+gid+"/keyword/"+mess_list[0]+".json")
    if checkexdoc == True:
        await matcher.send("已经存在由 "+mess_list[0]+" 为关键词的对话，请删除原对话后添加~")
        return
    messwin = ''
    for i in range(len(mess_list)):
        if i != 0:
            messwin2 = messwin+mess_list[i]+' '
            messwin = messwin2
    messwin2 = messwin2.rstrip(' ')
    mess_dic = {'message': messwin2, 'uploader': uid}
    with open("replydata/"+gid+"/keyword/"+mess_list[0]+".json", "w", encoding='utf8') as writemess:
        json.dump(mess_dic, writemess, ensure_ascii=False)
    await matcher.send('爱尔学会啦~')

matcher = on_command("关键词删除")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        await matcher.send("本群未启用此功能，详情请查阅BOT文档！")
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        await matcher.send('您已被封禁，无权使用此功能')
        return

    mess: str = str(foo)
    mess_list = mess.split()
    if mess_list[0].replace('.\\', ' ') != mess_list[0] or mess_list[0].replace('./', ' ') != mess_list[0]:
        await matcher.send('输入非法字符!参数不能带有 / \ . 等符号')
        return
    checkexdoc = os.path.exists(
        "replydata/"+gid+"/keyword/"+mess_list[0]+".json")
    if checkexdoc == False:
        await matcher.send("笨蛋!不存在这种对话哦")
        return
    os.remove("replydata/"+gid+"/keyword/"+mess_list[0]+".json")
    await matcher.send('已删除对话')

matcher = on_message(priority=99)


@matcher.handle()
async def _(event: GroupMessageEvent, foo: str = EventPlainText()):
    mess: str = str(foo)
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        return

    checkexdir = os.path.exists("replydata/"+gid+"/keyword")
    if checkexdir == True:
        keylist = os.listdir("replydata/"+gid+"/keyword")
        for i in range(len(keylist)):
            keystr = str(keylist[i])
            keystr2 = keystr.rstrip('json')
            keystr3 = keystr2.rstrip('.')
            checkdel1 = '/关键词删除'
            checkadd1 = '/关键词'
            checkdel2 = '/学习'
            checkadd2 = '/删除'
            if keystr3 in mess and checkdel1 not in mess and checkadd1 not in mess and checkdel2 not in mess and checkadd2 not in mess:
                checkexdoc = os.path.exists("replydata/"+gid+"/"+keystr+"")
                if checkexdoc == True and keystr3 == mess:
                    return
                with open("replydata/"+gid+"/keyword/"+keystr+"", "r", encoding='utf8') as readmess:
                    mess2: str = readmess.read()
                    mess_dic = json.loads(mess2)
                    mess3 = mess_dic['message']

                    if mess_dic['uploader'] in bannedlist:
                        return

                await matcher.send(mess3)


matcher = on_command("学习列表")


@matcher.handle()
async def _(event: GroupMessageEvent):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        await matcher.send("本群未启用此功能，详情请查阅BOT文档！")
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        await matcher.send('您已被封禁，无权使用此功能')
        return

    checkexdir = os.path.exists("replydata/"+gid+"")
    if checkexdir == True:
        keylist = os.listdir("replydata/"+gid+"")
        sendmess = ''
        for i in range(len(keylist)):
            keystr = str(keylist[i])
            keystr2 = keystr.rstrip('json')
            keystr3 = keystr2.rstrip('.')
            if keystr3 != 'keyword':

                with open("replydata/"+gid+"/"+keystr+"", "r", encoding='utf8') as readmess:
                    mess_dic = json.load(readmess)
                    if mess_dic['uploader'] in bannedlist:
                        keystr3 = keystr3+'[已屏蔽]'

                keystr4 = sendmess+keystr3+'  '
                sendmess = keystr4
        if sendmess != '':
            await matcher.send(sendmess)
        else:
            await matcher.send('本群暂无被学习的对话')


matcher = on_command("关键词列表")


@matcher.handle()
async def _(event: GroupMessageEvent):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")
    checkperdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkperdoc == False:
        await matcher.send("本群未启用此功能，详情请查阅BOT文档！")
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in bannedlist:
        await matcher.send('您已被封禁，无权使用此功能')
        return

    checkexdir = os.path.exists("replydata/"+gid+"/keyword")
    if checkexdir == True:
        keylist = os.listdir("replydata/"+gid+"/keyword")
        sendmess = ''
        for i in range(len(keylist)):
            keystr = str(keylist[i])
            keystr2 = keystr.rstrip('json')
            keystr3 = keystr2.rstrip('.')

            with open("replydata/"+gid+"/keyword/"+keystr+"", "r", encoding='utf8') as readmess:
                mess_dic = json.load(readmess)
                if mess_dic['uploader'] in bannedlist:
                    keystr3 = keystr3+'[已屏蔽]'

            keystr4 = sendmess+keystr3+'  '
            sendmess = keystr4
        if sendmess != '':
            await matcher.send(sendmess)
        else:
            await matcher.send('本群暂无关键词')

matcher = on_command("启用回复功能")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")

    checkexdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkexdoc == True:
        await matcher.send('此功能已启用')
        return
    checkexdoc = os.path.exists("permissiondata/"+gid+".json.disabled")
    if checkexdoc == False:
        permissiondata = {'admin': uid, 'banned': '114514'}
        with open("permissiondata/"+gid+".json", "w", encoding='utf8') as writemess:
            json.dump(permissiondata, writemess, ensure_ascii=False)
        await matcher.send('启用成功')
    if checkexdoc == True:
        with open("permissiondata/"+gid+".json.disabled", "r", encoding='utf8') as readprem:
            prem0: str = readprem.read()
            prem = json.loads(prem0)
            adminlist = str(prem['admin'])
            bannedlist = str(prem['banned'])
        if uid not in adminlist:
            await matcher.send('您无权使用此功能')
            return
        os.rename("permissiondata/"+gid+".json.disabled",
                  "permissiondata/"+gid+".json")
        await matcher.send('启用成功')

matcher = on_command("禁用回复功能")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")

    checkexdoc = os.path.exists("permissiondata/"+gid+".json.disable")
    if checkexdoc == True:
        await matcher.send('此功能已禁用')
        return
    checkexdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkexdoc == False:
        await matcher.send('本群未开启此功能')
    if checkexdoc == True:
        with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
            prem0: str = readprem.read()
            prem = json.loads(prem0)
            adminlist = str(prem['admin'])
            bannedlist = str(prem['banned'])
        if uid not in adminlist:
            await matcher.send('您无权使用此功能')
            return
        os.rename("permissiondata/"+gid+".json",
                  "permissiondata/"+gid+".json.disabled")
        await matcher.send('禁用成功')

matcher = on_command("添加管理员")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")

    checkexdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkexdoc == False:
        await matcher.send('本群未开启此功能或已禁用')
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in adminlist:
        adminlist += str(','+foo)
        premnew = {'admin': adminlist, 'banned': bannedlist}
        with open("permissiondata/"+gid+".json", "w", encoding='utf8') as writeprem:
            json.dump(premnew, writeprem, ensure_ascii=False)
        await matcher.send('已添加')
    else:
        await matcher.send('您无权使用此功能')

matcher = on_command("封禁")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    checkperdir = os.path.exists("permissiondata")
    if checkperdir == False:
        os.makedirs("permissiondata")

    checkexdoc = os.path.exists("permissiondata/"+gid+".json")
    if checkexdoc == False:
        await matcher.send('本群未开启此功能或已禁用')
        return
    with open("permissiondata/"+gid+".json", "r", encoding='utf8') as readprem:
        prem0: str = readprem.read()
        prem = json.loads(prem0)
        adminlist = str(prem['admin'])
        bannedlist = str(prem['banned'])
    if uid in adminlist:
        bannedlist += str(','+foo)
        premnew = {'admin': adminlist, 'banned': bannedlist}
        with open("permissiondata/"+gid+".json", "w", encoding='utf8') as writeprem:
            json.dump(premnew, writeprem, ensure_ascii=False)
        await matcher.send('已封禁')
    else:
        await matcher.send('您无权使用此功能')