import os
import json
import hashlib
import shutil
import time
from PIL import Image
from collections import defaultdict

# 定义 mappings.json 文件路径和图片存储路径
json_path = "C:\\Users\\Administrator\\Desktop\\ArcBot\\data\\saying\\mappings.json"
image_base_path = "C:\\Users\\Administrator\\Desktop\\ArcBot\\data\\saying"

def get_str_width(s):
    """计算字符串在终端中的显示宽度（考虑中英文字符差异）"""
    # 中文字符宽度为2，英文字符宽度为1
    width = 0
    for char in s:
        # 判断是否为中文字符（包括中文标点）
        if '\u4e00' <= char <= '\u9fff' or char in '，。！？；：「」【】（）《》':
            width += 2
        else:
            width += 1
    return width

def format_cell(content, width, align='left'):
    """格式化单元格内容，确保显示宽度一致"""
    content_str = str(content)
    current_width = get_str_width(content_str)
    
    # 如果内容宽度大于目标宽度，截断内容
    if current_width > width:
        # 逐步减少字符直到宽度合适
        while current_width > width - 3 and len(content_str) > 1:
            content_str = content_str[:-1]
            current_width = get_str_width(content_str)
        content_str = content_str + '..'
        current_width = get_str_width(content_str)
    
    # 计算需要填充的空格数量
    padding = width - current_width
    
    if align == 'right':
        return ' ' * padding + content_str
    elif align == 'center':
        left_pad = padding // 2
        right_pad = padding - left_pad
        return ' ' * left_pad + content_str + ' ' * right_pad
    else:  # left align
        return content_str + ' ' * padding

def print_section(title, width=50):
    """打印分区标题"""
    print("\n" + "=" * width)
    print(format_cell(title, width, 'center'))
    print("=" * width)

