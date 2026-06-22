"""
请求频率限制中间件模块
=========================
基于 Redis 有序集合（Sorted Set）实现滑动窗口限流器。
用于防止 API 接口被恶意高频调用，保护服务器资源。

主要功能：
- 基于客户端 IP 和请求路径分别限流
- 使用滑动窗口算法，精准控制时间窗口内的请求次数
- Redis 不可用时自动降级（跳过限流），保证服务可用性
- 支持自定义限制阈值和时间窗口
"""
import time
import redis
from flask import request, jsonify
from functools import wraps
from app.config.settings import settings


class RateLimiter:
    """
    基于 Redis 的滑动窗口限流器
    ------------------------------

    使用 Redis 有序集合（ZSET）实现滑动窗口：
    - member = 请求时间戳（字符串）
    - score = 请求时间戳（数值）
    - 自动移除窗口外的过期记录

    属性:
        limit (int): 时间窗口内允许的最大请求数
        window (int): 时间窗口大小（秒），默认 60 秒
    """

    def __init__(self, redis_client=None, limit=None, window=60):
        """
        初始化限流器

        参数:
            redis_client: Redis 客户端实例（可选，不传则自动连接）
            limit: 窗口内最大请求数（默认从 settings.RATE_LIMIT 读取）
            window: 时间窗口大小，单位秒，默认 60
        """
        self.limit = limit or settings.RATE_LIMIT
        self.window = window
        self._redis = redis_client
        self._redis_available = None  # None=未检测, True=可用, False=不可用

    @property
    def redis(self):
        """
        Redis 客户端延迟连接属性
        ---------------------------
        首次访问时连接 Redis，并检测连接状态。
        连接失败后将 _redis_available 标记为 False，后续不再重试。

        返回:
            Redis 客户端实例（可用时）或 None（不可用时）
        """
        if self._redis is None:
            try:
                # 从配置 URL 创建 Redis 连接
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                # 检测连接是否正常
                self._redis.ping()
                self._redis_available = True
            except (redis.ConnectionError, redis.TimeoutError):
                # Redis 连接失败，标记为不可用
                self._redis_available = False
        return self._redis if self._redis_available else None

    def limit_decorator(self, f):
        """
        限流装饰器
        -----------
        对被装饰的视图函数应用滑动窗口限流。
        使用客户端 IP + 请求路径作为限流 key，确保不同用户和接口独立计数。

        用法:
            @rate_limiter.limit_decorator
            @app.route('/api/chat', methods=['POST'])
            def chat():
                ...

        参数:
            f: 被装饰的视图函数

        返回:
            装饰后的函数
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            # 如果 Redis 不可用，跳过限流直接执行原函数
            if not self.redis:
                return f(*args, **kwargs)

            # 构造限流 key: rate_limit:{客户端IP}:{请求路径}
            client_ip = request.remote_addr or "127.0.0.1"
            key = f"rate_limit:{client_ip}:{request.path}"
            now = int(time.time())

            # 步骤1: 移除超出滑动窗口的旧记录（score <= 当前时间 - 窗口大小）
            self.redis.zremrangebyscore(key, 0, now - self.window)

            # 步骤2: 统计当前窗口内的请求数量
            count = self.redis.zcard(key)

            # 步骤3: 如果请求数已达上限，返回 429 拒绝请求
            if count >= self.limit:
                return jsonify({
                    "code": 429,
                    "message": "请求过于频繁，请稍后重试",
                    "data": None
                }), 429

            # 步骤4: 记录本次请求到有序集合中
            self.redis.zadd(key, {str(now): now})
            # 设置 key 的过期时间，自动清理不再使用的 key
            self.redis.expire(key, self.window)

            # 步骤5: 执行被装饰的视图函数
            return f(*args, **kwargs)
        return decorated
