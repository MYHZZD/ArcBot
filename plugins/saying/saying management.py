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
    
    # 存储图片在群内的使用情况 {picture_id: {group_id: count}}
    same_group_duplicates = {}
    # 存储图片在跨群的使用情况 {picture_id: set(group_ids)}
    cross_group_duplicates = {}

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

        # 1. 检测同群重复
        if group_id not in same_group_duplicates:
            same_group_duplicates[group_id] = {}
        
        if picture_id not in same_group_duplicates[group_id]:
            same_group_duplicates[group_id][picture_id] = 1
        else:
            same_group_duplicates[group_id][picture_id] += 1
        
        # 2. 检测跨群重复
        if picture_id not in cross_group_duplicates:
            cross_group_duplicates[picture_id] = set()
        cross_group_duplicates[picture_id].add(group_id)

    # 输出原始统计结果
    print("=" * 50)
    print("基础统计信息：")
    for group_id, stats in group_stats.items():
        print(f"群组 {group_id} 的记录统计：")
        for who_said, data in stats.items():
            print(f"  - {who_said}: 总记录数={data['total']}, 缺失图片数={data['missing_images']}")
        print()
    
    print("=" * 50)
    print("重复图片检测报告：")
    
    # 1. 输出同群重复情况
    same_group_found = False
    for group_id, pictures in same_group_duplicates.items():
        for pic_id, count in pictures.items():
            if count > 1:
                if not same_group_found:
                    print("\n同群重复图片（同一图片在同一个群内添加多次）：")
                    same_group_found = True
                print(f"  图片 '{pic_id}' 在群组 {group_id} 中重复添加了 {count} 次")
    
    if not same_group_found:
        print("\n未发现同群重复图片")
    
    # 2. 输出跨群重复情况
    cross_group_found = False
    for pic_id, groups in cross_group_duplicates.items():
        if len(groups) > 1:
            if not cross_group_found:
                print("\n跨群重复图片（同一图片在多个群组中使用）：")
                cross_group_found = True
            group_list = ", ".join(groups)
            print(f"  图片 '{pic_id}' 在 {len(groups)} 个群组中使用: [{group_list}]")
    
    if not cross_group_found:
        print("\n未发现跨群重复图片")
    
    print("=" * 50)

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

'''
    # 示例：迁移记录
    source_group = "733968766"  # 源群组ID
    target_group = "863388869"  # 目标群组ID
    who_said = "裙友说过"    # 要迁移的“某人说过”
    print(f"\n开始迁移记录：{who_said} 从群组 {source_group} 到 {target_group}")
    migrate_records(source_group, target_group, who_said)
'''