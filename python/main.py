import os
import re
from tkinter import *
from tkinter import messagebox, ttk

import jpg
import wlbi
from PIL import Image

wlbi_filepath = ""
# 待补充没勾选wlbi时


# 读取文件并获取头部信息和芯片地图数据
def read_file(file_path, file_type="default"):
    with open(file_path, "r") as file:
        lines = file.readlines()

    # 找到地图数据的起始行
    start_line = 0
    for i, line in enumerate(lines):
        # 根据文件类型识别起始行
        if ".*" in line or ".S" in line or "[MAP]:" in line:
            start_line = i
            break

    # 提取头部信息
    header = {}
    for line in lines[:start_line]:
        if ": " in line:
            key, value = line.strip().split(": ", 1)
            header[key.strip()] = value.strip()

    # 提取芯片地图数据，过滤掉空行
    map_data = []
    for line in lines[start_line:]:
        stripped_line = line.strip()
        if stripped_line:
            map_data.append(stripped_line)

    return header, map_data


def overlay_maps(maps, order, debug=False):
    if not maps:
        return []

    # 按照用户指定的顺序排列地图
    ordered_maps = [maps[i] for i in order]

    # 初始化结果矩阵，使用第一个地图的数据
    result = [list(row) for row in ordered_maps[0]]

    # 调试信息
    if debug:
        debug_info = []
        debug_info.append("===== 叠图过程开始 =====")
        debug_info.append(f"初始地图:")
        for row in ordered_maps[0]:
            debug_info.append(row)
        debug_info.append("")

    # 按优先级覆盖
    for map_idx, map_data in enumerate(ordered_maps[1:]):
        if debug:
            debug_info.append(f"应用地图 {map_idx+2}:")
            for row in map_data:
                debug_info.append(row)
            debug_info.append("")
            debug_info.append(f"叠图后结果:")

        changes = 0
        change_details = []

        # 处理第一行：找到.S或.*后的第一个字符作为起始点
        if map_data and result:
            # 查找第一个地图中的.S或.*位置
            first_map_start = 0
            if len(result[0]) > 1:
                for j in range(len(result[0]) - 1):
                    if result[0][j] == "." and (
                        result[0][j + 1] == "S" or result[0][j + 1] == "*"
                    ):
                        first_map_start = j + 2  # 从.S或.*后的第一个字符开始
                        break

            # 查找当前地图中的.S或.*位置
            current_map_start = 0
            if len(map_data[0]) > 1:
                for j in range(len(map_data[0]) - 1):
                    if map_data[0][j] == "." and (
                        map_data[0][j + 1] == "S" or map_data[0][j + 1] == "*"
                    ):
                        current_map_start = j + 2
                        break

            # 计算偏移量
            offset = current_map_start - first_map_start

            # 处理第一行数据
            if len(result[0]) > 0 and len(map_data[0]) > 0:
                for j in range(len(map_data[0])):
                    # 计算在结果矩阵中的对应位置
                    result_pos = j - offset
                    if result_pos < 0 or result_pos >= len(result[0]):
                        continue

                    current_char = result[0][result_pos]
                    new_char = map_data[0][j]

                    # 跳过空白字符
                    if new_char == "." or new_char == " ":
                        continue

                    # 应用叠图逻辑
                    if current_char.isdigit() and new_char.isdigit():
                        if int(new_char) > int(current_char):
                            result[0][result_pos] = new_char
                            changes += 1
                            if debug:
                                change_details.append(
                                    f"位置 (0,{result_pos}): {current_char} -> {new_char}"
                                )
                    elif current_char == "." or current_char == " ":
                        result[0][result_pos] = new_char
                        changes += 1
                        if debug:
                            change_details.append(
                                f"位置 (0,{result_pos}): {current_char} -> {new_char}"
                            )
                    elif not new_char.isdigit():
                        result[0][result_pos] = new_char
                        changes += 1
                        if debug:
                            change_details.append(
                                f"位置 (0,{result_pos}): {current_char} -> {new_char}"
                            )

        # 处理其余行：找到第一个.后的第一个数字作为起始点
        for i in range(1, min(len(result), len(map_data))):
            # 找到第一个地图中当前行的起始点
            first_map_start = 0
            found_dot = False
            for j in range(len(result[i])):
                if result[i][j] == ".":
                    found_dot = True
                elif found_dot and result[i][j].isdigit():
                    first_map_start = j
                    break

            # 找到当前地图中当前行的起始点
            current_map_start = 0
            found_dot = False
            for j in range(len(map_data[i])):
                if map_data[i][j] == ".":
                    found_dot = True
                elif found_dot and map_data[i][j].isdigit():
                    current_map_start = j
                    break

            # 计算偏移量
            offset = current_map_start - first_map_start

            # 处理当前行数据
            for j in range(len(map_data[i])):
                # 计算在结果矩阵中的对应位置
                result_pos = j - offset
                if result_pos < 0 or result_pos >= len(result[i]):
                    continue

                current_char = result[i][result_pos]
                new_char = map_data[i][j]

                # 跳过空白字符
                if new_char == "." or new_char == " ":
                    continue

                # 应用叠图逻辑
                if current_char.isdigit() and new_char.isdigit():
                    if int(new_char) > int(current_char):
                        result[i][result_pos] = new_char
                        changes += 1
                        if debug:
                            change_details.append(
                                f"位置 ({i},{result_pos}): {current_char} -> {new_char}"
                            )
                elif current_char == "." or current_char == " ":
                    result[i][result_pos] = new_char
                    changes += 1
                    if debug:
                        change_details.append(
                            f"位置 ({i},{result_pos}): {current_char} -> {new_char}"
                        )
                elif not new_char.isdigit():
                    result[i][result_pos] = new_char
                    changes += 1
                    if debug:
                        change_details.append(
                            f"位置 ({i},{result_pos}): {current_char} -> {new_char}"
                        )

        if debug:
            debug_info.append(f"本轮修改了 {changes} 个位置")
            for row in result:
                debug_info.append("".join(row))
            debug_info.append("")
            debug_info.append("具体更改:")
            debug_info.extend(change_details)
            debug_info.append("")

    if debug:
        debug_info.append("===== 叠图过程结束 =====")
        debug_info.append("最终地图:")
        for row in result:
            debug_info.append("".join(row))
        return ["".join(row) for row in result], debug_info

    return ["".join(row) for row in result]


