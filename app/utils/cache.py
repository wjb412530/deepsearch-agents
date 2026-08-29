"""
Redis 缓存工具模块

提供 Redis 连接和缓存操作，支持优雅降级：
- Redis 连接失败时静默降级，不影响主业务流程
- 所有缓存操作失败时返回 None，由调用方决定后续逻辑
"""

import os
import json
import hashlib
import logging
from typing import Optional, Any
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# 全局 Redis 客户端实例
_redis_client: Optional[Redis] = None
_redis_enabled: bool = False


def _init_redis_client() -> Optional[Redis]:
    """
    初始化 Redis 客户端

    Returns:
        Redis 客户端实例，连接失败时返回 None
    """
    global _redis_client, _redis_enabled

    # 检查是否启用 Redis
    redis_enabled_str = os.getenv("REDIS_ENABLED", "false").lower()
    _redis_enabled = redis_enabled_str in ("true", "1", "yes")

    if not _redis_enabled:
        logger.info("Redis caching is disabled (REDIS_ENABLED=false)")
        return None

    # 获取 Redis URL
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        client = Redis.from_url(redis_url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
        # 测试连接
        client.ping()
        logger.info(f"Redis client initialized successfully: {redis_url}")
        return client
    except RedisError as e:
        logger.warning(f"Failed to connect to Redis at {redis_url}: {e}. Caching will be disabled.")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error initializing Redis: {e}. Caching will be disabled.")
        return None


def get_redis_client() -> Optional[Redis]:
    """
    获取 Redis 客户端实例（懒加载）

    Returns:
        Redis 客户端，未启用或连接失败时返回 None
    """
    global _redis_client

    if _redis_client is None and _redis_enabled:
        _redis_client = _init_redis_client()

    return _redis_client


def generate_cache_key(prefix: str, *args: Any) -> str:
    """
    生成缓存键，使用 MD5 哈希确保键长度可控

    Args:
        prefix: 键前缀（如 "tavily_search", "ragflow_list"）
        *args: 用于生成键的参数

    Returns:
        格式为 "prefix:md5_hash" 的缓存键
    """
    # 将参数序列化为 JSON 字符串
    params_str = json.dumps(args, sort_keys=True, ensure_ascii=False)
    # 计算 MD5 哈希
    hash_value = hashlib.md5(params_str.encode("utf-8")).hexdigest()
    return f"{prefix}:{hash_value}"


def cache_get(key: str) -> Optional[Any]:
    """
    从缓存获取数据

    Args:
        key: 缓存键

    Returns:
        缓存的数据（JSON 反序列化后），未命中或失败时返回 None
    """
    client = get_redis_client()
    if client is None:
        return None

    try:
        value = client.get(key)
        if value is None:
            logger.debug(f"Cache miss: {key}")
            return None

        logger.info(f"Cache hit: {key}")
        return json.loads(value)
    except RedisError as e:
        logger.warning(f"Redis get failed for key {key}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to decode cached value for key {key}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error getting cache for key {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    设置缓存数据

    Args:
        key: 缓存键
        value: 要缓存的数据（会被 JSON 序列化）
        ttl: 过期时间（秒），None 则使用默认值 SEARCH_CACHE_TTL

    Returns:
        设置成功返回 True，失败返回 False
    """
    client = get_redis_client()
    if client is None:
        return False

    # 获取默认 TTL
    if ttl is None:
        ttl = int(os.getenv("SEARCH_CACHE_TTL", "3600"))

    try:
        value_str = json.dumps(value, ensure_ascii=False)
        client.setex(key, ttl, value_str)
        logger.info(f"Cache set: {key} (TTL: {ttl}s)")
        return True
    except RedisError as e:
        logger.warning(f"Redis set failed for key {key}: {e}")
        return False
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize value for key {key}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error setting cache for key {key}: {e}")
        return False


def cache_delete(key: str) -> bool:
    """
    删除缓存数据

    Args:
        key: 缓存键

    Returns:
        删除成功返回 True，失败返回 False
    """
    client = get_redis_client()
    if client is None:
        return False

    try:
        client.delete(key)
        logger.info(f"Cache deleted: {key}")
        return True
    except RedisError as e:
        logger.warning(f"Redis delete failed for key {key}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error deleting cache for key {key}: {e}")
        return False


def is_cache_enabled() -> bool:
    """
    检查缓存是否已启用且可用

    Returns:
        缓存可用返回 True，否则返回 False
    """
    return get_redis_client() is not None
