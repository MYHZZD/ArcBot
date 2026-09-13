# nonebot_plugin_bapng/builder.py
"""
APNG 伪装图构建核心逻辑（与 NoneBot 无关，可单独使用）
"""
import io
import struct
import zlib
from typing import Optional, Union

from PIL import Image

__all__ = ["build_disguise_apng", "strip_metadata", "PNG_SIGNATURE"]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_IDAT_LEN = 65536
DEFAULT_TEXT_MARK = b"ChatBarApngDisguise\x001;STATIC;1"


def png_chunk(chunk_type: str, data: bytes) -> bytes:
    """生成一个 PNG 数据块：长度 + 类型 + 数据 + CRC"""
    length = struct.pack(">L", len(data))
    type_bytes = chunk_type.encode("ascii")
    crc = struct.pack(">L", zlib.crc32(type_bytes + data) & 0xFFFFFFFF)
    return length + type_bytes + data + crc


def extract_png_chunks(img: Image.Image):
    """将 PIL Image 编码为 PNG 字节流，提取 IHDR 与合并后的 IDAT"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw = buf.getvalue()

    pos = 8  # 跳过 8 字节 PNG 签名
    ihdr: Optional[bytes] = None
    idat_list = []
    while pos < len(raw):
        length = struct.unpack(">L", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        cdata = raw[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            ihdr = cdata
        elif ctype == b"IDAT":
            idat_list.append(cdata)
        pos += 12 + length
        if ctype == b"IEND":
            break

    if ihdr is None:
        raise ValueError("无法从图像中提取 IHDR")
    return ihdr, b"".join(idat_list)


def split_data(data: bytes, max_len: int = MAX_IDAT_LEN):
    """按最大长度切分数据块"""
    return [data[i:i + max_len] for i in range(0, len(data), max_len)]


def strip_metadata(img: Image.Image) -> Image.Image:
    """元数据清理：alpha LSB 清零 + 全透明像素 RGB 置白"""
    img = img.convert("RGBA")
    pixels = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            a &= 0xFE          # 255 -> 254，半透明取偶
            if a == 0:
                r = g = b = 255
            pixels[x, y] = (r, g, b, a)
    return img


def _to_rgba_image(src: Union[str, bytes, bytearray, Image.Image]) -> Image.Image:
    """把 路径 / bytes / PIL.Image 统一转成 RGBA 图像"""
    if isinstance(src, Image.Image):
        img = src
    elif isinstance(src, (bytes, bytearray)):
        img = Image.open(io.BytesIO(bytes(src)))
    else:
        img = Image.open(src)
    return img.convert("RGBA")


def build_disguise_apng(
    original: Union[str, bytes, bytearray, Image.Image],
    thumb: Union[str, bytes, bytearray, Image.Image],
    *,
    delay_num: int = 10,
    delay_den: int = 100,
    text_mark: Optional[bytes] = DEFAULT_TEXT_MARK,
    output_path: Optional[str] = None,
    clean_metadata: bool = True,
) -> bytes:
    """
    构建伪装 APNG。

    :param original: 原图（会被藏进动画帧里）
    :param thumb:    底图（作为默认静态图像，同时被拉伸到原图尺寸）
    :param delay_num / delay_den: 帧延迟，10/100 即 0.1 秒
    :param text_mark: 写入 tEXt 的关键标记，传 None 则跳过
    :param output_path: 若给出则同时写入文件
    :param clean_metadata: 是否做 alpha LSB 清理
    :return: APNG 字节流
    """
    original_img = _to_rgba_image(original)
    thumb_img = _to_rgba_image(thumb)

    # 统一尺寸（以原图尺寸为准）
    width, height = original_img.size
    if thumb_img.size != (width, height):
        thumb_img = thumb_img.resize((width, height), Image.Resampling.LANCZOS)

    if clean_metadata:
        thumb_img = strip_metadata(thumb_img)
        original_img = strip_metadata(original_img)

    # 默认图像（静态可见）用底图，动画帧用原图
    ihdr_data, idat_thumb = extract_png_chunks(thumb_img)
    _, idat_original = extract_png_chunks(original_img)

    # 微调原图作为第二帧，避免两帧数据完全一致被优化掉
    nudged = original_img.copy()
    r, g, b, a = nudged.getpixel((0, 0))
    nudged.putpixel((0, 0), (r, g, b, a ^ 1))
    _, idat_nudged = extract_png_chunks(nudged)

    chunks = [png_chunk("IHDR", ihdr_data)]

    # acTL: 2 帧，num_plays=0 表示无限循环
    chunks.append(png_chunk("acTL", struct.pack(">LL", 2, 0)))

    if text_mark:
        chunks.append(png_chunk("tEXt", text_mark))

    # 默认图像 IDAT（底图）
    for part in split_data(idat_thumb):
        chunks.append(png_chunk("IDAT", part))

    seq = 0
    for frame_data in (idat_original, idat_nudged):
        # fcTL: seq / w / h / x / y / delay_num / delay_den / dispose / blend
        fctl = struct.pack(
            ">LLLLLHHBB",
            seq, width, height, 0, 0,
            delay_num, delay_den,
            0,  # dispose_op = NONE
            0,  # blend_op   = SOURCE
        )
        chunks.append(png_chunk("fcTL", fctl))
        seq += 1

        for part in split_data(frame_data):
            chunks.append(png_chunk("fdAT", struct.pack(">L", seq) + part))
            seq += 1

    chunks.append(png_chunk("IEND", b""))

    result = PNG_SIGNATURE + b"".join(chunks)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(result)

    return result