# 计算统计信息
def calculate_stats(map_data):
    """
    计算总测试数、通过数、失败数和良率
    """
    total_tested = 0
    total_pass = 0
    for row in map_data:
        for char in row:
            if char != "." and char != "S" and char != "*":
                total_tested += 1
                # 假设'1'表示通过，其他数字表示失败
                if char == "1" or char == "A":
                    total_pass += 1
    total_fail = total_tested - total_pass
    yield_percentage = (total_pass / total_tested) * 100 if total_tested > 0 else 0
    return total_tested, total_pass, total_fail, yield_percentage


# 生成HEX格式
def generate_hex(map_data):
    hex_lines = []
    digit_count = {}
    for row in map_data:
        processed_row = []
        for char in row:
            if char == "." or char == "S":
                processed_row.append("__ ")
            elif char.isdigit():
                processed_row.append(f"0{char} ")
                digit_count[char] = digit_count.get(char, 0) + 1
            else:
                processed_row.append(f"*{char} ")
        hex_lines.append(f"Rowdata: {''.join(processed_row)}")

    stats_lines = ["\n# 数字统计:"]
    for digit, count in sorted(digit_count.items(), key=lambda x: int(x[0])):
        stats_lines.append(f"0{digit}: {count} ")

    return "\n".join(hex_lines + stats_lines)


# 生成jpg格式
def generate_jpg(map_data, file_name):
    width = max(len(line) for line in map_data) if map_data else 0
    height = len(map_data)
    img = Image.new("RGB", (width, height), color="white")
    for y, line in enumerate(map_data):
        for x, char in enumerate(line):
            if char != "." and char != " ":
                # 根据字符不同显示不同颜色
                if char.isdigit():
                    color = (
                        int(char) * 30,
                        0,
                        255 - int(char) * 30,
                    )  # 数字越大，颜色越偏向红色
                else:
                    color = (0, 0, 0)  # 非数字字符显示为黑色
                img.putpixel((x, y), color)
    output_path = os.path.join(output_formats["jpg"], file_name.replace(".txt", ".jpg"))
    img.save(output_path)


