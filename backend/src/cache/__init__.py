"""Redis 缓存模块

提供统一的缓存接口,支持:
- 模型配置缓存
- 用户会话缓存
- 技能列表缓存
- 查询结果缓存
"""

from .redis_cache import RedisCache, get_cache

__all__ = ["RedisCache", "get_cache"]
