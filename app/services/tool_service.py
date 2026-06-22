# =============================================================================
# 工具管理服务模块 (Tool Service)
# =============================================================================
# 本模块使用注册表模式（Registry Pattern）管理所有可用工具，
# 提供工具的注册、查询、列表和执行功能。
#
# 设计要点：
#   - 通过类级别的 _tools 字典集中管理工具注册表
#   - 工具注册与执行解耦，便于动态扩展新工具
#   - 异常安全：工具执行时的异常被捕获并返回友好的错误信息
# =============================================================================

from app.tools.calculator import calculator
from app.tools.data_analyzer import data_analyzer
from app.tools.web_search import web_search


class ToolService:
    """工具管理服务

    管理所有可用的工具，支持工具注册、查询和动态加载。
    使用类方法模式，无需实例化即可操作全局工具注册表。

    当前内置工具:
        - calculator: 计算器工具，用于执行数学运算
        - data_analyzer: 数据分析工具，用于处理和分析数据
        - web_search: 网络搜索工具，用于检索互联网信息

    使用示例:
        >>> ToolService.get_all_tools()          # 获取所有工具
        >>> ToolService.get_tool("calculator")    # 获取单个工具
        >>> ToolService.execute_tool("calculator", expression="1+1")  # 执行工具
    """

    _tools = {
        "calculator": calculator,
        "data_analyzer": data_analyzer,
        "web_search": web_search,
    }
    """工具注册表字典：键为工具名称（字符串），值为工具实例对象。
    所有工具实例需实现 run(**kwargs) -> str 方法以支持统一调用。"""

    @classmethod
    def get_all_tools(cls) -> list:
        """获取所有已注册的工具

        返回:
            list: 所有工具实例对象的列表。
                每个工具对象应包含 run() 方法和描述信息。
        """
        return list(cls._tools.values())

    @classmethod
    def get_tool_names(cls) -> list:
        """获取所有工具名称

        返回:
            list: 所有已注册工具的名称字符串列表，如 ["calculator", "data_analyzer", "web_search"]
        """
        return list(cls._tools.keys())

    @classmethod
    def get_tool(cls, name: str):
        """通过名称获取工具

        参数:
            name (str): 工具名称，需与注册时的键名一致

        返回:
            object 或 None: 找到的工具实例对象，若不存在则返回 None
        """
        return cls._tools.get(name)

    @classmethod
    def register_tool(cls, name: str, tool):
        """注册新工具

        允许在运行时动态添加新工具到注册表中，
        方便功能扩展和插件化开发。

        参数:
            name (str): 工具名称（注册键名），需全局唯一
            tool (object): 工具实例对象，需实现 run(**kwargs) -> str 接口
        """
        cls._tools[name] = tool

    @classmethod
    def execute_tool(cls, name: str, **kwargs) -> str:
        """执行指定工具

        根据工具名称查找并执行对应的工具，支持任意关键字参数传递给工具。
        执行过程中的异常会被捕获并以字符串形式返回，保证调用方不会因为
        工具异常而崩溃。

        参数:
            name (str): 要执行的工具名称
            **kwargs: 传递给工具 run() 方法的关键字参数

        返回:
            str: 工具执行结果字符串。
                若工具未找到，返回 "未找到工具: {name}"
                若执行过程抛出异常，返回 "工具执行失败: {异常信息}"
                正常情况下返回工具 run() 方法的返回值
        """
        tool = cls._tools.get(name)
        if not tool:
            return f"未找到工具: {name}"
        try:
            return tool.run(**kwargs)
        except Exception as e:
            return f"工具执行失败: {str(e)}"