# 处理叠图和输出
def process_mapping():
    selected_formats = []
    for i, var in enumerate(format_vars):
        if var.get() == 1:
            selected_formats.append(format_names[i])

    if not selected_formats:
        messagebox.showwarning("警告", "请至少选择一种输入格式！")
        return

    # 创建输出文件夹
    for output_folder in output_formats.values():
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    # 创建调试信息文件夹
    debug_dir = "输出文件/debug"
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)

    # 处理每个晶圆
    for wafer_id in ["01"]:
        headers = []
        maps = []
        selected_indices = []
        format_names_list = []

        # 按照用户选择的顺序读取文件
        for format_name in selected_formats:
            folder_path = input_formats[format_name]
            if folder_path:
                if format_name == "FAB":
                    file_name = f"P0094B_B003332_{wafer_id}.txt"
                    file_path = os.path.join(folder_path, file_name)
                    file_type = "FAB"
                elif format_name == "WLBI":
                    file_name = (
                        f"B003332-{wafer_id}_20250325_170454.WaferMap"  # 假设文件名格式
                    )
                    file_path = os.path.join(folder_path, file_name)
                    wlbi_filepath = file_path
                    map_data = wlbi.parse_wlbi_to_matrix(file_path)  # 调用函数获取列表
                    map_data = [
                        "".join(row) for row in map_data
                    ]  # 将二维列表转换为一维字符串列表
                    for row in map_data:
                        print(row)

                else:
                    file_name = (
                        f"S1M032120B_B003332_{wafer_id}.txt"
                        if format_name == "AOI"
                        else f"S1M032120B_B003332_{wafer_id}_mapEx.txt"
                    )
                    file_path = os.path.join(folder_path, file_name)
                    file_type = "default"

                if os.path.exists(file_path):
                    if (format_name) != "WLBI":
                        header, map_data = read_file(file_path, file_type)
                    if map_data:
                        headers.append(header)
                        maps.append(map_data)
                        selected_indices.append(format_names.index(format_name))
                        format_names_list.append(format_name)
                        print(f"已加载 {format_name} 文件: {file_path}")
                        print(
                            f"地图尺寸: {len(map_data)} 行, {len(map_data[0]) if map_data else 0} 列"
                        )
                    else:
                        print(f"警告: 文件 {file_path} 没有有效的地图数据")
                else:
                    print(f"警告: 文件 {file_path} 不存在")

        # 叠图

        if not maps:
            messagebox.showwarning("警告", f"晶圆 {wafer_id} 没有找到有效的叠图数据！")
            continue

        # 使用用户选择的顺序进行叠图，并获取调试信息
        overlayed_map, debug_info = overlay_maps(
            maps, list(range(len(maps))), debug=True
        )

        # 计算统计信息
        total_tested, total_pass, total_fail, yield_percentage = calculate_stats(
            overlayed_map
        )

        # 保存调试信息
        debug_file = os.path.join(debug_dir, f"S1M032120B_B003332_{wafer_id}_debug.txt")
        with open(debug_file, "w") as f:
            f.write(f"叠图顺序: {', '.join(format_names_list)}\n\n")
            f.write("\n".join(debug_info))
            f.write("\n\n统计信息:\n")
            f.write(f"总测试数: {total_tested}\n")
            f.write(f"通过数: {total_pass}\n")
            f.write(f"失败数: {total_fail}\n")
            f.write(f"良率: {yield_percentage:.2f}%\n")

        print(f"调试信息已保存到: {debug_file}")

        # 输出到不同格式
        base_file_name = f"S1M032120B_B003332_{wafer_id}"

        # 输出mapEx格式
        output_mapEx_path = os.path.join(
            output_formats["mapEx"], f"{base_file_name}_overlayed.mapEx"
        )
        with open(output_mapEx_path, "w") as file:
            # 写入第一个文件的头部信息
            for key, value in headers[0].items():
                if key == "Total Tested":
                    value = str(total_tested)
                elif key == "Total Pass":
                    value = str(total_pass)
                elif key == "Total Fail":
                    value = str(total_fail)
                elif key == "Yield":
                    value = f"{yield_percentage:.2f}%"
                file.write(f"{key}: {value}\n")
            file.write("\n")  # 空行分隔头部和地图数据
            # 写入地图数据
            for row in overlayed_map:
                file.write(f"{row}\n")

        # 输出HEX格式
        hex_data = generate_hex(overlayed_map)
        output_hex_path = os.path.join(
            output_formats["HEX"], f"{base_file_name}_overlayed.hex"
        )
        with open(output_hex_path, "w") as file:
            file.write(hex_data)

        # 输出jpg格式
        # generate_jpg(overlayed_map, f"{base_file_name}_overlayed.jpg")
        # jpg.generate_threejs(overlayed_map, f"{base_file_name}_overlayed.jpg")
        jpg.generate_color_image(
            overlayed_map, f"输出文件/jpg/{base_file_name}_overlayed_map.jpg"
        )

        # 输出wafermap格式
        output_wafermap_path = os.path.join(
            output_formats["wafermap"], f"{base_file_name}_overlayed.wafermap"
        )
        with open(output_wafermap_path, "w") as file:
            # 写入第一个文件的头部信息
            for key, value in headers[0].items():
                if key == "Total Tested":
                    value = str(total_tested)
                elif key == "Total Pass":
                    value = str(total_pass)
                elif key == "Total Fail":
                    value = str(total_fail)
                elif key == "Yield":
                    value = f"{yield_percentage:.2f}%"
                file.write(f"{key}: {value}\n")
            file.write("\n")  # 空行分隔头部和地图数据
            # 写入地图数据
            for row in overlayed_map:
                file.write(f"{row}\n")

        wlbi.print_inform_wafermap(overlayed_map, wlbi_filepath, base_file_name)
        # generate_wafermap(overlayed_map, wlbi_filepath)
        # for row in overlayed_map:
        #     print(row)


