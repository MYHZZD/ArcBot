import json
import os
from datetime import datetime
from collections import defaultdict

FILE_PATH = "../../data/getgold/price_history.json"
WINDOW_SIZE = 15  # 区间窗口大小


def load_history(file_path):
    """加载 JSON 历史数据"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件 {file_path} 不存在")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON 根元素应为列表")
    return data


def format_time(timestamp):
    """将时间戳转为可读字符串"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def analyze_extremes(history):
    """
    分析价格极值：
      - 单次最大涨跌幅（相邻两点）
      - 区间最大涨跌幅（窗口内首尾）
    """
    # 提取价格列表（忽略可能存在的 "推送" 字段）
    prices = []
    times = []
    for record in history:
        if "price" in record and record["price"] is not None:
            prices.append(float(record["price"]))
            times.append(record.get("time", 0))  # 若缺 time 则用索引

    if len(prices) < 2:
        print("数据点不足，至少需要 2 条记录。")
        return

    # ---------- 1. 单次变化 ----------
    single_changes = []  # 存储 (涨幅‰, 起始时间, 结束时间)
    for i in range(1, len(prices)):
        p_prev = prices[i - 1]
        p_curr = prices[i]
        if p_prev == 0:
            continue
        change_per_mille = (p_curr - p_prev) / p_prev * 1000
        single_changes.append((change_per_mille, times[i - 1], times[i]))

    # 找最大涨幅和最大跌幅
    max_increase = max(single_changes, key=lambda x: x[0])
    max_decrease = min(single_changes, key=lambda x: x[0])

    # ---------- 2. 区间变化（滑动窗口） ----------
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

    # ---------- 输出结果 ----------
    print("=" * 50)
    print("价格历史分析结果（变化率单位：‰）")
    print("=" * 50)

    print(f"\n【单次相邻变化】")
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
    """
    每天内的局部极值（相邻 + 区间窗口）
    """
    # 按日期分组
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
        items.sort(key=lambda x: x[0])  # 按时间排序
        times = [t for t, _ in items]
        prices = [p for _, p in items]
        n = len(prices)

        if n < 2:
            continue  # 当天至少两个点才能计算相邻变化

        # ---- 相邻变化 ----
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

        # ---- 区间变化（滑动窗口，窗口大小 WINDOW_SIZE） ----
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

        # ---- 输出当天结果 ----
        print(f"\n日期: {date_key}  (共 {n} 个数据点)")

        # 相邻
        if max_adj_inc is not None:
            print(f"  相邻最大涨幅: {max_adj_inc[0]:.3f}‰  ({format_time(max_adj_inc[1])} → {format_time(max_adj_inc[2])})")
            print(f"  相邻最大跌幅: {max_adj_dec[0]:.3f}‰  ({format_time(max_adj_dec[1])} → {format_time(max_adj_dec[2])})")
        else:
            print("  相邻变化: 数据不足")

        # 区间
        if max_int_inc is not None:
            print(f"  {WINDOW_SIZE}点区间最大上涨: {max_int_inc[0]:.3f}‰  ({format_time(max_int_inc[1])} → {format_time(max_int_inc[2])})")
            print(f"  {WINDOW_SIZE}点区间最大下跌: {max_int_dec[0]:.3f}‰  ({format_time(max_int_dec[1])} → {format_time(max_int_dec[2])})")
        else:
            print(f"  {WINDOW_SIZE}点区间变化: 数据不足（当天少于{WINDOW_SIZE+1}个点）")


if __name__ == "__main__":
    try:
        history = load_history(FILE_PATH)
        analyze_extremes(history)
        analyze_daily_extremes(history)
    except Exception as e:
        print(f"错误: {e}")
