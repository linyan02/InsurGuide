import pandas as pd
import os
import re


class InsuranceTableProcessor:
    def __init__(self):
        pass

    def _clean_text(self, text):
        """清洗文本：去除换行、多余空格"""
        if pd.isna(text):
            return ""
        return str(text).strip().replace('\n', ' ').replace('\r', '')

    def _get_file_config(self, filename):
        """
        根据文件名匹配不同的解析策略
        返回: (header_rows, attr_col_cnt, start_row)
        """
        if '百万医疗' in filename:
            # 标准格式：第0行是表头，前3列是属性
            return ([0], 3, 1)
        elif '众民保' in filename:
            # 众民保：第2行是表头（索引2），前2列是属性
            return ([2], 2, 3)
        elif '少儿门急诊' in filename:
            # 多层表头：第0行和第1行共同组成表头
            return ([0, 1], 1, 2)
        elif '小额住院保' in filename:
            # 混合表头：第0行是产品名，第2行是计划名
            return ([0, 2], 2, 3)
        elif '工作表1' in filename:
            return ([0], 3, 1)
        else:
            # 默认兜底策略
            return ([0], 1, 1)

    def process_file(self, file_path):
        filename = os.path.basename(file_path)
        print(f"正在处理: {filename} ...")

        try:
            df = pd.read_csv(file_path, header=None)
            header_rows, attr_col_cnt, start_row = self._get_file_config(filename)

            # --- 1. 构建产品名称（处理多行表头）---
            # 提取表头区域
            headers_df = df.iloc[header_rows, attr_col_cnt:].copy()
            # 填充第一行表头的空值（处理合并单元格，如“众安住院保”跨两列）
            headers_df.iloc[0] = headers_df.iloc[0].ffill()

            product_names = []
            for col in headers_df.columns:
                parts = []
                for row_idx in header_rows:
                    val = headers_df.at[row_idx, col]
                    val_str = self._clean_text(val)
                    if val_str and val_str not in ['/', 'nan', '产品名称']:
                        parts.append(val_str)
                # 组合多级表头，例如 "大地熊猫 - 有社保"
                full_name = " - ".join(parts) if parts else f"未命名产品_{col}"
                product_names.append(full_name)

            # --- 2. 遍历数据行（状态机逻辑）---
            # 这是一个状态列表，用于记录当前行的“父级分类”
            # 例如：[必选责任, 一般医疗, 保额]
            # 如果下一行只写了 "免赔额"，我们需要复用前两级分类
            current_attrs = [None] * attr_col_cnt

            processed_data = []  # 存储处理后的中间数据

            for idx in range(start_row, len(df)):
                row = df.iloc[idx]

                # 更新属性层级状态
                # 逻辑：如果当前列有值，则更新该层级及之后所有层级；
                # 如果当前列为空，则保持该层级不变（继承上文），除非它是第一级且发生大类切换

                # 更稳健的逻辑：
                # 1. 找到当前行第一个非空的属性列 index
                first_valid_idx = -1
                for i in range(attr_col_cnt):
                    if self._clean_text(row[i]):
                        first_valid_idx = i
                        break

                if first_valid_idx != -1:
                    # 更新当前层级
                    current_attrs[first_valid_idx] = self._clean_text(row[first_valid_idx])
                    # 清空子层级（防止 "增值服务" 继承了 "一般医疗" 的 "免赔额"）
                    for k in range(first_valid_idx + 1, attr_col_cnt):
                        current_attrs[k] = None
                        # 如果当前行该子列也有值，则更新
                        if self._clean_text(row[k]):
                            current_attrs[k] = self._clean_text(row[k])
                else:
                    # 全空行，可能是格式行，跳过或继续
                    pass

                # 构建当前行的完整属性名
                # 过滤掉 None 和 空字符串
                valid_attr_parts = [x for x in current_attrs if x]
                attr_name = " - ".join(valid_attr_parts)

                if not attr_name:
                    continue

                # 提取每个产品在该行的值
                for i, prod_name in enumerate(product_names):
                    col_idx = attr_col_cnt + i
                    if col_idx >= len(row): continue

                    val = self._clean_text(row[col_idx])

                    # 只有当值有效时才记录
                    if val and val not in ['/', '\\', 'nan', '-']:
                        processed_data.append({
                            'product': prod_name,
                            'attribute': attr_name,
                            'value': val
                        })

            # --- 3. 生成 Markdown 文档 ---
            # 按产品分组生成
            docs = {}
            for item in processed_data:
                p = item['product']
                if p not in docs:
                    docs[p] = []
                    docs[p].append(f"# 保险产品档案: {p}")
                    docs[p].append(f"数据来源: {filename}")
                    docs[p].append("")

                docs[p].append(f"- **{item['attribute']}**: {item['value']}")

            return list(docs.values())

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            return []


# --- 使用示例 ---
if __name__ == "__main__":
    # 基于脚本位置构建 data/dataset 的绝对路径，适配任意运行目录
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # data/
    _DATASET_DIR = os.path.join(_SCRIPT_DIR, "dataset")

    # 文件路径：data/dataset/ 下的文件
    file_list = [
        os.path.join(_DATASET_DIR, "【保通】百万医疗对比表——持续更新.xlsx - 百万医疗.csv"),
        os.path.join(_DATASET_DIR, "【保通】百万医疗对比表——持续更新.xlsx - 众民保类产品对比.csv"),
        os.path.join(_DATASET_DIR, "【保通】百万医疗对比表——持续更新.xlsx - 少儿门急诊.csv"),
        os.path.join(_DATASET_DIR, "【保通】百万医疗对比表——持续更新.xlsx - 小额住院保.csv"),
    ]
    # Excel 源文件路径（当前脚本读的是 CSV，若需读 xlsx 需改 process_file 用 pd.read_excel）：
    # excel_path = os.path.join(_DATASET_DIR, "【保通】百万医疗对比表——持续更新.xlsx")

    processor = InsuranceTableProcessor()
    all_docs = []

    for f in file_list:
        if os.path.exists(f):
            docs = processor.process_file(f)
            all_docs.extend(docs)

    # 将结果保存为一个大文件，或者按产品保存
    with open('insurance_rag_corpus.md', 'w', encoding='utf-8') as f:
        f.write("\n\n---\n\n".join(all_docs))

    print(f"成功生成 {len(all_docs)} 个产品文档，已保存至 insurance_rag_corpus.md")