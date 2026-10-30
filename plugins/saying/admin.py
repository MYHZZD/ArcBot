"""saying 本地查重 / 规则校验脚本（独立运行，不依赖 NoneBot）。

用法（在 plugins 目录下）：
    python saying/admin.py                  # 默认 dry-run
    python saying/admin.py --apply          # 执行修复

检查：
  1. Who 是否是“xx说过”格式；
  2. 文件名 stem 是否等于内容 MD5，扩展名是否与真实格式一致；
  3. 是否重复。

去重：
  - 同群 + 同人 + 同图：保留最早，合并 Have sent，其余移入 quotes_archive；
  - 同群 + 不同人 + 同图：两条都保留，只共用一份规范文件；
  - 跨群同图：永不合并。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from PIL import Image


def _load_storage():
    path = Path(__file__).with_name("storage.py")
    spec = importlib.util.spec_from_file_location("saying_storage", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


storage = _load_storage()

FORMAT_EXT = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp"}
MAX_SIZE = 20 * 1024 * 1024
RE_PIC = re.compile(r"^[0-9A-F]{32}\.(jpg|png|gif|webp)$")
TS_MIN = 1640995200000  # 2022-01-01
TS_MAX = int(time.time() * 1000) + 24 * 3600 * 1000


@dataclass
class FileInfo:
    path: Path
    size: int = 0
    md5: Optional[str] = None
    fmt: Optional[str] = None
    error: Optional[str] = None

    @property
    def ext(self) -> Optional[str]:
        return FORMAT_EXT.get(self.fmt or "")


@dataclass
class Report:
    total: int = 0
    deleted: int = 0
    active: int = 0
    groups: set[str] = field(default_factory=set)
    who_format: list[dict[str, Any]] = field(default_factory=list)
    field_errors: list[dict[str, Any]] = field(default_factory=list)
    missing: list[dict[str, Any]] = field(default_factory=list)
    unreadable: list[dict[str, Any]] = field(default_factory=list)
    oversize: list[dict[str, Any]] = field(default_factory=list)
    md5_mismatch: list[dict[str, Any]] = field(default_factory=list)
    ext_mismatch: list[dict[str, Any]] = field(default_factory=list)
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    same_image_diff_person: list[dict[str, Any]] = field(default_factory=list)
    cross_group: list[dict[str, Any]] = field(default_factory=list)
    orphans: list[dict[str, Any]] = field(default_factory=list)


def md5_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest().upper()


def inspect_file(path: Path) -> FileInfo:
    info = FileInfo(path=path)
    try:
        info.size = path.stat().st_size
        info.md5 = md5_file(path)
        with Image.open(path) as im:
            info.fmt = im.format
            im.verify()
        if info.size == 0:
            info.error = "zero size"
    except Exception as exc:
        info.error = str(exc)
    return info


def scan_files(images: Path) -> dict[tuple[str, str], FileInfo]:
    files: dict[tuple[str, str], FileInfo] = {}
    if not images.is_dir():
        return files
    for group_dir in images.iterdir():
        if not group_dir.is_dir() or not group_dir.name.isdigit():
            continue
        for path in group_dir.iterdir():
            if path.is_file():
                files[(group_dir.name, path.name)] = inspect_file(path)
    return files


def load_rows(db: Path) -> list[Any]:
    conn = storage.connect(db)
    try:
        return conn.execute("SELECT * FROM quotes ORDER BY created_at ASC, id ASC").fetchall()
    finally:
        conn.close()


def add(report: Report, bucket: list[dict[str, Any]], **kwargs: Any) -> None:
    bucket.append(kwargs)


def analyze(db: Path, images: Path) -> tuple[Report, dict[str, Any]]:
    report = Report()
    rows = load_rows(db)
    files = scan_files(images)
    report.total = len(rows)
    report.deleted = sum(1 for r in rows if r["deleted_by"] is not None)
    report.active = report.total - report.deleted
    report.groups = {str(r["group_id"]) for r in rows}

    row_file: dict[int, Optional[FileInfo]] = {}
    actual_md5: dict[int, Optional[str]] = {}
    canonical: dict[tuple[str, str], str] = {}  # (group, old_name) -> canonical
    row_target: dict[int, str] = {}
    bad_files: set[tuple[str, str]] = set()

    # 1. 记录字段校验
    for r in rows:
        rid = int(r["id"])
        who = str(r["who"])
        gid = str(r["group_id"])
        pid = str(r["picture_id"])
        if not (who.endswith("说过") and who == who.strip() and 3 <= len(who) <= 30):
            add(report, report.who_format, group=gid, who=who, picture_id=pid,
                detail="Who 不是“xx说过”格式")
        if not (str(r["added_by"]).isdigit() and 5 <= len(str(r["added_by"])) <= 12):
            add(report, report.field_errors, group=gid, who=who, picture_id=pid,
                detail=f"Added By 非法: {r['added_by']!r}")
        if not gid.isdigit():
            add(report, report.field_errors, group=gid, who=who, picture_id=pid,
                detail="Group 非法")
        if os.path.basename(pid) != pid or "/" in pid or "\\" in pid:
            add(report, report.field_errors, group=gid, who=who, picture_id=pid,
                detail="Picture ID 含路径")
        if r["have_sent"] not in (0, 1):
            add(report, report.field_errors, group=gid, who=who, picture_id=pid,
                detail=f"Have sent 非法: {r['have_sent']!r}")
        if r["deleted_by"] is not None and not (
            str(r["deleted_by"]).isdigit() and 5 <= len(str(r["deleted_by"])) <= 12
        ):
            add(report, report.field_errors, group=gid, who=who, picture_id=pid,
                detail=f"Del by 非法: {r['deleted_by']!r}")
        if not (TS_MIN <= int(r["created_at"]) <= TS_MAX):
            add(report, report.field_errors, group=gid, who=who, picture_id=pid,
                detail=f"时间戳超出范围: {r['created_at']}")

        info = files.get((gid, pid))
        row_file[rid] = info
        if info is None:
            add(report, report.missing, group=gid, who=who, picture_id=pid,
                detail="文件不存在")
            continue
        if info.error:
            add(report, report.unreadable, group=gid, who=who, picture_id=pid,
                detail=info.error)
            bad_files.add((gid, pid))
            continue
        if info.size > MAX_SIZE:
            add(report, report.oversize, group=gid, who=who, picture_id=pid,
                detail=f"文件过大: {info.size}")
        actual_md5[rid] = info.md5

        if info.md5 and os.path.splitext(pid)[0] != info.md5:
            add(report, report.md5_mismatch, group=gid, who=who, picture_id=pid,
                detail=f"文件名 stem 不是内容 MD5 ({info.md5})")
        if info.ext and os.path.splitext(pid)[1].lower() != info.ext:
            add(report, report.ext_mismatch, group=gid, who=who, picture_id=pid,
                detail=f"扩展名应为 {info.ext}，实际格式 {info.fmt}")

    # 2. 计算规范文件名：只归一行内被记录引用的文件，孤儿文件不重命名
    row_paths = {(str(r["group_id"]), str(r["picture_id"])) for r in rows}
    by_group_md5: dict[tuple[str, str], list[str]] = defaultdict(list)
    for (gid, name), info in files.items():
        if (gid, name) not in row_paths:
            continue
        if info.md5 and info.ext and not info.error:
            by_group_md5[(gid, info.md5)].append(name)

    trash_files: set[tuple[str, str]] = set(bad_files)
    renames: dict[tuple[str, str], str] = {}
    for (gid, md5), names in by_group_md5.items():
        info = files[(gid, names[0])]
        target = f"{md5}{info.ext}"
        canonical[(gid, target)] = target
        if target not in names:
            source = sorted(names)[0]
            renames[(gid, source)] = target
        for name in names:
            if name != target:
                if (gid, name) not in renames:
                    trash_files.add((gid, name))

    # 3. 行 -> 规范文件名
    for r in rows:
        rid = int(r["id"])
        gid = str(r["group_id"])
        pid = str(r["picture_id"])
        info = row_file.get(rid)
        if info is None or info.error or not info.md5 or not info.ext:
            continue
        target = f"{info.md5}{info.ext}"
        canonical[(gid, pid)] = target
        row_target[rid] = target
        if target != pid:
            renames.setdefault((gid, pid), target)

    # 4. 同群同人同图去重（仅活跃记录）
    groups: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    for r in rows:
        if r["deleted_by"] is not None:
            continue
        md5 = actual_md5.get(int(r["id"]))
        if not md5:
            continue
        groups[(str(r["group_id"]), str(r["who"]), md5)].append(r)

    archive_plan: dict[int, tuple[str, int]] = {}
    sent_updates: dict[int, int] = {}
    for key, items in groups.items():
        if len(items) <= 1:
            continue
        items_sorted = sorted(items, key=lambda r: (int(r["created_at"]), int(r["id"])))
        keep = items_sorted[0]
        if any(int(r["have_sent"]) for r in items_sorted):
            sent_updates[int(keep["id"])] = 1
        for extra in items_sorted[1:]:
            archive_plan[int(extra["id"])] = ("duplicate_same_person", int(keep["id"]))
            add(report, report.duplicates, group=key[0], who=key[1],
                picture_id=str(extra["picture_id"]), md5=key[2],
                detail=f"重复于 id={keep['id']}，保留最早")

    # 5. 同图不同人 / 跨群同图（只报告）
    gid_md5_who: dict[tuple[str, str], set[str]] = defaultdict(set)
    md5_groups: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r["deleted_by"] is not None:
            continue
        md5 = actual_md5.get(int(r["id"]))
        if not md5:
            continue
        gid = str(r["group_id"])
        gid_md5_who[(gid, md5)].add(str(r["who"]))
        md5_groups[md5].add(gid)
    for (gid, md5), whos in gid_md5_who.items():
        if len(whos) > 1:
            add(report, report.same_image_diff_person, group=gid, who=" / ".join(sorted(whos)),
                picture_id=f"{md5}", md5=md5, detail=f"同图不同人 {len(whos)} 人，保留")
    for md5, gids in md5_groups.items():
        if len(gids) > 1:
            add(report, report.cross_group, group=" / ".join(sorted(gids)), who="",
                picture_id=f"{md5}", md5=md5, detail=f"跨群同图 {len(gids)} 群，永不合并")

    # 6. 缺失 / 不可读：归档
    for r in rows:
        rid = int(r["id"])
        if rid in archive_plan:
            continue
        if rid in row_target or row_file.get(rid) is None:
            if row_file.get(rid) is None:
                archive_plan[rid] = ("missing_file", 0)
            continue
        info = row_file[rid]
        if info and info.error:
            archive_plan[rid] = ("unreadable", 0)

    # 7. 孤儿文件（所有记录，含已删除，都算引用）
    referenced: set[tuple[str, str]] = set()
    for r in rows:
        gid = str(r["group_id"])
        pid = str(r["picture_id"])
        target = row_target.get(int(r["id"]), pid)
        referenced.add((gid, target))
        referenced.add((gid, pid))
    for (gid, name), info in files.items():
        if (gid, name) not in referenced:
            add(report, report.orphans, group=gid, who="", picture_id=name,
                md5=info.md5 or "", detail=f"未被引用，{info.size} bytes")
            trash_files.add((gid, name))

    plan = {
        "rows": rows,
        "files": files,
        "row_target": row_target,
        "renames": renames,
        "trash_files": trash_files,
        "archive_plan": archive_plan,
        "sent_updates": sent_updates,
        "actual_md5": actual_md5,
        "canonical": canonical,
    }
    return report, plan


def print_report(report: Report) -> None:
    print("=" * 60)
    print("saying 查重 / 规则校验")
    print("=" * 60)
    print(f"总记录: {report.total}  活跃: {report.active}  已删除: {report.deleted}  群: {len(report.groups)}")
    print(f"Who 格式问题: {len(report.who_format)}")
    print(f"字段问题: {len(report.field_errors)}")
    print(f"缺失文件: {len(report.missing)}")
    print(f"不可读文件: {len(report.unreadable)}")
    print(f"超大文件: {len(report.oversize)}")
    print(f"MD5 文件名不符: {len(report.md5_mismatch)}")
    print(f"扩展名不符: {len(report.ext_mismatch)}")
    print(f"同人同图重复(多余): {len(report.duplicates)}")
    print(f"同图不同人: {len(report.same_image_diff_person)} 组")
    print(f"跨群同图: {len(report.cross_group)} 组")
    print(f"孤儿文件: {len(report.orphans)}")
    for title, items in (
        ("Who 格式", report.who_format),
        ("缺失", report.missing),
        ("不可读", report.unreadable),
        ("MD5 不符", report.md5_mismatch),
        ("扩展名不符", report.ext_mismatch),
        ("重复", report.duplicates),
        ("孤儿", report.orphans),
    ):
        if items:
            print(f"\n[{title}] 例:")
            for item in items[:5]:
                print(f"  {item}")


def write_csv(path: Path, report: Report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "group_id", "who", "picture_id", "md5", "detail", "action"])
        for cat, items in (
            ("who_format", report.who_format),
            ("field_error", report.field_errors),
            ("missing_file", report.missing),
            ("unreadable", report.unreadable),
            ("oversize", report.oversize),
            ("md5_mismatch", report.md5_mismatch),
            ("ext_mismatch", report.ext_mismatch),
            ("duplicate_same_person", report.duplicates),
            ("same_image_diff_person", report.same_image_diff_person),
            ("cross_group_same_image", report.cross_group),
            ("orphan_file", report.orphans),
        ):
            for item in items:
                w.writerow([
                    cat,
                    item.get("group", ""),
                    item.get("who", ""),
                    item.get("picture_id", ""),
                    item.get("md5", ""),
                    item.get("detail", ""),
                    "keep" if cat in ("same_image_diff_person", "cross_group_same_image", "who_format", "field_error") else "fix",
                ])


def move_to_trash(images: Path, trash: Path, gid: str, name: str) -> Optional[Path]:
    src = images / gid / name
    if not src.is_file():
        return None
    dst_dir = trash / gid
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / name
    if dst.exists():
        dst = dst_dir / f"{time.strftime('%H%M%S')}_{name}"
    shutil.move(str(src), str(dst))
    return dst


def apply(db: Path, images: Path, plan: dict[str, Any], report: Report) -> None:
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = images / "_backup"
    backup_dir.mkdir(exist_ok=True)
    backup = storage.backup_db(backup_dir / f"saying_{ts}.db", db)
    print(f"DB 备份: {backup}")

    trash = images / "_trash" / ts
    trash.mkdir(parents=True, exist_ok=True)
    undo: list[tuple[str, str, str]] = []

    try:
        # 先处理文件
        for (gid, old), new in sorted(plan["renames"].items()):
            src = images / gid / old
            dst = images / gid / new
            if not src.exists():
                continue
            if dst.exists():
                # 规范文件已存在，旧文件进回收站
                moved = move_to_trash(images, trash, gid, old)
                if moved:
                    undo.append(("trash", str(moved), str(src)))
            else:
                os.replace(src, dst)
                undo.append(("rename", str(src), str(dst)))

        for gid, name in sorted(plan["trash_files"]):
            moved = move_to_trash(images, trash, gid, name)
            if moved:
                undo.append(("trash", str(moved), str(images / gid / name)))

        # 再更新 DB
        conn = storage.connect(db)
        try:
            conn.execute("BEGIN")
            for rid, target in plan["row_target"].items():
                md5 = plan["actual_md5"].get(rid)
                conn.execute(
                    "UPDATE quotes SET picture_id=?, md5=? WHERE id=?",
                    (target, md5, rid),
                )
            for rid, sent in plan["sent_updates"].items():
                conn.execute("UPDATE quotes SET have_sent=? WHERE id=?", (sent, rid))
            conn.commit()
        finally:
            conn.close()

        for rid, (reason, kept) in plan["archive_plan"].items():
            storage.archive_quote(rid, reason, kept_id=kept or None, db_path=db)

        storage.ensure_unique_index(db)
    except Exception:
        print("执行失败，开始回滚文件操作……")
        for action, a, b in reversed(undo):
            try:
                if action == "rename":
                    if Path(b).exists():
                        os.replace(b, a)
                elif action == "trash":
                    if Path(a).exists():
                        Path(b).parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(a, b)
            except Exception as exc:
                print(f"  回滚失败: {action} {a} {b}: {exc}")
        try:
            for suffix in ("-wal", "-shm"):
                p = Path(str(db) + suffix)
                if p.exists():
                    p.unlink()
            shutil.copy2(backup, db)
            print(f"已从备份恢复 DB: {backup}")
        except Exception as exc:
            print(f"恢复 DB 失败，请手动使用 {backup}: {exc}")
        raise

    print(f"回收站: {trash}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=storage.DB_PATH)
    parser.add_argument("--images", type=Path, default=storage.SAYING_DIR)
    parser.add_argument("--apply", action="store_true", help="实际执行修复（默认 dry-run）")
    parser.add_argument("--report-dir", type=Path, default=None)
    args = parser.parse_args()

    if not args.db.is_file():
        print(f"DB 不存在: {args.db}", file=sys.stderr)
        return 2
    if not args.images.is_dir():
        print(f"图片目录不存在: {args.images}", file=sys.stderr)
        return 2

    storage.init_db(args.db, create_unique=False)
    report, plan = analyze(args.db, args.images)
    print_report(report)

    report_dir = args.report_dir or (args.images / "_reports")
    csv_path = report_dir / f"report_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    write_csv(csv_path, report)
    print(f"\nCSV 报告: {csv_path}")

    if not args.apply:
        print("\n当前为 dry-run；加 --apply 才会修改 DB/文件。")
        return 0

    print("\n注意：--apply 会修改 DB 和图片文件，建议先停止 Bot。")
    print("开始执行修复……")
    apply(args.db, args.images, plan, report)

    # 修复后再次校验
    report2, _ = analyze(args.db, args.images)
    print("\n" + "=" * 60)
    print("修复后校验")
    print("=" * 60)
    print_report(report2)
    ok = (
        len(report2.duplicates) == 0
        and len(report2.missing) == 0
        and len(report2.unreadable) == 0
        and len(report2.md5_mismatch) == 0
        and len(report2.ext_mismatch) == 0
        and len(report2.orphans) == 0
    )
    print(f"\n可自动修复项清零: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
