import time
import redis
from flask import request, jsonify
from functools import wraps
from app.config.settings import settings


class RateLimiter:
    """基于 Redis 的滑动窗口限流器"""

    def __init__(self, redis_client=None, limit=None, window=60):
        self.limit = limit or settings.RATE_LIMIT
        self.window = window
        self._redis = redis_client
        self._redis_available = None

    @property
    def redis(self):
        """延迟连接 Redis"""
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self._redis.ping()
                self._redis_available = True
            except (redis.ConnectionError, redis.TimeoutError):
                self._redis_available = False
        return self._redis if self._redis_available else None

    def limit_decorator(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not self.redis:
                # Redis 不可用时跳过限流
                return f(*args, **kwargs)

            client_ip = request.remote_addr or "127.0.0.1"
            key = f"rate_limit:{client_ip}:{request.path}"
            now = int(time.time())

            # 移除窗口外的记录
            self.redis.zremrangebyscore(key, 0, now - self.window)

            # 当前请求数
            count = self.redis.zcard(key)

            if count >= self.limit:
                return jsonify({
                    "code": 429,
                    "message": "请求过于频繁，请稍后重试",
                    "data": None
                }), 429

            # 记录本次请求
            self.redis.zadd(key, {str(now): now})
            self.redis.expire(key, self.window)

            return f(*args, **kwargs)
        return decorated
