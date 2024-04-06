import requests
import time
import json
import os
import random
from nonebot import get_driver, on_message, on_command, get_bot
from nonebot.params import EventMessage, EventPlainText, CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment

from .config import Config
global_config = get_driver().config
config = Config.parse_obj(global_config)

jsonpath = "data/saying/"
jsonname = "data/saying/mappings.json"
checkexdir = os.path.exists(jsonpath)
if checkexdir == False:
    os.makedirs(jsonpath)
    startdata = {'Plugin': 'Created by MYHZZD'}
    with open(jsonname, "w", encoding='utf8') as writejson:
        json.dump(startdata, writejson, ensure_ascii=False)


def download_img(img_url, gid, img_name):
    filepath = "data/saying/"+gid
    checkexdir = os.path.exists(filepath)
    if checkexdir == False:
        os.makedirs(filepath)
    filename = "data/saying/"+gid+"/"+img_name
    header = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.53",
    }
    r = requests.get(img_url, headers=header, stream=True)
    if r.status_code == 200:
        open(filename, 'wb').write(r.content)
    del r


def mapping_table(gid, uid, img_name, who_said):
    unixtime = str(int(round(time.time() * 1000)))
    data_1 = {'Added By': uid, 'Group': gid,
              'Picture ID': img_name, 'Have sent': 'False'}
    data_2 = {'Who': who_said, 'Data': data_1}
    data_3 = {unixtime: data_2}
    with open(jsonname, "r", encoding='utf8') as readfile:
        jsondata: str = readfile.read()
        mappings = json.loads(jsondata)
    mappings.update(data_3)
    with open(jsonname, "w", encoding='utf8') as writejson:
        json.dump(mappings, writejson, ensure_ascii=False)


def mapping_table_del(img_name, who_del, gid):
    with open(jsonname, "r", encoding='utf8') as readfile:
        jsondata: str = readfile.read()
        mappings = json.loads(jsondata)

    for Key in mappings:
        if Key != 'Plugin':
            Data = mappings[Key]
            Data_2 = Data['Data']
            if img_name == Data_2['Picture ID'] and gid == Data_2['Group']:
                deldata = {'Del by': who_del}
                Data_2.update(deldata)
    with open(jsonname, "w", encoding='utf8') as writejson:
        json.dump(mappings, writejson, ensure_ascii=False)


matcher = on_command("名言")


@matcher.handle()
async def _(event: GroupMessageEvent, Mes: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    for arg in Mes:
        if arg.type == 'text':
            who_said = str(arg)

    check = str(event.reply)
    if check != 'None':
        mes_id = event.reply.message_id
        bot = get_bot()
        r_mes = await bot.get_msg(message_id=mes_id)
        #print(r_mes)
        img_url: str = r_mes['message'][0]['data']['url']
        img_name: str = r_mes['message'][0]['data']['file']
        download_img(img_url, gid, img_name)
        mapping_table(gid, uid, img_name, who_said)

    if check == 'None':
        for arg in Mes:
            if arg.type == 'image':
                img_url: str = arg.data['url']
                img_name: str = arg.data['file']
                download_img(img_url, gid, img_name)
                mapping_table(gid, uid, img_name, who_said)

    await matcher.send("已记录")

matcher = on_command("名言图片删除")


@matcher.handle()
async def _(event: GroupMessageEvent, Mes: Message = CommandArg()):
    gid = str(event.group_id)
    uid = str(event.user_id)

    for arg in Mes:
        if arg.type == 'image':
            img_name: str = arg.data['file']
            mapping_table_del(img_name, uid, gid)

    await matcher.send("已删除"+img_name+",请确保此为想删除的原图哦")


matcher = on_message(priority=99)


@matcher.handle()
async def _(event: GroupMessageEvent, Message: str = EventPlainText()):
    gid = str(event.group_id)

    if '说过' in Message:
        with open(jsonname, "r", encoding='utf8') as readfile:
            jsondata: str = readfile.read()
            mappings = json.loads(jsondata)

        pic = []
        for Key in mappings:
            if Key != 'Plugin':
                Data = mappings[Key]
                Data_2 = Data['Data']
                if Message in Data['Who'] and gid == Data_2['Group'] and 'False' == Data_2['Have sent'] and 'Del by' not in Data_2.keys():
                    pic.append(str(Data_2['Picture ID']))
        if len(pic) != 0:
            num = random.randint(0, len(pic)-1)
            img_path = f"/root/ArcBot/data/saying/"+gid+"/"+pic[num]
            with open(img_path, 'rb') as f:
                bytes_img = f.read()
            Msg = MessageSegment.image(bytes_img)
            await matcher.send(Msg)
            

        have_sent_num = 0
        havent_sent_num = 0
        for Key in mappings:
            if Key != 'Plugin':
                Data = mappings[Key]
                Data_2 = Data['Data']
                if len(pic) != 0:
                    if Message in Data['Who'] and gid == Data_2['Group'] and pic[num] == Data_2['Picture ID']:
                        Data_2['Have sent'] = 'True'
                if Message in Data['Who'] and gid == Data_2['Group'] and Data_2['Have sent'] == 'True' and 'Del by' not in Data_2.keys():
                    have_sent_num += 1
                if Message in Data['Who'] and gid == Data_2['Group'] and Data_2['Have sent'] == 'False' and 'Del by' not in Data_2.keys():
                    havent_sent_num += 1
        if havent_sent_num == 0 and have_sent_num > 0:
            for Key in mappings:
                if Key != 'Plugin':
                    Data = mappings[Key]
                    Data_2 = Data['Data']
                    if Message in Data['Who'] and gid == Data_2['Group']:
                        Data_2['Have sent'] = 'False'
        with open(jsonname, "w", encoding='utf8') as writejson:
            json.dump(mappings, writejson, ensure_ascii=False)


matcher = on_command("名言删除")


@matcher.handle()
async def _(event: GroupMessageEvent):
    gid = str(event.group_id)
    uid = str(event.user_id)

    check = str(event.reply)
    if check != 'None':
        mes_id = event.reply.message_id
        bot = get_bot()
        r_mes = await bot.get_msg(message_id=mes_id)
        img_name: str = r_mes['message'][0]['data']['file']
        mapping_table_del(img_name, uid, gid)

        img_path = f"/root/ArcBot/data/saying/"+gid+"/"+img_name
        with open(img_path, 'rb') as f:
             bytes_img = f.read()
        Msg = MessageSegment.image(bytes_img)
        await matcher.send("已删除"+Msg+",请确保此为想删除的原图哦")
