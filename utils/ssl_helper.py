#!/usr/bin/env python3
"""
SSL 辅助工具

用于管理 SSL 证书验证和设置
"""

import logging
import os
import sys
import warnings
from typing import Optional

import urllib3

logger = logging.getLogger(__name__)


def configure_ssl_verification(disable_ssl: Optional[bool] = None) -> bool:
    """
    全局配置 SSL 证书验证

    参数：
        disable_ssl: 是否禁用 SSL 验证，如果为 None，则从环境变量读取

    返回：
        bool: SSL 验证是否被禁用
    """
    # 确定是否禁用 SSL 验证
    if disable_ssl is None:
        disable_ssl = os.environ.get(
            "DISABLE_TELEGRAM_SSL_VERIFY", "False"
        ).lower() in ("true", "1", "t", "yes")

    if disable_ssl:
        # 禁用所有 urllib3 警告
        urllib3.disable_warnings()
        # 特别禁用不安全请求的警告
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # 禁用 Python HTTPS 验证
        os.environ["PYTHONHTTPSVERIFY"] = "0"

        # 使用 warnings 过滤器禁用警告
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
        warnings.filterwarnings(
            "ignore", category=urllib3.exceptions.InsecureRequestWarning
        )

        # 使用 requests 库内置的禁用警告机制
        try:
            import requests

            requests.packages.urllib3.disable_warnings()
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )
        except (ImportError, AttributeError):
            pass

        # 使用 Python 模块 - 级别禁用警告
        if not sys.warnoptions:
            # 删除这里的 import warnings，使用全局导入的 warnings 模块
            warnings.simplefilter("ignore")

        # 添加警告信息，标记为临时解决方案
        logger.warning(
            "⚠️ SSL 证书验证已禁用。这是临时解决方案，请考虑以下安全替代方案："
        )
        logger.warning("1. 更新系统证书库")
        logger.warning("2. 检查代理配置是否正确")
        logger.warning("3. 如使用自建代理，确保配置正确的 SSL 传递")

        logger.warning(
            "⚠️ SSL 证书验证已完全禁用。这可能存在安全风险，仅建议在特殊网络环境或开发环境中使用。"
        )
        return True
    else:
        # 确保环境变量设置正确
        os.environ["PYTHONHTTPSVERIFY"] = "1"
        return False


# 启动时自动调用
is_disabled = configure_ssl_verification()