# 打开排序对话框
def open_sort_dialog():
    # 获取当前选中的格式
    selected = [i for i, var in enumerate(format_vars) if var.get() == 1]
    if not selected:
        messagebox.showwarning("警告", "请先选择至少一种格式！")
        return

    # 创建排序对话框
    sort_window = Toplevel(root)
    sort_window.title("调整叠图顺序")
    sort_window.geometry("300x300")

    # 创建列表框显示选中的格式
    listbox = Listbox(sort_window, selectmode=SINGLE, height=len(selected))
    for i in selected:
        listbox.insert(END, format_names[i])
    listbox.pack(pady=10, fill=BOTH, expand=True)

    # 创建上移和下移按钮
    frame = Frame(sort_window)
    frame.pack(pady=10)

    def move_up():
        selected_index = listbox.curselection()
        if selected_index and selected_index[0] > 0:
            current_item = listbox.get(selected_index[0])
            listbox.delete(selected_index[0])
            listbox.insert(selected_index[0] - 1, current_item)
            listbox.selection_set(selected_index[0] - 1)

    def move_down():
        selected_index = listbox.curselection()
        if selected_index and selected_index[0] < listbox.size() - 1:
            current_item = listbox.get(selected_index[0])
            listbox.delete(selected_index[0])
            listbox.insert(selected_index[0] + 1, current_item)
            listbox.selection_set(selected_index[0] + 1)

    def save_order():
        # 获取排序后的顺序
        sorted_formats = [listbox.get(i) for i in range(listbox.size())]
        # 更新format_names的顺序
        global format_names
        # 先保存未选中的格式
        unselected = [name for i, name in enumerate(format_names) if i not in selected]
        # 重新组合格式列表
        format_names = sorted_formats + unselected
        # 更新界面显示
        update_format_display()
        sort_window.destroy()

    Button(frame, text="上移", command=move_up).pack(side=LEFT, padx=5)
    Button(frame, text="下移", command=move_down).pack(side=LEFT, padx=5)
    Button(sort_window, text="保存顺序", command=save_order).pack(pady=10)


# 更新格式显示
def update_format_display():
    for i, name in enumerate(format_names):
        checkbuttons[i].config(text=name)


# 定义每个输入格式的文件夹路径
input_formats = {
    "衬底": "",  # 这里没有衬底相关文件示例，可补充路径
    "AOI": "叠图输入文件/AOI/S1M032120B_B003332",
    "CP1": "叠图输入文件/CP1/S1M032120B_B003332_1_0",
    "CP2": "叠图输入文件/CP2/S1M032120B_B003332_1_0",
    "FAB": "叠图输入文件/FAB CP/B003332",
    "WLBI": "叠图输入文件/WLBI/B003332",
}

# 定义输出格式的文件夹路径
output_formats = {
    "mapEx": "输出文件/mapEx",
    "wafermap": "输出文件/wafermap",
    "HEX": "输出文件/HEX",
    "jpg": "输出文件/jpg",
}

# 创建主窗口
root = Tk()
root.title("叠图处理工具")

# 输入格式选择
format_names = ["衬底", "AOI", "CP1", "CP2", "FAB", "WLBI"]
format_vars = []
checkbuttons = []
for i, name in enumerate(format_names):
    var = IntVar()
    format_vars.append(var)
    cb = Checkbutton(root, text=name, variable=var)
    cb.grid(row=i, column=0, sticky=W)
    checkbuttons.append(cb)

# 排序按钮
Button(root, text="调整叠图顺序", command=open_sort_dialog).grid(
    row=len(format_names), column=0, pady=5, sticky=W
)

# 处理按钮
Button(root, text="开始处理", command=process_mapping).grid(
    row=len(format_names) + 1, column=0, pady=10
)

# 运行主循环
root.mainloop()
