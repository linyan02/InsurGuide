"""
将【保通】百万医疗对比表 的「列转行」处理脚本

Excel 原始布局（列式）：
- A 列：字段名（产品名称、保险公司、投保年龄、等待期等）
- B/C 列：子分类（如：必选责任、一般医疗保险金、保额）
- 第 1 行 D-L 列：各产品名称（众安尊享e生、平安e生保等）
- 每行 D-L 列：各产品在该字段下的值

转置后布局（行式）：
- 行 = 产品（每款产品一行）
- 列 = 字段（产品名称、承保公司、投保年龄、等待期等）
"""

import pandas as pd
import os


def _read_excel_safe(excel_path, header=None, **kwargs):
    """
    安全读取 Excel，兼容 WPS/保通等生成的含非标准样式的 .xlsx
    """
    try:
        return pd.read_excel(excel_path, header=header, **kwargs)
    except Exception as e:
        if "Fill" in str(e) or "openpyxl" in str(e).lower():
            try:
                return pd.read_excel(excel_path, engine="calamine", header=header, **kwargs)
            except ImportError:
                raise ImportError("读取该 Excel 需安装 python-calamine") from e
        raise


# 字段名映射（可选）
_FIELD_MAP = {"保险公司": "承保公司", "保障期限": "续保条件"}


def transpose_columns_to_rows(excel_path):
    """
    将「列转行」：原始 Excel 中每列一个产品 → 转成每行一个产品、每列一个字段。

    原始结构：
        A列(字段)   B     C    |  D(产品1)  E(产品2)  F(产品3) ...
        产品名称    -     -    |  众安尊享  平安e生保  安欣保
        保险公司    -     -    |  众安财险  平安健康  平安健康
        投保年龄    -     -    |  30天-70岁 28天-55岁 28天-70岁
        ...

    转置后结构：
        产品名称    承保公司    投保年龄    等待期    ...
        众安尊享    众安财险    30天-70岁   30天
        平安e生保   平安健康    28天-55岁   30天
        安欣保      平安健康    28天-70岁   90天
        ...

    :param excel_path: Excel 文件路径
    :return: 转置后的 DataFrame（行=产品，列=字段）
    """
    raw = _read_excel_safe(excel_path, header=None)

    # 产品名：第 0 行，D 列(索引3) 到 L 列(索引11)
    product_col_start = 3
    product_names = raw.iloc[0, product_col_start:].astype(str).str.strip()
    product_names = product_names[product_names != "nan"].tolist()

    if not product_names:
        raise ValueError("未找到产品名称（第 1 行 D 列起）")

    # 第一遍：收集所有字段名（含去重后缀），保证每产品列结构一致
    all_field_names = []
    seen_fields = {}
    for r in range(1, len(raw)):
        field_parts = []
        for col_idx in range(min(3, raw.shape[1])):
            v = raw.iloc[r, col_idx]
            if pd.notna(v) and str(v).strip():
                field_parts.append(str(v).strip().replace("\n", " ").strip())
        if not field_parts:
            continue
        field_name = " - ".join(field_parts)
        field_name = _FIELD_MAP.get(field_name, field_name)
        if field_name in seen_fields:
            seen_fields[field_name] += 1
            field_name = f"{field_name}_{seen_fields[field_name]}"
        else:
            seen_fields[field_name] = 0
        all_field_names.append((r, field_name))

    # 第二遍：按产品列填充数据
    records = []
    for c in range(len(product_names)):
        rec = {"产品名称": product_names[c]}
        for r, field_name in all_field_names:
            col_idx = product_col_start + c
            if col_idx < raw.shape[1]:
                val = raw.iloc[r, col_idx]
                rec[field_name] = val if pd.notna(val) else ""
        records.append(rec)

    df = pd.DataFrame(records)
    df = df.fillna("")
    # 统一将 \n 转为空格，便于 CSV 展示
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(r"\n", " ", regex=True)
    return df


# ------------------- 使用示例 -------------------
if __name__ == "__main__":
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(_SCRIPT_DIR, "dataset", "【保通】百万医疗对比表——持续更新.xlsx")

    if not os.path.exists(excel_path):
        print(f"❌ 文件不存在：{excel_path}")
    else:
        df = transpose_columns_to_rows(excel_path)
        print(f"✅ 列转行完成：{len(df)} 款产品，{len(df.columns)} 个字段")
        print(df[["产品名称", "承保公司", "投保年龄", "等待期"]].head().to_string())
        # 可选：保存为 CSV
        out_path = os.path.join(_SCRIPT_DIR, "dataset", "百万医疗险_列转行结果.csv")
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\n已保存至：{out_path}")
