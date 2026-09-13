import json,asyncio
from nonebot import require, get_bot, get_driver, on_command, on_notice
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageSegment,
    NoticeEvent,
)

matcher = on_notice()


@matcher.handle()
async def _(event: NoticeEvent):
    # print(event)
    notice_type = event.notice_type
    # print(notice_type)
    if notice_type == "group_increase":
        img_path = f"data/welcome/1.png"
        with open(img_path, "rb") as f:
            bytes_img = f.read()
        Msg = MessageSegment.image(bytes_img)
        await matcher.send(Msg)
        await asyncio.sleep(1)
        
        img_path = f"data/welcome/2.png"
        with open(img_path, "rb") as f:
            bytes_img = f.read()
        Msg = MessageSegment.image(bytes_img)
        await matcher.send(Msg)
        await asyncio.sleep(1)

        img_path = f"data/welcome/3.png"
        with open(img_path, "rb") as f:
            bytes_img = f.read()
        Msg = MessageSegment.image(bytes_img)
        await matcher.send(Msg)
