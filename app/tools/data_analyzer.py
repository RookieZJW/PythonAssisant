"""
数据分析工具模块
==================
提供 JSON 格式数据的统计分析功能。
接收 JSON 格式的数据字符串，使用 Pandas 和 NumPy 进行：
- 基本数据概览（行数、列数、列名）
- 数值列统计（均值、中位数、标准差、最大/最小值）
- 分类列统计（最常见值及其频次）
- 缺失值统计（缺失数量和占比）

可作为 LangChain 工具供 AI 模型调用。
"""
import pandas as pd
import numpy as np
import json
from langchain_core.tools import tool


@tool
def data_analyzer(data_json: str) -> str:
    """
    对传入的 JSON 格式数据进行分析，返回统计分析结果。
    当用户需要分析数据、统计信息、生成摘要时使用此工具。

    参数:
        data_json (str): JSON 格式的数据字符串
            支持 JSON 数组（自动转换为 DataFrame 的多行数据）
            或 JSON 对象（自动转换为单行 DataFrame）

    返回:
        str: 格式化的统计分析结果文本

    示例:
        >>> data_analyzer('[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]')
        '数据形状: 2 行 x 2 列\\n列名: name, age\\n\\n--- 数值列统计 ---\\nage: 均值=27.50, ...'
    """
    try:
        # 解析 JSON 字符串为 Python 对象
        data = json.loads(data_json)

        # 转换为 pandas DataFrame
        if isinstance(data, list):
            # JSON 数组 -> 多行 DataFrame
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # JSON 对象 -> 单行 DataFrame（包裹在列表中）
            df = pd.DataFrame([data])
        else:
            return "错误: 数据格式不支持，请传入 JSON 数组或对象"

        # ----- 构建分析结果文本 -----
        result_parts = []

        # 1. 数据基本概览
        result_parts.append(f"数据形状: {df.shape[0]} 行 x {df.shape[1]} 列")
        result_parts.append(f"列名: {', '.join(df.columns.tolist())}")

        # 2. 数值列统计
        # 自动筛选出所有数值类型的列（int, float 等）
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            result_parts.append("\n--- 数值列统计 ---")
            # 使用 describe() 获取常见统计量
            stats = df[numeric_cols].describe()
            for col in numeric_cols:
                result_parts.append(
                    f"{col}: 均值={stats[col]['mean']:.2f}, "
                    f"中位数={df[col].median():.2f}, "
                    f"标准差={stats[col]['std']:.2f}, "
                    f"最小值={stats[col]['min']:.2f}, "
                    f"最大值={stats[col]['max']:.2f}"
                )

        # 3. 分类列统计
        # 自动筛选出所有字符串/分类类型的列
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(cat_cols) > 0:
            result_parts.append("\n--- 分类列统计 ---")
            for col in cat_cols:
                # 显示前 5 个最常见的取值及其频次
                value_counts = df[col].value_counts().head(5)
                result_parts.append(f"{col} 最常见值: {dict(value_counts)}")

        # 4. 缺失值统计
        # 检查每列的缺失值数量
        missing = df.isnull().sum()
        missing_cols = missing[missing > 0]
        if len(missing_cols) > 0:
            result_parts.append("\n--- 缺失值统计 ---")
            for col, count in missing_cols.items():
                # 显示缺失数量和缺失占比（百分比）
                result_parts.append(f"{col}: {count} 个缺失值 ({count / len(df) * 100:.1f}%)")

        return "\n".join(result_parts)

    except json.JSONDecodeError:
        # JSON 解析失败
        return "错误: JSON 格式无效"
    except Exception as e:
        # 其他分析过程中发生的错误
        return f"分析错误: {str(e)}"
