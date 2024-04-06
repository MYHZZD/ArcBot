import random
from nonebot import get_driver, on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .config import Config
global_config = get_driver().config
config = Config.parse_obj(global_config)

matcher = on_command("1d6")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    ans=str(random.randint(1,6))
    await matcher.send('本次1d6的结果为: '+ans)
    
matcher = on_command("1d20")


@matcher.handle()
async def _(event: GroupMessageEvent, foo: Message = CommandArg()):
    ans=str(random.randint(1,20))
    await matcher.send('本次1d20的结果为: '+ans)