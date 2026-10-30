"""saying：群内“XX说过”图片名言库。

运行时只使用 SQLite（data/saying/saying.db），不再读写 mappings.json。
图片仍保存在 data/saying/{group_id}/{picture_id}。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import httpx
from PIL import Image

from nonebot import get_driver, on_command, on_message
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventPlainText

from . import storage

FORMAT_EXT = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp"}
MAX_IMAGE_BYTES = int(os.getenv("SAYING_MAX_IMAGE_MB", "20")) * 1024 * 1024
DOWNLOAD_TIMEOUT = float(os.getenv("SAYING_DOWNLOAD_TIMEOUT", "30"))
SAYING_DIR = storage.SAYING_DIR
_pick_lock = asyncio.Lock()

_config = get_driver().config
GGID = {str(x) for x in (getattr(_config, "ggid", None) or [])}

storage.init_db(create_unique=False)
try:
    storage.ensure_unique_index()
except sqlite3.IntegrityError:
    logger.warning(
        "saying: 数据库中仍有重复记录，未创建唯一索引；请先运行 saying/admin.py --apply"
    )


def _is_valid_who(who: str) -> bool:
    if not who or who != who.strip():
        return False
    if not who.endswith("说过"):
        return False
    if not (3 <= len(who) <= 30):
        return False
    if any(ch in who for ch in "\r\n\t/\\"):
        return False
    return True


async def _fetch_image(source: Optional[str]) -> bytes:
    if not source:
        raise ValueError("图片地址为空")
    if source.startswith("base64://"):
        data = base64.b64decode(source[9:])
    elif source.startswith("file://"):
        parsed = urlparse(source)
        path = unquote(parsed.path)
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        data = Path(path).read_bytes()
    elif source.startswith(("http://", "https://")):
        async with httpx.AsyncClient(
            timeout=DOWNLOAD_TIMEOUT, follow_redirects=True
        ) as client:
            resp = await client.get(source)
            resp.raise_for_status()
            data = resp.content
    else:
        path = Path(source)
        if not path.is_file():
            raise ValueError("无法识别的图片地址")
        data = path.read_bytes()

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"图片超过 {MAX_IMAGE_BYTES // 1024 // 1024} MB")
    if not data:
        raise ValueError("图片为空")
    return data


def _validate_image(data: bytes) -> tuple[str, str, str]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except Exception as exc:
        raise ValueError(f"无法识别的图片: {exc}") from exc
    ext = FORMAT_EXT.get(fmt or "")
    if not ext:
        raise ValueError(f"不支持的图片格式: {fmt}")
    return fmt or "", ext, hashlib.md5(data).hexdigest().upper()


def _save_image(group_id: str, md5: str, ext: str, data: bytes) -> str:
    directory = SAYING_DIR / group_id
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{md5}{ext}"
    target = directory / name
    if target.is_file():
        if target.stat().st_size != len(data):
            raise ValueError("同名图片内容冲突")
        return name

    tmp = directory / f".{name}.tmp"
    tmp.write_bytes(data)
    os.replace(tmp, target)
    return name


async def _get_image_from_event(
    bot: Bot, event: GroupMessageEvent, args: Message
) -> bytes:
    """优先取被回复消息里的图，其次取当前消息里的图。"""
    if event.reply is not None:
        replied = await bot.get_msg(message_id=event.reply.message_id)
        for seg in replied.get("message", []):
            if seg.get("type") == "image":
                data = seg.get("data", {})
                return await _fetch_image(data.get("url") or data.get("file"))

    for seg in args:
        if seg.type == "image":
            source = seg.data.get("url") or seg.data.get("file")
            return await _fetch_image(source)

    raise ValueError("请附带一张图片，或回复一张图片")


learn = on_command("名言", priority=5, block=True)


@learn.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    matcher: Matcher,
    args: Message = CommandArg(),
):
    texts = [str(seg).strip() for seg in args if seg.type == "text"]
    who = " ".join(t for t in texts if t).strip()

    if not who:
        await matcher.finish("用法：/名言 日向说过，并附带一张图片或回复一张图片")
    if not _is_valid_who(who):
        await matcher.finish("名字需要是“xx说过”格式，例如：/名言 日向说过")

    try:
        data = await _get_image_from_event(bot, event, args)
        _, ext, md5 = _validate_image(data)
        picture_id = _save_image(str(event.group_id), md5, ext, data)
    except Exception as exc:
        logger.exception("名言图片处理失败")
        await matcher.finish(f"添加失败：{exc}")

    quote_id, inserted = storage.add_quote(
        created_at=int(time.time() * 1000),
        who=who,
        added_by=str(event.user_id),
        group_id=str(event.group_id),
        picture_id=picture_id,
        md5=md5,
        source="runtime",
    )
    if inserted:
        await matcher.finish("爱尔学会啦~")
    await matcher.finish("这张图已经记过啦~")


trigger = on_message(priority=99)


@trigger.handle()
async def _(
    event: GroupMessageEvent,
    matcher: Matcher,
    text: str = EventPlainText(),
):
    message = text.strip()
    if "说过" not in message:
        return

    gid = str(event.group_id)
    group_ids = sorted(GGID) if gid in GGID else [gid]

    async with _pick_lock:
        row = storage.pick_quote(group_ids, message)
        if row is None:
            return

        image_path = SAYING_DIR / str(row["group_id"]) / str(row["picture_id"])
        if not image_path.is_file():
            logger.warning(f"名言图片不存在: {image_path}")
            return

        storage.mark_sent(int(row["id"]))

    try:
        await matcher.send(MessageSegment.image(image_path.read_bytes()))
    except Exception:
        storage.mark_unsent(int(row["id"]))
        logger.exception("名言发送失败")


remove = on_command("名言删除", priority=5, block=True)


@remove.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    matcher: Matcher,
):
    if event.reply is None:
        await matcher.finish("请回复要删除的名言图片")

    replied = await bot.get_msg(message_id=event.reply.message_id)
    image_data = None
    for seg in replied.get("message", []):
        if seg.get("type") == "image":
            image_data = seg.get("data", {})
            break
    if not image_data:
        await matcher.finish("你回复的不是图片")

    picture_id = image_data.get("file")
    md5 = None
    try:
        raw = await _fetch_image(image_data.get("url") or picture_id)
        _, _, md5 = _validate_image(raw)
    except Exception:
        pass

    count = storage.delete_quote(
        group_id=str(event.group_id),
        deleted_by=str(event.user_id),
        picture_id=str(picture_id) if picture_id else None,
        md5=md5,
    )
    if count:
        await matcher.finish("已从本群删除")
    await matcher.finish("本群没有找到这张名言")


stat = on_command("名言统计", priority=5, block=True)


@stat.handle()
async def _(bot: Bot, event: GroupMessageEvent, matcher: Matcher):
    gid = str(event.group_id)
    global_mode = gid in GGID
    group_ids = sorted(GGID) if global_mode else [gid]
    rows, total = storage.stats(group_ids)

    title = "全局名言统计" if global_mode else "本群名言统计"
    if not rows:
        await matcher.finish(f"{title}：暂无名言")

    header = f"{title}（共 {total} 张 / {len(rows)} 人）"
    lines = [
        f"{index}. {row['who']}  {row['cnt']} 张"
        for index, row in enumerate(rows, start=1)
    ]

    if len(lines) <= 15:
        await matcher.send(header + "\n" + "\n".join(lines))
        return

    pages = [lines[i : i + 15] for i in range(0, len(lines), 15)]
    nodes = []
    for index, page in enumerate(pages, start=1):
        content = (header + "\n" if index == 1 else "") + "\n".join(page)
        if index == len(pages):
            content += f"\n【第{index}页-完】"
        else:
            content += f"\n【第{index}页】"
        nodes.append(
            {
                "type": "node",
                "data": {
                    "name": "名言统计",
                    "uin": bot.self_id,
                    "content": content,
                },
            }
        )

    try:
        await bot.send_group_forward_msg(group_id=event.group_id, messages=nodes)
    except Exception:
        logger.exception("名言统计合并转发失败，改为分段发送")
        for index, page in enumerate(pages, start=1):
            content = (header + "\n" if index == 1 else "") + "\n".join(page)
            await matcher.send(content)
