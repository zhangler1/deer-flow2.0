"""
Redis 缓存实现

提供高性能的分布式缓存功能
"""

from __future__ import annotations

import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 缓存客户端"""

    def __init__(self, redis_url: Optional[str] = None):
        """
        初始化 Redis 客户端

        Args:
            redis_url: Redis 连接字符串 (例如: redis://localhost:6379/0)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._enabled = False

        try:
            import redis

            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # 测试连接
            self._client.ping()
            self._enabled = True
            logger.info(f"Redis 缓存已启用: {self.redis_url}")
        except ImportError:
            logger.warning("Redis 未安装,缓存功能禁用. 安装: pip install redis")
        except Exception as e:
            logger.warning(f"无法连接到 Redis,缓存功能禁用: {e}")

    @property
    def enabled(self) -> bool:
        """是否启用缓存"""
        return self._enabled

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值,不存在则返回 None
        """
        if not self._enabled:
            return None

        try:
            value = self._client.get(key)
            if value is None:
                return None

            # 尝试反序列化 JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"从 Redis 读取失败 [key={key}]: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值 (自动序列化为 JSON)
            ttl: 过期时间 (秒),None 表示永不过期

        Returns:
            是否成功
        """
        if not self._enabled:
            return False

        try:
            # 序列化为 JSON
            if isinstance(value, (dict, list, tuple)):
                serialized = json.dumps(value, ensure_ascii=False)
            else:
                serialized = str(value)

            if ttl:
                self._client.setex(key, ttl, serialized)
            else:
                self._client.set(key, serialized)

            return True
        except Exception as e:
            logger.error(f"写入 Redis 失败 [key={key}]: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        if not self._enabled:
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"从 Redis 删除失败 [key={key}]: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if not self._enabled:
            return False

        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"检查 Redis 键失败 [key={key}]: {e}")
            return False

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        增加计数器

        Args:
            key: 缓存键
            amount: 增加量

        Returns:
            新值,失败返回 None
        """
        if not self._enabled:
            return None

        try:
            return self._client.incrby(key, amount)
        except Exception as e:
            logger.error(f"增加 Redis 计数器失败 [key={key}]: {e}")
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """
        设置过期时间

        Args:
            key: 缓存键
            ttl: 过期时间 (秒)

        Returns:
            是否成功
        """
        if not self._enabled:
            return False

        try:
            self._client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"设置 Redis 过期时间失败 [key={key}]: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的所有键

        Args:
            pattern: 匹配模式 (例如: "user:*")

        Returns:
            删除的键数量
        """
        if not self._enabled:
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"清除 Redis 模式失败 [pattern={pattern}]: {e}")
            return 0

    def get_stats(self) -> dict[str, Any]:
        """
        获取 Redis 统计信息

        Returns:
            统计信息字典
        """
        if not self._enabled:
            return {"enabled": False}

        try:
            info = self._client.info()
            return {
                "enabled": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "hit_rate": (
                    info["keyspace_hits"] / (info["keyspace_hits"] + info["keyspace_misses"])
                    if (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)) > 0
                    else 0
                ),
            }
        except Exception as e:
            logger.error(f"获取 Redis 统计信息失败: {e}")
            return {"enabled": True, "error": str(e)}


# 全局缓存实例
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    获取全局缓存实例

    Returns:
        RedisCache 实例
    """
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def cache(ttl: int = 300, key_prefix: str = ""):
    """
    缓存装饰器

    Args:
        ttl: 缓存过期时间 (秒),默认 5 分钟
        key_prefix: 缓存键前缀

    Example:
        @cache(ttl=3600, key_prefix="model")
        def get_model_config(model_name: str):
            return load_model_config(model_name)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_client = get_cache()
            if not cache_client.enabled:
                return func(*args, **kwargs)

            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"

            # 尝试从缓存获取
            cached_value = cache_client.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value

            # 调用原函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache_client.set(cache_key, result, ttl=ttl)
            logger.debug(f"缓存存储: {cache_key}")

            return result

        return wrapper

    return decorator


# 使用示例
if __name__ == "__main__":
    # 初始化缓存
    cache_client = RedisCache("redis://localhost:6379/0")

    # 基本操作
    cache_client.set("user:123", {"name": "Alice", "age": 25}, ttl=300)
    user = cache_client.get("user:123")
    print(f"User: {user}")

    # 使用装饰器
    @cache(ttl=60, key_prefix="api")
    def fetch_data(url: str) -> dict:
        import requests

        response = requests.get(url)
        return response.json()

    # 第一次调用会请求 API
    data1 = fetch_data("https://api.example.com/data")

    # 第二次调用会从缓存读取
    data2 = fetch_data("https://api.example.com/data")

    # 查看统计
    stats = cache_client.get_stats()
    print(f"Cache stats: {stats}")
