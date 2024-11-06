import asyncio
import random
from nonebot import get_driver, on_keyword
from nonebot.adapters import Message, Event
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.matcher import current_bot, current_event

test = on_keyword({"/绘图","/分析"}, block=False)


@test.handle()
async def _(bot: Bot, event: MessageEvent):
    mess_id = current_event.get().message_id
    try:
        await asyncio.sleep(random.randint(1, 5))
        await current_bot.get().delete_msg(message_id=mess_id)
    except:
        print("撤回失败，可能是bot权限不够导致")
