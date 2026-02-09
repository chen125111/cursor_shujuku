"""
数据库初始化脚本
从 CSV/Excel 文件导入数据到数据库
"""

import os
import zipfile
import pandas as pd

from backend.database import init_database, batch_create_records, get_statistics

def import_data_from_excel(file_path: str = "date.csv"):
    """从 CSV/Excel 文件导入数据"""
    print("="*50)
    print("   气体混合物数据导入工具")
    print("="*50)
    
    # 1. 初始化数据库
    print("\n[1/3] 初始化数据库...")
    init_database()
    
    # 2. 读取Excel文件
    print(f"\n[2/3] 读取数据文件: {file_path}")
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".csv", ".tsv"]:
            if zipfile.is_zipfile(file_path):
                df = pd.read_excel(file_path)
                print("    [WARN] 文件扩展名为 CSV，但内容为 Excel（xlsx）；已改用 read_excel 读取")
            else:
                sep = "\t" if ext == ".tsv" else None
                encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk", "latin1"]
                df = None
                last_err = None
                for enc in encodings:
                    try:
                        df = pd.read_csv(
                            file_path,
                            sep=sep,
                            engine="python",
                            encoding=enc,
                        )
                        print(f"    [OK] 检测到编码: {enc}")
                        break
                    except UnicodeDecodeError as e:
                        last_err = e
                    except Exception as e:
                        last_err = e
                if df is None:
                    try:
                        df = pd.read_csv(
                            file_path,
                            sep=sep,
                            engine="python",
                            encoding="utf-8",
                            encoding_errors="replace",
                        )
                        print("    [WARN] 使用 utf-8 + replace 兜底读取（可能存在少量乱码字符）")
                    except Exception:
                        raise last_err or RuntimeError("读取 CSV 失败")
        elif ext in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
        print(f"    [OK] 成功读取 {len(df)} 条记录")
        print(f"    [OK] 列名: {df.columns.tolist()}")
    except Exception as e:
        print(f"    [ERROR] 读取文件失败: {e}")
        return
    
    # 3. 转换数据格式并导入
    print("\n[3/3] 导入数据到数据库...")
    
    # 映射列名到数据库字段
    column_mapping = {
        'T (K)': 'temperature',
        'xCH4': 'x_ch4',
        'xC2H6': 'x_c2h6',
        'xC3H8': 'x_c3h8',
        'xCO2': 'x_co2',
        'xN2': 'x_n2',
        'xH2S': 'x_h2s',
        'x i-C4H10': 'x_ic4h10',
        'p (MPa)': 'pressure'
    }
    
    # 转换为记录列表
    records = []
    for _, row in df.iterrows():
        record = {}
        for excel_col, db_col in column_mapping.items():
            if excel_col in df.columns:
                value = row[excel_col]
                # 处理NaN值
                record[db_col] = 0 if pd.isna(value) else float(value)
            else:
                record[db_col] = 0
        records.append(record)
    
    # 批量插入
    try:
        count = batch_create_records(records)
        print(f"    [OK] 成功导入 {count} 条记录")
    except Exception as e:
        print(f"    [ERROR] 导入失败: {e}")
        return
    
    # 4. 显示统计信息
    print("\n" + "="*50)
    print("   导入完成！数据统计")
    print("="*50)
    
    stats = get_statistics()
    print(f"""
    * 总记录数: {stats.get('total_records', 0)}
    * 温度范围: {stats.get('min_temperature', 0):.2f} ~ {stats.get('max_temperature', 0):.2f} K
    * 平均温度: {stats.get('avg_temperature', 0):.2f} K
    * 压力范围: {stats.get('min_pressure', 0):.3f} ~ {stats.get('max_pressure', 0):.3f} MPa
    * 平均压力: {stats.get('avg_pressure', 0):.3f} MPa
    """)
    
    print("\n[DONE] 数据导入完成！运行 'python -m uvicorn backend.main:app --reload' 启动Web应用")

if __name__ == "__main__":
    import_data_from_excel()

