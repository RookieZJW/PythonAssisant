"""
计算器工具模块
=================
提供安全的数学表达式计算功能。
通过限制 eval 的命名空间，仅允许使用 math 模块中的数学函数，
禁止访问任何 Python 内置函数（__builtins__ 被置空），
从而实现安全的表达式求值。

可作为 LangChain 工具供 AI 模型调用。
"""
import math
from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """
    执行数学计算表达式。
    当用户需要进行数学计算时使用此工具。

    参数:
        expression (str): 数学表达式字符串，例如 "2 + 3 * 4" 或 "sin(pi/2)"

    返回:
        str: 计算结果或错误信息

    示例:
        >>> calculator("2 + 3 * 4")
        '计算结果: 14'
        >>> calculator("sqrt(16) + log(100, 10)")
        '计算结果: 6.0'
        >>> calculator("1 / 0")
        '错误: 不能除以零'
    """
    try:
        # 构建安全的数学命名空间
        # 从 math 模块中提取所有非私有函数（不以 __ 开头）
        allowed_names = {
            k: v for k, v in math.__dict__.items()
            if not k.startswith("__")
        }
        # 补充 Python 内置的安全函数
        allowed_names["abs"] = abs      # 绝对值
        allowed_names["round"] = round  # 四舍五入
        allowed_names["pow"] = pow      # 幂运算（比 math.pow 更灵活）
        allowed_names["min"] = min      # 最小值
        allowed_names["max"] = max      # 最大值

        # 执行表达式求值
        # 将 __builtins__ 置空以阻止调用任何 Python 内置函数
        # 仅允许在 allowed_names 限定的命名空间内运算
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"计算结果: {result}"
    except ZeroDivisionError:
        # 捕获除零错误
        return "错误: 不能除以零"
    except SyntaxError:
        # 捕获表达式语法错误
        return "错误: 表达式语法不正确"
    except Exception as e:
        # 捕获其他所有可能的异常（如数学域错误、名称错误等）
        return f"计算错误: {str(e)}"
