from app.tools.calculator import calculator
from app.tools.data_analyzer import data_analyzer
from app.tools.web_search import web_search


class ToolService:
    """工具管理服务

    管理所有可用的工具，支持工具注册、查询和动态加载。
    """

    _tools = {
        "calculator": calculator,
        "data_analyzer": data_analyzer,
        "web_search": web_search,
    }

    @classmethod
    def get_all_tools(cls) -> list:
        """获取所有已注册的工具"""
        return list(cls._tools.values())

    @classmethod
    def get_tool_names(cls) -> list:
        """获取所有工具名称"""
        return list(cls._tools.keys())

    @classmethod
    def get_tool(cls, name: str):
        """通过名称获取工具"""
        return cls._tools.get(name)

    @classmethod
    def register_tool(cls, name: str, tool):
        """注册新工具"""
        cls._tools[name] = tool

    @classmethod
    def execute_tool(cls, name: str, **kwargs) -> str:
        """执行指定工具"""
        tool = cls._tools.get(name)
        if not tool:
            return f"未找到工具: {name}"
        try:
            return tool.run(**kwargs)
        except Exception as e:
            return f"工具执行失败: {str(e)}"
