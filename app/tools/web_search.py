import requests
from langchain_core.tools import tool


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """
    搜索互联网信息。
    当用户询问实时信息、新闻或你不知道的内容时使用此工具。
    参数:
        query - 搜索关键词
        num_results - 返回结果数量，默认5条
    """
    try:
        # 使用 DuckDuckGo 的即时回答 API（无需 API Key）
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        results = []

        # 即时回答
        if data.get("AbstractText"):
            results.append(f"摘要: {data['AbstractText']}")

        # 相关主题
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"- {topic['Text']}")

        if not results:
            return f"未找到与 '{query}' 相关的搜索结果。"

        return "\n".join(results)

    except requests.exceptions.Timeout:
        return "搜索超时，请稍后重试。"
    except requests.exceptions.RequestException as e:
        return f"搜索请求失败: {str(e)}"
    except Exception as e:
        return f"搜索错误: {str(e)}"
