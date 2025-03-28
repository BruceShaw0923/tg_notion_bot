"""
API 速率限制模块

提供 API 请求速率限制功能，确保不超过服务提供商设定的请求限制
"""

import logging
import threading
import time
from collections import deque
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    速率限制器类

    用于控制特定时间窗口内的请求数量，确保不超过 API 限制
    """

    def __init__(self, max_calls, time_frame):
        """
        初始化速率限制器

        参数：
            max_calls: 时间窗口内允许的最大请求数
            time_frame: 时间窗口大小 (秒)
        """
        self.max_calls = max_calls  # 最大请求数
        self.time_frame = time_frame  # 时间窗口 (秒)
        self.calls_timestamps = deque()  # 请求时间戳队列
        self.lock = threading.Lock()  # 线程锁

    def __call__(self, func):
        """
        装饰器方法，用于包装需要限流的函数
        """

        @wraps(func)
        def wrapped(*args, **kwargs):
            self.wait_if_limited()
            return func(*args, **kwargs)

        return wrapped

    def wait_if_limited(self):
        """
        检查是否达到速率限制，如果是则等待
        """
        with self.lock:
            # 当前时间
            now = time.time()

            # 移除时间窗口外的时间戳
            while (
                self.calls_timestamps
                and now - self.calls_timestamps[0] > self.time_frame
            ):
                self.calls_timestamps.popleft()

            # 检查是否达到限制
            if len(self.calls_timestamps) >= self.max_calls:
                # 计算需要等待的时间
                sleep_time = self.time_frame - (now - self.calls_timestamps[0])
                if sleep_time > 0:
                    logger.info(
                        f"达到 API 请求限制 ({self.max_calls}/{self.time_frame}秒)，等待 {sleep_time:.2f} 秒"
                    )
                    # 释放锁定，避免阻塞其他线程
                    self.lock.release()
                    time.sleep(sleep_time)
                    # 重新获取锁定
                    self.lock.acquire()
                    # 重新调用自身，确保限流正确
                    return self.wait_if_limited()

            # 添加当前请求的时间戳
            self.calls_timestamps.append(now)
            current_rpm = len(self.calls_timestamps) / (self.time_frame / 60)
            if current_rpm > self.max_calls * 0.8:  # 当使用超过 80% 容量时记录警告
                logger.warning(
                    f"API 请求频率较高：当前 {current_rpm:.1f} RPM，限制 {self.max_calls} RPM"
                )
            else:
                logger.debug(f"当前请求频率：{current_rpm:.1f} RPM")
