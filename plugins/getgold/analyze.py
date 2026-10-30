"""getgold 离线分析：直接读取 data/getgold/getgold.db。

用法：
    python getgold/analyze.py
    python getgold/analyze.py --days 7
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = Path(os.getenv("GETGOLD_DB", PROJECT_ROOT / "data" / "getgold" / "getgold.db"))
WINDOW_SIZE = 15  # 区间窗口大小


def load_history(db_path: Path, days: int | None = None):
    """加载价格历史，返回 [{'time': float, 'price': float}, ...]。"""
    if not db_path.is_file():
        raise FileNotFoundError(f"数据库不存在: {db_path}")
    conn = sqlite3.connect(str(db_path))
    try:
        sql = "SELECT ts, price FROM prices"
        params: list[float] = []
        if days is not None:
            cutoff = datetime.now().timestamp() - days * 86400
            sql += " WHERE ts >= ?"
            params.append(cutoff)
        sql += " ORDER BY ts ASC, id ASC"
        rows = conn.execute(sql, params).fetchall()
        return [{"time": float(r[0]), "price": float(r[1])} for r in rows]
    finally:
        conn.close()


def format_time(timestamp):
    """将时间戳转为可读字符串"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def analyze_extremes(history):
    """
    分析价格极值：
      - 单次最大涨跌幅（相邻两点）
      - 区间最大涨跌幅（窗口内首尾）
    """
    prices = []
    times = []
    for record in history:
        if "price" in record and record["price"] is not None:
            prices.append(float(record["price"]))
            times.append(record.get("time", 0))

    if len(prices) < 2:
        print("数据点不足，至少需要 2 条记录。")
        return

    single_changes = []
    for i in range(1, len(prices)):
        p_prev = prices[i - 1]
        p_curr = prices[i]
        if p_prev == 0:
            continue
        change_per_mille = (p_curr - p_prev) / p_prev * 1000
        single_changes.append((change_per_mille, times[i - 1], times[i]))

    if not single_changes:
        print("没有可计算的相邻变化。")
        return

    max_increase = max(single_changes, key=lambda x: x[0])
    max_decrease = min(single_changes, key=lambda x: x[0])

    interval_changes = []
    for i in range(len(prices) - WINDOW_SIZE):
        p_start = prices[i]
        p_end = prices[i + WINDOW_SIZE]
        if p_start == 0:
            continue
        change_per_mille = (p_end - p_start) / p_start * 1000
        interval_changes.append((change_per_mille, times[i], times[i + WINDOW_SIZE]))

    if interval_changes:
        max_interval_inc = max(interval_changes, key=lambda x: x[0])
        max_interval_dec = min(interval_changes, key=lambda x: x[0])
    else:
        max_interval_inc = max_interval_dec = None

    print("=" * 50)
    print("价格历史分析结果（变化率单位：‰）")
    print("=" * 50)

    print("\n【单次相邻变化】")
    print(f"最大涨幅: {max_increase[0]:.3f}‰")
    print(f"  发生时段: {format_time(max_increase[1])} → {format_time(max_increase[2])}")
    print(f"最大跌幅: {max_decrease[0]:.3f}‰")
    print(f"  发生时段: {format_time(max_decrease[1])} → {format_time(max_decrease[2])}")

    if max_interval_inc is not None:
        print(f"\n【{WINDOW_SIZE} 点区间变化】")
        print(f"区间最大上涨: {max_interval_inc[0]:.3f}‰")
        print(f"  起始时间: {format_time(max_interval_inc[1])}")
        print(f"  结束时间: {format_time(max_interval_inc[2])}")
        print(f"区间最大下跌: {max_interval_dec[0]:.3f}‰")
        print(f"  起始时间: {format_time(max_interval_dec[1])}")
        print(f"  结束时间: {format_time(max_interval_dec[2])}")
    else:
        print(f"\n【{WINDOW_SIZE} 点区间变化】数据不足，无法计算。")

    print("\n提示：正值表示上涨，负值表示下跌。")


def analyze_daily_extremes(history):
    """每天内的局部极值（相邻 + 区间窗口）"""
    daily_data = defaultdict(list)
    for record in history:
        if "price" in record and record["price"] is not None:
            ts = record.get("time", 0)
            if ts == 0:
                continue
            dt = datetime.fromtimestamp(ts)
            daily_data[dt.date()].append((ts, float(record["price"])))

    print("\n" + "=" * 50)
    print("【每日】局部涨跌幅极值（单位：‰）")
    print("=" * 50)

    for date_key in sorted(daily_data.keys()):
        items = daily_data[date_key]
        items.sort(key=lambda x: x[0])
        times = [t for t, _ in items]
        prices = [p for _, p in items]
        n = len(prices)

        if n < 2:
            continue

        adj_changes = []
        for i in range(1, n):
            p_prev = prices[i - 1]
            p_curr = prices[i]
            if p_prev == 0:
                continue
            change = (p_curr - p_prev) / p_prev * 1000
            adj_changes.append((change, times[i - 1], times[i]))

        if adj_changes:
            max_adj_inc = max(adj_changes, key=lambda x: x[0])
            max_adj_dec = min(adj_changes, key=lambda x: x[0])
        else:
            max_adj_inc = max_adj_dec = None

        interval_changes = []
        for i in range(n - WINDOW_SIZE):
            p_start = prices[i]
            p_end = prices[i + WINDOW_SIZE]
            if p_start == 0:
                continue
            change = (p_end - p_start) / p_start * 1000
            interval_changes.append((change, times[i], times[i + WINDOW_SIZE]))

        if interval_changes:
            max_int_inc = max(interval_changes, key=lambda x: x[0])
            max_int_dec = min(interval_changes, key=lambda x: x[0])
        else:
            max_int_inc = max_int_dec = None

        print(f"\n日期: {date_key}  (共 {n} 个数据点)")

        if max_adj_inc is not None:
            print(f"  相邻最大涨幅: {max_adj_inc[0]:.3f}‰  ({format_time(max_adj_inc[1])} → {format_time(max_adj_inc[2])})")
            print(f"  相邻最大跌幅: {max_adj_dec[0]:.3f}‰  ({format_time(max_adj_dec[1])} → {format_time(max_adj_dec[2])})")
        else:
            print("  相邻变化: 数据不足")

        if max_int_inc is not None:
            print(f"  {WINDOW_SIZE}点区间最大上涨: {max_int_inc[0]:.3f}‰  ({format_time(max_int_inc[1])} → {format_time(max_int_inc[2])})")
            print(f"  {WINDOW_SIZE}点区间最大下跌: {max_int_dec[0]:.3f}‰  ({format_time(max_int_dec[1])} → {format_time(max_int_dec[2])})")
        else:
            print(f"  {WINDOW_SIZE}点区间变化: 数据不足（当天少于{WINDOW_SIZE+1}个点）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--days", type=int, default=None, help="只分析最近 N 天")
    args = parser.parse_args()

    try:
        history = load_history(args.db, args.days)
        print(f"数据库: {args.db}  记录数: {len(history)}")
        analyze_extremes(history)
        analyze_daily_extremes(history)
    except Exception as exc:
        print(f"错误: {exc}")
