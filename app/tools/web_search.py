"""
网络搜索工具模块
===================
提供互联网信息搜索功能，使用 DuckDuckGo 的即时回答 API。
无需 API Key，完全免费，适合获取实时信息、新闻或补充知识库。

主要功能：
- 搜索互联网信息并返回摘要和相关主题
- 支持控制返回结果数量
- 包含超时处理和异常处理

可作为 LangChain 工具供 AI 模型调用。
"""
import requests
from langchain_core.tools import tool


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """
    搜索互联网信息。
    当用户询问实时信息、新闻或你不知道的内容时使用此工具。

    参数:
        query (str): 搜索关键词，描述要查找的内容
        num_results (int): 返回结果数量，默认 5 条

    返回:
        str: 格式化的搜索结果文本，包含摘要和相关主题

    示例:
        >>> web_search("2024年诺贝尔奖")
        '摘要: ...\\n- 相关主题1\\n- 相关主题2'
    """
    try:
        # 使用 DuckDuckGo 的即时回答 API（无需 API Key）
        # 该 API 提供即时摘要和相关主题两个层级的搜索结果
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,                # 搜索查询词
            "format": "json",          # 返回 JSON 格式
            "no_html": 1,              # 排除 HTML 标签，仅返回纯文本
            "skip_disambig": 1,        # 跳过消歧义页面
        }

        # 发送 HTTP GET 请求，设置 10 秒超时防止长时间等待
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        results = []

        # 1. 提取即时回答摘要（AbstractText 字段提供百科级别的概要）
        if data.get("AbstractText"):
            results.append(f"摘要: {data['AbstractText']}")

        # 2. 提取相关主题（RelatedTopics 提供搜索结果列表）
        # 限制条数不超过 num_results
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"- {topic['Text']}")

        # 如果没有找到任何结果，返回提示信息
        if not results:
            return f"未找到与 '{query}' 相关的搜索结果。"

        # 将所有结果用换行符连接为单一字符串
        return "\n".join(results)

    except requests.exceptions.Timeout:
        # 请求超时处理（超过 10 秒未响应）
        return "搜索超时，请稍后重试。"
    except requests.exceptions.RequestException as e:
        # 网络请求相关异常（DNS 解析失败、连接被拒绝等）
        return f"搜索请求失败: {str(e)}"
    except Exception as e:
        # 其他未知错误
        return f"搜索错误: {str(e)}"
