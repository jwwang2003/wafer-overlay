# three.js有点复杂了
from PIL import Image, ImageDraw, ImageFont


def generate_color_image(
    overlayed_map,
    save_path,
    cell_width=30,
    cell_height=20,
    table_data={
        "产品名称": "S1M032120B_B003332_03",
        "晶圆尺寸": "150.000",
        "步距": "4986.000, 3740.000",
        "切角": "180°（下）",
        "时间": "2025-04-10 15:20:16",
        "晶粒总数": 805,
        "测试总数": 805,
        "良品": 718,
        "次品": 87,
        "良率": "89.19%",
    },
):
    # 颜色映射
    color_map = {
        ".": (220, 220, 220),  # 灰
        "1": (76, 175, 80),  # 绿
        "3": (33, 150, 243),  # 蓝
        "4": (244, 67, 54),  # 红
        "5": (255, 193, 7),  # 黄
        "S": (0, 0, 0),  # 黑
    }

    rows = len(overlayed_map)
    cols = len(overlayed_map[0])

    # 主图大小
    img_width = cols * cell_width
    img_height = rows * cell_height

    # 表格参数
    table_rows = len(table_data) if table_data else 0
    table_row_height = 30
    table_height = table_rows * table_row_height + 20 if table_rows else 0

    # 总图像高度 = 主图 + 表格
    total_height = img_height + table_height

    # 创建图片
    img = Image.new("RGB", (img_width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 尝试加载字体
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    # 画主图内容（cell）
    for y, row in enumerate(overlayed_map):
        for x, ch in enumerate(row):
            color = color_map.get(ch, (255, 255, 255))
            x0 = x * cell_width
            y0 = y * cell_height
            x1 = x0 + cell_width
            y1 = y0 + cell_height
            draw.rectangle([x0, y0, x1, y1], fill=color, outline=(180, 180, 180))

    # 画下方表格
    if table_data:
        table_top = img_height + 10
        col_widths = [img_width // 2, img_width // 2]
        for i, (key, value) in enumerate(table_data.items()):
            y_top = table_top + i * table_row_height
            # 左侧表头格
            draw.rectangle(
                [0, y_top, col_widths[0], y_top + table_row_height], outline="black"
            )
            draw.text((10, y_top + 5), str(key), fill="black", font=font)
            # 右侧数值格
            draw.rectangle(
                [col_widths[0], y_top, img_width, y_top + table_row_height],
                outline="black",
            )
            draw.text(
                (col_widths[0] + 10, y_top + 5), str(value), fill="black", font=font
            )

    # 保存图片
    img.save(save_path)
