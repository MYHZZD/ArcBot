from nonebot import on_command
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment, Message
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.log import logger

import base64
from pathlib import Path

import httpx

from .builder import build_disguise_apng


__plugin_meta__ = PluginMetadata(
    name="bapng",
    description="将原图伪装成底图的 APNG 插件",
    usage="/bapng 原图 底图",
    type="application",
    supported_adapters={"~onebot.v11"},
)


bapng = on_command("bapng", priority=5, block=True)


async def _get_image_bytes(data: dict) -> bytes:
    """从 OneBot v11 的 image 消息段中获取图片字节"""
    url = data.get("url")
    file = data.get("file")

    for source in (url, file):
        if not source:
            continue

        # base64://
        if source.startswith("base64://"):
            return base64.b64decode(source[9:])

        # file://
        if source.startswith("file://"):
            return Path(source[7:]).read_bytes()

        # http(s)://
        if source.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(source)
                resp.raise_for_status()
                return resp.content

        # 本地路径
        p = Path(source)
        if p.exists():
            return p.read_bytes()

    raise ValueError("无法获取图片数据")


@bapng.handle()
async def handle_bapng(
    bot: Bot,
    event: MessageEvent,
    matcher: Matcher,
    args: Message = CommandArg(),
):
    # 取出命令后面的所有图片消息段，按发送顺序排列
    image_segments = [seg for seg in args if seg.type == "image"]

    if len(image_segments) < 2:
        await matcher.finish(
            "用法：/bapng 原图 底图\n"
            "请发送两张图片，第一张为原图，第二张为底图。"
        )

    original_seg = image_segments[0]
    thumb_seg = image_segments[1]

    try:
        original_bytes = await _get_image_bytes(original_seg.data)
        thumb_bytes = await _get_image_bytes(thumb_seg.data)
    except Exception as e:
        logger.exception("下载图片失败")
        await matcher.finish(f"下载图片失败：{e}")

    try:
        apng_bytes = build_disguise_apng(original_bytes, thumb_bytes)
    except Exception as e:
        logger.exception("生成 APNG 失败")
        await matcher.finish(f"生成伪装 APNG 失败：{e}")

    await matcher.finish(MessageSegment.image(apng_bytes))