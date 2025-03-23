#!/usr/bin/env python3
"""
Telegram 辅助工具

提供 Telegram 相关的辅助函数，包括参数验证、错误处理等
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Telegram Request 类接受的参数列表
VALID_REQUEST_ARGS = {
    "con_pool_size",
    "connect_timeout",
    "read_timeout",
    "proxy_url",
    "urllib3_proxy_kwargs",
    "raise_keyboard_interrupt",
}


def validate_request_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并过滤 Telegram Request 的请求参数

    参数：
        kwargs: 原始请求参数

    返回：
        Dict: 过滤后的有效请求参数
    """
    valid_kwargs = {}

    for key, value in kwargs.items():
        if key in VALID_REQUEST_ARGS:
            valid_kwargs[key] = value
        else:
            logger.warning(f"移除不兼容的请求参数：{key}")

    return valid_kwargs


def monitor_telegram_webhook(bot):
    """
    检查并记录 webhook 设置

    参数：
        bot: Telegram Bot 对象

    返回：
        bool: Webhook 是否被设置
    """
    try:
        webhook_info = bot.get_webhook_info()
        if webhook_info.url:
            logger.warning(f"警告：发现 webhook 设置！URL: {webhook_info.url}")
            logger.warning(
                "轮询模式可能会与 webhook 冲突。如果使用轮询，请确保取消 webhook 设置。"
            )
            return True
        return False
    except Exception as e:
        logger.error(f"无法获取 webhook 信息：{e}")
        return False


def clear_webhook(bot):
    """
    清除可能存在的 webhook 设置

    参数：
        bot: Telegram Bot 对象

    返回：
        bool: 操作是否成功
    """
    try:
        bot.delete_webhook()
        logger.info("成功清除了 webhook 设置")
        return True
    except Exception as e:
        logger.error(f"清除 webhook 时出错：{e}")
        return False
