import os


def parse_wlbi_to_matrix(file_path):
    """
    解析WLBI格式文件，根据y轴分行，将257转换为S，输出完整矩阵
    """
    # 读取文件
    with open(file_path, "r") as file:
        lines = file.readlines()

    # 存储坐标数据
    coordinates = []

    # 解析坐标数据
    in_map_section = False
    for line in lines:
        line = line.strip()

        # 检查是否进入MAP部分
        if line == "[MAP]:":
            in_map_section = True
            continue

        # 只处理MAP部分的数据
        if not in_map_section:
            continue

        # 跳过统计信息和结束标记
        if (
            line.startswith("Total Prober")
            or line.startswith("Bin")
            or line.startswith("## END ##")
        ):
            continue

        # 解析坐标数据
        parts = line.split()
        if len(parts) >= 3:
            try:
                x = int(parts[0])
                y = int(parts[1])
                bin_value = int(parts[2])

                # 将257转换为S
                value = "S" if bin_value == 257 else str(bin_value)

                coordinates.append((x, y, value))
            except ValueError:
                continue

    if not coordinates:
        return []

    # 确定坐标范围
    x_values = [coord[0] for coord in coordinates]
    y_values = [coord[1] for coord in coordinates]

    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)

    # 创建空矩阵
    matrix = []

    # 按y轴排序
    sorted_coords = sorted(coordinates, key=lambda c: (c[1], c[0]))

    # 初始化当前y值和行
    current_y = None
    current_row = []

    # 构建矩阵
    for x, y, value in sorted_coords:
        # 如果y值变化，开始新行
        if current_y is None or y != current_y:
            if current_row:
                matrix.append(current_row)
            current_row = []
            current_y = y

        # 填充空位置
        while len(current_row) < (x - min_x):
            current_row.append(".")

        # 添加当前值
        current_row.append(value)

    # 添加最后一行
    if current_row:
        matrix.append(current_row)

    # 确保每行长度一致
    max_length = max(len(row) for row in matrix)
    for i in range(len(matrix)):
        while len(matrix[i]) < max_length:
            matrix[i].append(".")

    return matrix


def print_inform_wafermap(overlayed_map, wlbi_filepath, base_file_name):
    """
    解析WLBI格式文件，根据y轴分行，将257转换为S，输出完整矩阵，并添加Bin统计
    """
    # 处理overlayed_map获取single_line
    cleaned_row = []
    for row in overlayed_map:
        cleaned_row.append(row.replace(".", ""))
    single_line = "".join(cleaned_row)

    headers = []  # 存储头部信息
    coordinates = []  # 存储坐标数据

    # 读取文件并解析
    with open(wlbi_filepath, "r") as file:
        lines = file.readlines()

    in_header_section = True
    for line in lines:
        stripped_line = line.strip()

        # 识别MAP部分开始
        if stripped_line == "[MAP]:":
            in_header_section = False
            continue

        # 收集头部信息
        if in_header_section and stripped_line:
            headers.append(stripped_line)
            continue

        # 跳过非MAP部分和统计行
        if in_header_section or (
            stripped_line.startswith("Total Prober")
            or stripped_line.startswith("Bin")
            or stripped_line.startswith("## END ##")
        ):
            continue

        # 解析坐标数据
        parts = stripped_line.split()
        if len(parts) >= 3:
            try:
                x = int(parts[0])
                y = int(parts[1])
                coordinates.append((x, y))
            except ValueError:
                continue

    # 更新坐标值并统计Bin
    bin_counts = {}  # 用于统计Bin出现次数
    updated_coordinates = []
    index = 0  # 用于遍历single_line
    for x, y in coordinates:
        if index < len(single_line):
            if single_line[index] == "S":
                bin_value = "257"
            else:
                bin_value = single_line[index]
            # S转换为257

            updated_coordinates.append((x, y, bin_value))

            # 更新统计
            bin_counts[str(bin_value)] = bin_counts.get(bin_value, 0) + 1
            index += 1

        else:
            break  # 数据不足时停止
    # 计算总测试数和通过率
    total_tested = len(updated_coordinates) - 2
    total_pass = 0
    for bin_value, count in bin_counts.items():
        if bin_value in ["1", "A"]:  # 根据你的规则，"1"和"A"都可能表示通过
            total_pass += count

    total_fail = total_tested - total_pass
    yield_percentage = (total_pass / total_tested) * 100 if total_tested > 0 else 0

    # 生成输出文件路径
    output_wafermap_path = os.path.join(
        "输出文件/wafermap", f"{base_file_name}_overlayed.mapEx"
    )

    with open(output_wafermap_path, "w") as file:
        # 写入头部信息
        for line in headers:
            # 更新统计相关头部信息
            if line.startswith("Total Tested:"):
                file.write(f"Total Tested: {total_tested}\n")
            elif line.startswith("Total Pass:"):
                file.write(f"Total Pass: {total_pass}\n")
            elif line.startswith("Total Fail:"):
                file.write(f"Total Fail: {total_fail}\n")
            elif line.startswith("Yield:"):
                file.write(f"Yield: {yield_percentage:.2f}%\n")
            else:
                file.write(f"{line}\n")

        file.write("\n[MAP]:\n")  # 分隔头部和MAP数据

        # 写入坐标数据
        for x, y, value in updated_coordinates:
            file.write(f"{x} {y} {value}\n")

        # 写入Bin统计信息
        file.write(f"\nTotal Prober Test Dies: {total_tested}\n")
        file.write(f"Total Prober Pass Dies: {total_pass}\n")

        # 按格式输出Bin统计（0-150）
        for bin_num in range(0, 151):
            bin_str = f"Bin {bin_num:2d}" if bin_num < 100 else f"Bin{bin_num:3d}"
            count = bin_counts.get(str(bin_num), 0)

            # 每行输出7个Bin
            if bin_num > 0 and bin_num % 7 == 0:
                file.write("\n")
            file.write(f"{bin_str}    {count},  ")

        file.write("\n\n## END ##\n")  # 结束标记
