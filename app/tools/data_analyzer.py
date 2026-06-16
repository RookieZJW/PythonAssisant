import pandas as pd
import numpy as np
import json
from langchain_core.tools import tool


@tool
def data_analyzer(data_json: str) -> str:
    """
    对传入的JSON格式数据进行分析，返回统计分析结果。
    当用户需要分析数据、统计信息、生成摘要时使用此工具。
    参数: data_json - JSON格式的数据字符串
    """
    try:
        data = json.loads(data_json)

        # 转换为 DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            return "错误: 数据格式不支持，请传入 JSON 数组或对象"

        # 基础统计
        result_parts = []

        result_parts.append(f"数据形状: {df.shape[0]} 行 x {df.shape[1]} 列")
        result_parts.append(f"列名: {', '.join(df.columns.tolist())}")

        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            result_parts.append("\n--- 数值列统计 ---")
            stats = df[numeric_cols].describe()
            for col in numeric_cols:
                result_parts.append(
                    f"{col}: 均值={stats[col]['mean']:.2f}, "
                    f"中位数={df[col].median():.2f}, "
                    f"标准差={stats[col]['std']:.2f}, "
                    f"最小值={stats[col]['min']:.2f}, "
                    f"最大值={stats[col]['max']:.2f}"
                )

        # 分类列统计
        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(cat_cols) > 0:
            result_parts.append("\n--- 分类列统计 ---")
            for col in cat_cols:
                value_counts = df[col].value_counts().head(5)
                result_parts.append(f"{col} 最常见值: {dict(value_counts)}")

        # 缺失值统计
        missing = df.isnull().sum()
        missing_cols = missing[missing > 0]
        if len(missing_cols) > 0:
            result_parts.append("\n--- 缺失值统计 ---")
            for col, count in missing_cols.items():
                result_parts.append(f"{col}: {count} 个缺失值 ({count / len(df) * 100:.1f}%)")

        return "\n".join(result_parts)

    except json.JSONDecodeError:
        return "错误: JSON 格式无效"
    except Exception as e:
        return f"分析错误: {str(e)}"
