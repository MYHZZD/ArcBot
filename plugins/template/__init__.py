from nonebot import require, get_bot, on_command, get_driver
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageSegment,
    Event,
)


scheduler = require("nonebot_plugin_apscheduler").scheduler

GID = get_driver().config.testgid
UID = get_driver().config.testuid


async def ck1():  # 固定时间触发

    await get_bot().send_group_msg(group_id=GID, message="cron测试")


scheduler.add_job(ck1, "cron", hour="15", minute="0", id="ck1")


async def ck2():  # 固定间隔触发

    await get_bot().send_group_msg(group_id=GID, message="interval测试")


scheduler.add_job(ck2, "interval", hours=8, id="ck2")

ck3 = on_command("ck3", aliases={"CK3", "Ck3"}, priority=90, block=True)


@ck3.handle()  # 基本指令回复
async def ck3_function():
    await get_bot().send_group_msg(group_id=GID, message="CK3!")


ck4 = on_command("ck4", priority=90, block=False)


@ck4.handle()  # finish中止传递
async def ck3_function(args: Message = CommandArg()):
    if p_args := args.extract_plain_text():
        await get_bot().send_group_msg(group_id=GID, message="CK4!")
    else:
        await ck4.finish("ck4结束")
    await get_bot().send_group_msg(group_id=GID, message=" " + p_args)


ck4_1 = on_command("ck4", priority=91, block=True)


@ck4_1.handle()  # finish不会影响这里
async def ck4_1_function(args: Message = CommandArg()):
    p_args = args.extract_plain_text()
    await get_bot().send_group_msg(group_id=GID, message="ck4=" + p_args)


ck5 = on_command("ck5", priority=90, block=True)


@ck5.handle()  # 基础消息构造
async def ck5_function(args: Message = CommandArg()):
    message = Message(
        [
            MessageSegment.text("CK5="),
            MessageSegment.text(args.extract_plain_text()),
        ]
    )
    await get_bot().send_group_msg(group_id=GID, message=message)


ck6 = on_command("ck6", priority=90, block=True)


@ck6.handle()  # 基础消息构造
async def ck6_function():
    message = Message(
        [
            MessageSegment.text("CK6="),
            MessageSegment.face(5),
            MessageSegment.text("\n"),
            MessageSegment.at(3080492158),
            MessageSegment.text("\n"),
            MessageSegment.image(
                "https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png"
            ),
            MessageSegment.text("嘿嘿"),
        ]
    )
    await get_bot().send_group_msg(group_id=GID, message=message)


ck7 = on_command("ck7", priority=90, block=True)


@ck7.handle()  # 回复消息构造
async def ck7_function(event: GroupMessageEvent):
    mid = event.message_id
    uid = event.user_id
    gid = event.group_id
    message = Message(
        [
            MessageSegment.reply(mid),
            MessageSegment.text("UID=" + str(uid) + " "),
            MessageSegment.text("GID=" + str(gid) + "\n"),
            MessageSegment.image(
                "https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png"
            ),
        ]
    )
    await get_bot().send_group_msg(group_id=GID, message=message)


ck8 = on_command("ck8", priority=90, block=True)


@ck8.handle()  # classmethod
async def ck8_function(event: GroupMessageEvent, event2: Event):
    uid = event.user_id
    message = Message(
        [
            MessageSegment.text("UID=" + str(uid) + " or " + event2.get_user_id()),
        ]
    )
    await get_bot().send_private_msg(user_id=UID, message=message)


ck9 = on_command("ck9", priority=90, block=True)


@ck9.handle()  # 合并转发
async def ck9_function(event: GroupMessageEvent):

    uid = event.user_id
    mid = event.message_id
    message1 = Message(
        [
            # MessageSegment.node(mid),
            MessageSegment.node_custom(2591573409, "SuperUser", "手动构建消息方法1-1"),
            MessageSegment.node_custom(2591573409, "SuperUser", "手动构建消息方法1-2"),
        ]
    )

    await get_bot().send_group_forward_msg(
        group_id=GID, messages=message1
    )  # 注意messages

    message2 = [
        {
            "type": "node",
            "data": {
                "name": "SuperUser",
                "uin": 2591573409,
                "content": "手动构建消息方法2-1",
            },
        },
        {
            "type": "node",
            "data": {
                "name": "SuperUser",
                "uin": 2591573409,
                "content": "手动构建消息方法2-2",
            },
        },
    ]

    await get_bot().call_api(
        "send_group_forward_msg",
        group_id=GID,
        messages=message2,
    )
