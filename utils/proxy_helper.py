#!/usr/bin/env python3
"""
代理辅助工具

提供代理配置、检测和优化功能
"""

import logging
import os
from typing import Dict, Optional

import requests
import urllib3

# 禁用不安全请求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


def detect_best_proxy() -> Optional[str]:
    """
    检测并返回最合适的代理设置

    返回：
        str: 推荐的代理 URL，如果没有可用代理则返回 None
    """
    # 按优先级获取代理设置
    proxies = {
        "https_proxy": os.environ.get("https_proxy", ""),
        "http_proxy": os.environ.get("http_proxy", ""),
        "all_proxy": os.environ.get("all_proxy", ""),
    }

    # 测试 URL
    test_url = "https://api.telegram.org"

    # 首先测试 HTTP 代理
    for proxy_type in ["https_proxy", "http_proxy"]:
        if proxies[proxy_type]:
            try:
                # 临时设置代理环境变量
                old_https = os.environ.get("https_proxy")
                old_http = os.environ.get("http_proxy")
                old_all = os.environ.get("all_proxy")

                # 只设置当前测试的代理类型
                os.environ["https_proxy"] = (
                    proxies[proxy_type] if proxy_type == "https_proxy" else ""
                )
                os.environ["http_proxy"] = (
                    proxies[proxy_type] if proxy_type == "http_proxy" else ""
                )
                os.environ["all_proxy"] = ""

                # 测试连接
                response = requests.get(test_url, timeout=5, verify=False)

                # 恢复环境变量
                os.environ["https_proxy"] = old_https if old_https else ""
                os.environ["http_proxy"] = old_http if old_http else ""
                os.environ["all_proxy"] = old_all if old_all else ""

                if response.status_code == 200:
                    logger.info(f"{proxy_type} 测试成功：{proxies[proxy_type]}")
                    return proxies[proxy_type]
            except Exception:
                # 恢复环境变量
                try:
                    os.environ["https_proxy"] = old_https if old_https else ""
                    os.environ["http_proxy"] = old_http if old_http else ""
                    os.environ["all_proxy"] = old_all if old_all else ""
                except Exception:
                    pass

    # 如果 HTTP 代理都不工作，尝试 SOCKS 代理
    if proxies["all_proxy"] and "socks" in proxies["all_proxy"].lower():
        try:
            # 尝试使用 SOCKS 代理
            old_all = os.environ.get("all_proxy")
            old_https = os.environ.get("https_proxy")
            old_http = os.environ.get("http_proxy")

            os.environ["all_proxy"] = proxies["all_proxy"]
            os.environ["https_proxy"] = ""
            os.environ["http_proxy"] = ""

            response = requests.get(test_url, timeout=5, verify=False)

            # 恢复环境变量
            os.environ["all_proxy"] = old_all if old_all else ""
            os.environ["https_proxy"] = old_https if old_https else ""
            os.environ["http_proxy"] = old_http if old_http else ""

            if response.status_code == 200:
                logger.info(f"SOCKS 代理测试成功：{proxies['all_proxy']}")
                return proxies["all_proxy"]
        except Exception:
            # 恢复环境变量
            try:
                os.environ["all_proxy"] = old_all if old_all else ""
                os.environ["https_proxy"] = old_https if old_https else ""
                os.environ["http_proxy"] = old_http if old_http else ""
            except Exception:
                pass

    logger.warning("未找到有效的代理设置")
    return None


def configure_proxy_for_requests() -> Dict[str, str]:
    """
    为 requests 库配置最佳代理并返回代理字典

    返回：
        Dict[str, str]: 配置的代理字典
    """
    best_proxy = detect_best_proxy()
    proxies = {}

    if best_proxy:
        if "socks" in best_proxy.lower():
            # SOCKS 代理设置
            proxies = {"http": best_proxy, "https": best_proxy}
        else:
            # HTTP 代理设置
            proxies = {"http": best_proxy, "https": best_proxy}

    return proxies


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 测试代理检测
    print("检测最佳代理设置...")
    best_proxy = detect_best_proxy()
    if best_proxy:
        print(f"找到最佳代理：{best_proxy}")
    else:
        print("未找到有效的代理设置，将使用直接连接")
