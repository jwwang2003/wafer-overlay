def parse_wlbi_to_matrix(file_path):
    """
    解析WLBI格式文件，根据y轴分行，将257转换为S，输出完整矩阵
    """
    # 读取文件
    with open(file_path, 'r') as file:
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
        if line.startswith('Total Prober') or line.startswith('Bin') or line.startswith('## END ##'):
            continue
        
        # 解析坐标数据
        parts = line.split()
        if len(parts) >= 3:
            try:
                x = int(parts[0])
                y = int(parts[1])
                bin_value = int(parts[2])
                
                # 将257转换为S
                value = 'S' if bin_value == 257 else str(bin_value)
                
                coordinates.append((x, y, value))
            except ValueError:
                continue
    
    # 如果没有坐标数据，返回空列表
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
            current_row.append('.')
        
        # 添加当前值
        current_row.append(value)
    
    # 添加最后一行
    if current_row:
        matrix.append(current_row)
    
    # 确保每行长度一致
    max_length = max(len(row) for row in matrix)
    for i in range(len(matrix)):
        while len(matrix[i]) < max_length:
            matrix[i].append('.')
    
    return matrix

# 示例使用
if __name__ == "__main__":
    file_path = "/Users/tan/Downloads/AOI项目/AOI/叠图输入文件/WLBI/B003332/B003332-01_20250325_170454.WaferMap"  # 替换为实际文件路径
    matrix = parse_wlbi_to_matrix(file_path)
    
    # 打印矩阵
    for row in matrix:
        print(''.join(row))
