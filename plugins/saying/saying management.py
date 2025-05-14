import os
import json
import shutil

# 定义 mappings.json 文件路径和图片存储路径
json_path = "C:\\Users\\Administrator\\Desktop\\ArcBot\\data\\saying\\mappings.json"
image_base_path = "C:\\Users\\Administrator\\Desktop\\ArcBot\\data\\saying"

# 1. 分析每个群内某人说过的记录数量，并检查图片文件是否存在
def analyze_records():
    with open(json_path, "r", encoding="utf8") as f:
        mappings = json.load(f)

    # 统计每个群组中每个人的记录数量
    group_stats = {}
    for timestamp, record in mappings.items():
        if timestamp == "Plugin":
            continue

        who_said = record["Who"]
        group_id = record["Data"]["Group"]
        picture_id = record["Data"]["Picture ID"]
        image_path = os.path.join(image_base_path, group_id, picture_id)

        # 初始化统计数据结构
        if group_id not in group_stats:
            group_stats[group_id] = {}
        if who_said not in group_stats[group_id]:
            group_stats[group_id][who_said] = {"total": 0, "missing_images": 0}

        # 统计记录数量
        group_stats[group_id][who_said]["total"] += 1

        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            group_stats[group_id][who_said]["missing_images"] += 1

    # 输出统计结果
    for group_id, stats in group_stats.items():
        print(f"群组 {group_id} 的记录统计：")
        for who_said, data in stats.items():
            print(f"  - {who_said}: 总记录数={data['total']}, 缺失图片数={data['missing_images']}")
        print()

# 2. 将指定群组内“某人说过”的记录迁移至另一个群组，并迁移图片数据
def migrate_records(source_group, target_group, who_said):
    with open(json_path, "r", encoding="utf8") as f:
        mappings = json.load(f)

    # 创建目标群组的图片目录
    target_image_path = os.path.join(image_base_path, target_group)
    if not os.path.exists(target_image_path):
        os.makedirs(target_image_path)

    # 遍历所有记录，找到符合条件的记录
    for timestamp, record in mappings.items():
        if timestamp == "Plugin":
            continue

        if record["Data"]["Group"] == source_group and record["Who"] == who_said:
            # 更新记录中的群组ID
            record["Data"]["Group"] = target_group

            # 迁移图片文件
            picture_id = record["Data"]["Picture ID"]
            source_image_path = os.path.join(image_base_path, source_group, picture_id)
            target_image_path_file = os.path.join(target_image_path, picture_id)

            if os.path.exists(source_image_path):
                shutil.move(source_image_path, target_image_path_file)
                print(f"已迁移图片: {picture_id} 从群组 {source_group} 到 {target_group}")
            else:
                print(f"图片 {picture_id} 在群组 {source_group} 中不存在，无法迁移")

    # 将更新后的 mappings 写回文件
    with open(json_path, "w", encoding="utf8") as f:
        json.dump(mappings, f, ensure_ascii=False, indent=4)

    print(f"已将群组 {source_group} 中 {who_said} 的记录迁移至群组 {target_group}")

# 主程序
if __name__ == "__main__":
    # 示例：分析所有记录
    print("开始分析记录...")
    analyze_records()

    # 示例：迁移记录
    source_group = "733968766"  # 源群组ID
    target_group = "863388869"  # 目标群组ID
    who_said = "裙友说过"    # 要迁移的“某人说过”
    print(f"\n开始迁移记录：{who_said} 从群组 {source_group} 到 {target_group}")
    migrate_records(source_group, target_group, who_said)