#!/usr/bin/env python3
"""
保持网络连接活跃的脚本，防止在 Mac 待机时失去连接
"""

import logging
import os
import subprocess
import threading
import time
from datetime import datetime

import requests

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("logs/keep_alive.log"), logging.StreamHandler()],
)
logger = logging.getLogger("keep_alive")

# 保活设置
KEEP_ALIVE = os.environ.get("KEEP_ALIVE", "true").lower() == "true"
RETRY_INTERVAL = int(os.environ.get("RETRY_INTERVAL", "30"))
TELEGRAM_API = "https://api.telegram.org"
CHECK_INTERVAL = 60  # 每 60 秒检查一次


def ping_telegram():
    """尝试连接 Telegram API 以保持网络活跃"""
    try:
        response = requests.get(TELEGRAM_API, timeout=10)
        logger.debug(f"Telegram API 状态码：{response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"无法连接 Telegram API: {e}")
        return False


def check_bot_status():
    """检查机器人服务状态"""
    try:
        result = subprocess.run(
            ["ps", "-ef"], capture_output=True, text=True, check=True
        )
        return "python main.py" in result.stdout
    except Exception as e:
        logger.error(f"检查机器人状态失败：{e}")
        return False


def keep_connection_alive():
    """定期发送请求保持网络连接活跃"""
    while KEEP_ALIVE:
        now = datetime.now()
        logger.debug(f"保活检查 - {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 尝试连接 Telegram API
        if ping_telegram():
            logger.debug("连接正常")
        else:
            logger.warning("连接异常，尝试恢复...")
            # 这里可以添加恢复连接的逻辑

        # 检查机器人服务
        if not check_bot_status():
            logger.warning("机器人服务似乎没有运行，尝试恢复...")
            # 这里可以添加重启服务的逻辑

        # 等待下一次检查
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if KEEP_ALIVE:
        logger.info("启动网络连接保活服务")
        # 在单独的线程中运行保活程序
        keep_alive_thread = threading.Thread(target=keep_connection_alive)
        keep_alive_thread.daemon = True
        keep_alive_thread.start()

        # 主线程继续运行，防止程序退出
        try:
            while True:
                time.sleep(3600)  # 每小时记录一次状态
                logger.info("保活服务正在运行")
        except KeyboardInterrupt:
            logger.info("保活服务已停止")
    else:
        logger.info("保活功能已禁用")