def analyze_records(perform_fix):
    # 备份原始文件（安全措施）
    if perform_fix:
        timestamp = int(time.time())
        backup_path = f"data/saying/backup_{timestamp}/"
        os.makedirs(backup_path, exist_ok=True)
        shutil.copy(json_path, backup_path + "mappings.json")
        print(f"[备份] 已创建备份: {backup_path}")

    with open(json_path, "r", encoding="utf8") as f:
        mappings = json.load(f)

    # 初始化数据结构
    group_stats = {}
    same_group_duplicates = defaultdict(lambda: defaultdict(list))  # {group_id: {md5: [timestamps]}}
    cross_group_duplicates = defaultdict(set)  # {md5: set(group_ids)}
    md5_cache = {}  # 文件内容MD5缓存
    
    # 问题记录集合
    missing_records = []  # 图片不存在的记录
    invalid_images = []   # 无法打开的图片
    repaired_images = []  # 修复成功的图片
    renamed_files = []    # 重命名的文件
    duplicate_records = defaultdict(list)  # 重复记录 {group_id: {md5: [timestamps]}}
    
    # 分析模式专用统计
    analysis_stats = {
        "total_duplicates": 0,
        "potential_renames": 0
    }

    # 遍历所有记录
    for timestamp, record in mappings.items():
        if timestamp == "Plugin":
            continue

        who_said = record["Who"]
        group_id = record["Data"]["Group"]
        picture_id = record["Data"]["Picture ID"]
        image_path = os.path.join(image_base_path, group_id, picture_id)

        # 初始化群组统计
        if group_id not in group_stats:
            group_stats[group_id] = {}
        if who_said not in group_stats[group_id]:
            group_stats[group_id][who_said] = {
                "total": 0, 
                "missing_images": 0,
                "invalid_images": 0,
                "mismatched_names": 0,
                "duplicates_detected": 0,
                "duplicates_removed": 0
            }

        # 统计记录数量
        group_stats[group_id][who_said]["total"] += 1

        # ===== 1. 检查图片是否存在 =====
        if not os.path.exists(image_path):
            group_stats[group_id][who_said]["missing_images"] += 1
            missing_records.append((timestamp, group_id, picture_id))
            
            # 修复：删除缺失图片的记录
            if perform_fix:
                # 记录将被删除，跳过后续处理
                continue
            else:
                # 仅分析，跳过后续处理
                continue

        # ===== 2. 检查图片有效性 =====
        actual_format = None
        try:
            # 尝试打开图片验证完整性
            with Image.open(image_path) as img:
                actual_format = img.format
                # 强制加载以检测损坏
                img.load()
        except (IOError, OSError, Image.UnidentifiedImageError) as e:
            group_stats[group_id][who_said]["invalid_images"] += 1
            invalid_images.append((timestamp, group_id, picture_id, str(e)))
            
            # 修复：尝试重新转存损坏的图片
            if perform_fix:
                try:
                    # 尝试重新打开并保存
                    with Image.open(image_path) as img:
                        # 创建修复后的临时文件
                        temp_path = image_path + ".fixed"
                        img.save(temp_path, format=img.format)
                        
                        # 替换原文件
                        os.remove(image_path)
                        os.rename(temp_path, image_path)
                        repaired_images.append((group_id, picture_id))
                        
                        # 重新加载修复后的图片
                        with Image.open(image_path) as fixed_img:
                            actual_format = fixed_img.format
                except Exception as fix_error:
                    # 修复失败，标记为缺失
                    missing_records.append((timestamp, group_id, picture_id))
                    continue
            else:
                # 仅分析，跳过后续处理
                continue

        # ===== 3. 计算文件MD5 =====
        if image_path in md5_cache:
            file_md5 = md5_cache[image_path]
        else:
            try:
                with open(image_path, "rb") as f:
                    file_md5 = hashlib.md5(f.read()).hexdigest().upper()
                md5_cache[image_path] = file_md5
            except Exception as e:
                continue

        # ===== 4. 统一扩展名格式 =====
        format_mapping = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}
        ext = format_mapping.get(actual_format, actual_format.lower() if actual_format else "unknown")
        
        # 构建预期的Hash文件名
        expected_name = f"{file_md5}.{ext}"
        
        # ===== 5. 文件名验证 =====
        if picture_id != expected_name:
            group_stats[group_id][who_said]["mismatched_names"] += 1
            analysis_stats["potential_renames"] += 1
            
            # 修复：重命名文件
            if perform_fix:
                try:
                    new_path = os.path.join(image_base_path, group_id, expected_name)
                    
                    # 避免覆盖现有文件
                    if not os.path.exists(new_path):
                        os.rename(image_path, new_path)
                        renamed_files.append((group_id, picture_id, expected_name))
                        
                        # 更新记录中的文件名
                        record["Data"]["Picture ID"] = expected_name
                        picture_id = expected_name
                        image_path = new_path
                except Exception as e:
                    pass
        
        # ===== 6. 重复检测 =====
        # 使用实际文件内容MD5作为唯一标识
        unique_id = str(file_md5)+" "+str(who_said)
        
        # 记录同群重复
        same_group_duplicates[group_id][unique_id].append(timestamp)
        
        # 记录跨群重复
        cross_group_duplicates[unique_id].add(group_id)

    # ===== 7. 分析模式：统计重复记录 =====
    for group_id, md5_records in same_group_duplicates.items():
        for md5, timestamps in md5_records.items():
            if len(timestamps) > 1:
                # 计算重复数量（保留最早的一条）
                dup_count = len(timestamps) - 1
                analysis_stats["total_duplicates"] += dup_count
                
                # 为每个发言人统计重复记录
                for ts in timestamps[1:]:  # 跳过最早的一条
                    if ts in mappings:
                        who_said = mappings[ts]["Who"]
                        group_stats[group_id][who_said]["duplicates_detected"] += 1

    # ===== 8. 修复模式：处理重复记录 =====
    if perform_fix:
        for group_id, md5_records in same_group_duplicates.items():
            for md5, timestamps in md5_records.items():
                if len(timestamps) > 1:
                    # 按时间戳排序（最早的在前）
                    sorted_timestamps = sorted(timestamps)
                    
                    # 保留最早的一条，删除其他
                    for ts in sorted_timestamps[1:]:
                        if ts in mappings:
                            # 获取说话人用于统计
                            who_said = mappings[ts]["Who"]
                            group_stats[group_id][who_said]["duplicates_removed"] += 1
                            
                            # 记录删除操作
                            duplicate_records[group_id].append((ts, md5))
                            del mappings[ts]
        
        # ===== 9. 删除缺失记录 =====
        for ts, group_id, picture_id in missing_records:
            if ts in mappings:
                # 获取说话人用于统计
                who_said = mappings[ts]["Who"]
                group_stats[group_id][who_said]["duplicates_removed"] += 1
                del mappings[ts]

        # ===== 10. 保存修复后的数据库 =====
        with open(json_path, "w", encoding="utf8") as writejson:
            json.dump(mappings, writejson, ensure_ascii=False)

    # ===== 11. 输出统计结果 =====
    print_section("基础统计信息")
    
    # 表头
    headers = ["群组/发言人", "总记录", "缺失图片", "无效图片", "文件名问题", 
               "重复检测" if not perform_fix else "删除重复"]
    
    # 计算每列宽度（考虑中英文字符宽度差异）
    col_widths = [20, 12, 12, 12, 12, 12]
    
    # 打印表头
    header_line = ""
    for i, header in enumerate(headers):
        header_line += format_cell(header, col_widths[i], 'center' if i > 0 else 'left') + " "
    print(header_line)
    print("-" * (sum(col_widths) + len(headers) * 1))  # 分隔线
    
    # 统计数据
    for group_id, stats in group_stats.items():
        group_line = format_cell(f"群组 {group_id}", col_widths[0])
        print(group_line)
        
        for who_said, data in stats.items():
            row = [
                f"├ {who_said}",
                data["total"],
                data["missing_images"],
                data["invalid_images"],
                data["mismatched_names"],
                data["duplicates_detected"] if not perform_fix else data["duplicates_removed"]
            ]
            
            row_line = ""
            for i, value in enumerate(row):
                align = 'center' if i > 0 else 'left'
                row_line += format_cell(value, col_widths[i], align) + " "
            print(row_line)
        
        print(format_cell("└", col_widths[0]) + "\n")

    # ===== 12. 输出重复检测结果 =====
    print_section("重复图片检测报告")
    
    # 同群重复统计
    same_group_count = 0
    for group_id, md5_records in same_group_duplicates.items():
        for md5, timestamps in md5_records.items():
            if len(timestamps) > 1:
                same_group_count += 1
                action = "保留" if perform_fix else "可保留"
                print(f"同群重复: {format_cell(f'群组 {group_id}', 15)} - 图片 {md5[:32]}")
                print(f"  次数: {len(timestamps)}  最早记录: {min(timestamps)} {action}")
    
    if same_group_count == 0:
        print("未发现同群重复图片")
    
    # 跨群重复统计
    cross_group_count = 0
    for md5, groups in cross_group_duplicates.items():
        if len(groups) > 1:
            cross_group_count += 1
            group_list = ", ".join(sorted(groups))
            print(f"跨群重复: {format_cell(f'图片 {md5[:32]}', 32)}")
            print(f"  群组数: {len(groups)}  群组列表: {group_list}")
    
    if cross_group_count == 0:
        print("未发现跨群重复图片")

    # ===== 13. 分析模式建议 =====
    if not perform_fix and (analysis_stats["total_duplicates"] > 0 or 
                            analysis_stats["potential_renames"] > 0 or
                            len(missing_records) > 0 or 
                            len(invalid_images) > 0):
        print_section("操作建议")
        
        suggestions = []
        if analysis_stats["total_duplicates"] > 0:
            suggestions.append(f"检测到重复记录: {analysis_stats['total_duplicates']} 条")
        if analysis_stats["potential_renames"] > 0:
            suggestions.append(f"需重命名文件: {analysis_stats['potential_renames']} 个")
        if len(missing_records) > 0:
            suggestions.append(f"缺失图片记录: {len(missing_records)} 条")
        if len(invalid_images) > 0:
            suggestions.append(f"无效图片文件: {len(invalid_images)} 个")
        
        for i, suggestion in enumerate(suggestions):
            prefix = "└─ " if i == len(suggestions) - 1 else "├─ "
            print(prefix + suggestion)
        
        print("\n运行修复模式可处理以上问题")
        print("命令: analyze_records(True)")

    print_section("分析完成")

if __name__ == "__main__":
    print("开始分析记录...")
    analyze_records(False)