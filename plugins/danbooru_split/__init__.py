from nonebot import get_driver, on_message
from nonebot.params import EventPlainText
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from .config import Config
global_config = get_driver().config
config = Config.parse_obj(global_config)

matcher = on_message(priority=99)


@matcher.handle()
async def _(event: GroupMessageEvent, tag: str = EventPlainText()):
    tag = tag.replace("\r\n", "\n")
    if ("M\n? " in tag) | ("k\n? " in tag):
        tag_list = tag.split("\n")
        tag_all = ""
        for tag_single in tag_list:
            tag_info = tag_single.split(" ")
            tag_out, i = "", 1
            while i < len(tag_info)-1:
                tag_out = tag_out+" "+str(tag_info[i])
                i = i+1
            if tag_out != "":
                tag_all = tag_all+tag_out+","
        await matcher.send(tag_all.strip())
        return
    else:
        return
