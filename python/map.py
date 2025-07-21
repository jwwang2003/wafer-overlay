import json
import os

import pandas as pd

input_file_path = "叠图输入文件/衬底/1-86107919CNF1.xls"

file_basename = os.path.basename(input_file_path)
file_name = os.path.splitext(file_basename)[0]
output_dir = os.path.join("输出衬底", file_name)
os.makedirs(output_dir, exist_ok=True)

try:
    excel_file = pd.ExcelFile(input_file_path)
except Exception as e:
    print(f"读取XLS文件失败：{e}")
    exit()

sheets_config = {
    "Surface defect list": "surface",
    "PL defect list": "PL"
}

for sheet_name, suffix in sheets_config.items():
    try:
        df = excel_file.parse(sheet_name)
        required_columns = ["X(mm)", "Y(mm)", "W(um)", "H(um)", "Class"]
        available_columns = [col for col in required_columns if col in df.columns]
        if not available_columns:
            continue
        
        data = df[available_columns]
        data_list = data.to_dict(orient="records")
        output_json_name = f"{suffix}.json"
        output_json_path = os.path.join(output_dir, output_json_name)
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)
        
        print(f"已生成：{output_json_path}")
    
    except Exception as e:
        print(f"处理工作表{sheet_name}时出错：{e}")

