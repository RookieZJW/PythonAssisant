import math
from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """
    执行数学计算表达式。
    当用户需要进行数学计算时使用此工具。
    参数: expression - 数学表达式字符串，例如 "2 + 3 * 4"
    """
    try:
        # 使用安全的数学命名空间
        allowed_names = {
            k: v for k, v in math.__dict__.items()
            if not k.startswith("__")
        }
        allowed_names["abs"] = abs
        allowed_names["round"] = round
        allowed_names["pow"] = pow
        allowed_names["min"] = min
        allowed_names["max"] = max

        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"计算结果: {result}"
    except ZeroDivisionError:
        return "错误: 不能除以零"
    except SyntaxError:
        return "错误: 表达式语法不正确"
    except Exception as e:
        return f"计算错误: {str(e)}"
