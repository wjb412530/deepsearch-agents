"""
Tavily 网络搜索工具模块

封装 internet_search 工具，供网络搜索子智能体检索互联网公开信息
工具内部会先通过 monitor 上报调用参数，再请求 Tavily API 返回结构化搜索结果
"""

import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.tools import tool
from tavily import TavilyClient

from app.api.monitor import monitor
from app.utils.cache import cache_get, cache_set, generate_cache_key

load_dotenv()


# TavilyClient 是实际访问搜索服务的客户端；模块级复用可避免每次工具调用重复初始化
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# @tool 会把函数签名和 docstring 暴露给 DeepAgents，模型据此决定是否调用以及如何填参
@tool
def internet_search(
    query: str,
    topic: Literal["news", "finance", "general"] = "general",
    max_results: int = 5,
    include_raw_content: bool = False,
):
    """
    根据用户问题检索互联网公开信息

    注意：本工具只用于外部公开网页、新闻、政策等信息，不用于查询业务数据库或 RAGFlow 私有知识库
    :param query: 搜索关键词或自然语言问题
    :param topic: 搜索主题，可选 news、finance、general
    :param max_results: 返回的最大结果数
    :param include_raw_content: 是否返回网页原文内容；False 返回摘要，True 尝试返回更完整正文
    :return: Tavily 返回的结构化搜索结果
    """
    # 生成缓存键（基于所有查询参数）
    cache_key = generate_cache_key(
        "tavily_search",
        query,
        topic,
        max_results,
        include_raw_content
    )

    # 尝试从缓存获取结果
    cached_result = cache_get(cache_key)
    if cached_result is not None:
        # 缓存命中，上报工具调用（标记为缓存命中）
        monitor.report_tool(
            tool_name="网络搜索工具",
            args={
                "query": query,
                "topic": topic,
                "max_results": max_results,
                "include_raw_content": include_raw_content,
                "cache_hit": True,
            },
        )
        return cached_result

    # 缓存未命中，上报工具调用
    monitor.report_tool(
        tool_name="网络搜索工具",
        args={
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "include_raw_content": include_raw_content,
            "cache_hit": False,
        },
    )

    # 调用 Tavily API 获取搜索结果
    result = tavily_client.search(
        query=query,
        topic=topic,
        max_results=max_results,
        include_raw_content=include_raw_content,
    )

    # 将结果存入缓存（异步操作，失败不影响返回）
    cache_set(cache_key, result)

    return result


if __name__ == "__main__":
    from pprint import pprint

    # 本地调试入口：直接运行本文件可验证 TAVILY_API_KEY 和 Tavily API 是否可用
    pprint(
        internet_search.invoke(
            {"query": "2026中国法定节假日放假安排表，我天天都想要放假"}
        )
    )
