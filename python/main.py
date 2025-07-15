import os
from tkinter import *
from tkinter import messagebox

import jpg
import wlbi
from PIL import Image

wlbi_filepath = ""


# 读取文件并获取头部信息和芯片地图数据
def read_file(file_path, file_type="default"):
    with open(file_path, "r") as file:
        lines = file.readlines()

    start_line = 0
    for i, line in enumerate(lines):
        if ".*" in line or ".S" in line or "[MAP]:" in line:
            start_line = i
            break

    # 提取头部信息
    header = {}
    for line in lines[:start_line]:
        if ": " in line:
            key, value = line.strip().split(": ", 1)
            header[key.strip()] = value.strip()

    map_data = []
    for line in lines[start_line:]:
        stripped_line = line.strip()
        if stripped_line:
            map_data.append(stripped_line)

    return header, map_data


def overlay_maps(maps, order, debug=False):
    if not maps:
        return []

    ordered_maps = [maps[i] for i in order]
    result = [list(row) for row in ordered_maps[0]]
    debug_info = [] if debug else None

    def get_start_position(line, is_first_line=False):
        # 获取行的起始位置，第一行和其他行逻辑不同
        if not line:
            return 0
        if is_first_line:
            for j in range(len(line) - 1):
                if line[j] == "." and (line[j + 1] == "S" or line[j + 1] == "*"):
                    return j + 2
        else:
            found_dot = False
            for j, char in enumerate(line):
                if char == ".":
                    found_dot = True
                elif found_dot and char.isdigit():
                    return j
        return 0

    def should_replace(current, new):
        # 判断是否应该用新字符替换当前字符
        if new in (".", " "):
            return False
        if current.isdigit() and new.isdigit():
            return int(new) > int(current)
        if current in (".", " "):
            return True
        return not new.isdigit()

    def process_line(result_line, map_line, i, is_first_line):
        # 处理单行的叠加逻辑
        changes = 0
        change_details = []
        result_start = get_start_position(result_line, is_first_line)
        map_start = get_start_position(map_line, is_first_line)
        offset = map_start - result_start

        for j, new_char in enumerate(map_line):
            result_pos = j - offset
            if 0 <= result_pos < len(result_line):
                current_char = result_line[result_pos]
                if should_replace(current_char, new_char):
                    result_line[result_pos] = new_char
                    changes += 1
                    if debug:
                        pos_str = (
                            f"({i},{result_pos})"
                            if not is_first_line
                            else f"(0,{result_pos})"
                        )
                        change_details.append(
                            f"位置 {pos_str}: {current_char} -> {new_char}"
                        )
        return changes, change_details

    # 调试信息初始化
    if debug:
        debug_info.append("===== 叠图过程开始 =====")
        debug_info.append("初始地图:")
        debug_info.extend(["".join(row) for row in result])
        debug_info.append("")

    # 按优先级覆盖地图
    for map_idx, map_data in enumerate(ordered_maps[1:], start=2):
        if debug:
            debug_info.append(f"应用地图 {map_idx}:")
            debug_info.extend(["".join(row) for row in map_data])
            debug_info.append("")
            debug_info.append("叠图后结果:")

        total_changes = 0
        all_change_details = []

        # 处理第一行
        if result and map_data:
            changes, details = process_line(result[0], map_data[0], 0, True)
            total_changes += changes
            all_change_details.extend(details)

        # 处理剩余行
        for i in range(1, min(len(result), len(map_data))):
            changes, details = process_line(result[i], map_data[i], i, False)
            total_changes += changes
            all_change_details.extend(details)

        # 添加调试信息
        if debug:
            debug_info.append(f"本轮修改了 {total_changes} 个位置")
            debug_info.extend(["".join(row) for row in result])
            debug_info.append("")
            debug_info.append("具体更改:")
            debug_info.extend(all_change_details)
            debug_info.append("")

    # 返回结果
    if debug:
        debug_info.append("===== 叠图过程结束 =====")
        debug_info.append("最终地图:")
        debug_info.extend(["".join(row) for row in result])
        return ["".join(row) for row in result], debug_info
    else:
        return ["".join(row) for row in result]


def calculate_stats(map_data):
    # 计算总测试数、通过数、失败数和良率
    total_tested = 0
    total_pass = 0
    for row in map_data:
        for char in row:
            if char != "." and char != "S" and char != "*":
                total_tested += 1
                # '1'和'A'表示通过，其他表示失败
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


# 处理叠图和输出
def process_mapping():
    wlbi_index = format_names.index("WLBI")
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
    debug_dir = output_formats["debug"]
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
            file_path = input_formats[format_name]
            if file_path:

                file_type = format_name
                if format_name == "WLBI":

                    # 检查对应索引的变量值是否为1（被勾选）
                    if format_vars[wlbi_index].get() == 1:
                        wlbi_filepath = file_path

                    map_data = wlbi.parse_wlbi_to_matrix(file_path)  # 调用函数获取列表
                    map_data = [
                        "".join(row) for row in map_data
                    ]  # 将二维列表转换为一维字符串列表
                    for row in map_data:
                        print(row)
                    # file_type = "default"

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
        debug_file = os.path.join(debug_dir, f"debug.txt")
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

        if format_vars[wlbi_index].get() == 1:
            wlbi.print_inform_wafermap(overlayed_map, wlbi_filepath, base_file_name)


def open_sort_dialog():
    selected = [i for i, var in enumerate(format_vars) if var.get() == 1]
    if not selected:
        messagebox.showwarning("警告", "请先选择至少一种格式！")
        return

    sort_window = Toplevel(root)
    sort_window.title("调整叠图顺序")
    sort_window.geometry("300x300")

    # 创建列表框显示选中的格式
    listbox = Listbox(sort_window, selectmode=SINGLE, height=len(selected))
    for i in selected:
        listbox.insert(END, format_names[i])
    listbox.pack(pady=10, fill=BOTH, expand=True)

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
        sorted_formats = [listbox.get(i) for i in range(listbox.size())]
        global format_names
        unselected = [name for i, name in enumerate(format_names) if i not in selected]
        format_names = sorted_formats + unselected
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
    "衬底": "",  # 补充路径
    "AOI": "叠图输入文件/AOI/S1M032120B_B003332/S1M032120B_B003332_01.txt",
    "CP1": "叠图输入文件/CP1/S1M032120B_B003332_1_0/S1M032120B_B003332_01_mapEx.txt",
    "CP2": "叠图输入文件/CP2/S1M032120B_B003332_1_0/S1M032120B_B003332_01_mapEx.txt",
    "FAB": "叠图输入文件/FAB CP/B003332/P0094B_B003332_01.txt",
    "WLBI": "叠图输入文件/WLBI/B003332/B003332-01_20250325_170454.WaferMap",
}

# 定义输出格式的文件夹路径
output_formats = {
    "debug": "输出文件/debug",
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
# format_names = ["衬底", "CP1", "CP2", "WLBI", "CP3", "AOI"]

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
