#!/usr/bin/env python3
"""
智能代理配置助手

自动检测并使用最佳代理设置，同时保持安全性
"""

import logging
import os
import socket
import ssl
import time
from typing import Dict

import requests
import urllib3

logger = logging.getLogger(__name__)

# 禁用不安全请求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def configure_proxy_for_telegram() -> Dict:
    """
    为 Telegram 配置最佳代理设置

    返回：
        Dict: Request 的请求参数字典
    """
    # 设置基础请求参数 - 移除不兼容的 connect_retries 参数
    request_kwargs = {
        "connect_timeout": 30.0,
        "read_timeout": 60.0,  # 增加读取超时时间
        "con_pool_size": 10,
    }

    # 获取代理环境变量
    proxies = {
        "https_proxy": os.environ.get("https_proxy", ""),
        "http_proxy": os.environ.get("http_proxy", ""),
        "all_proxy": os.environ.get("all_proxy", ""),
    }

    # 检测禁用 SSL 验证的环境变量
    disable_ssl_verify = os.environ.get(
        "DISABLE_TELEGRAM_SSL_VERIFY", "False"
    ).lower() in ("true", "1", "t", "yes")

    # 优先使用 HTTPS 代理
    proxy_url = proxies["https_proxy"]

    # 没有 HTTPS 代理时使用 HTTP 代理
    if not proxy_url:
        proxy_url = proxies["http_proxy"]

    # 没有 HTTP 代理时才使用 SOCKS 代理
    if not proxy_url:
        proxy_url = proxies["all_proxy"]

    if proxy_url and proxy_url.strip():
        logger.info(f"使用代理：{proxy_url}")
        request_kwargs["proxy_url"] = proxy_url

        # 为代理设置超时参数
        urllib3_kwargs = {
            "timeout": 30,
        }

        # 如果需要禁用 SSL 验证
        if disable_ssl_verify:
            logger.warning("⚠️ SSL 证书验证已禁用。这可能存在安全风险。")
            urllib3_kwargs["cert_reqs"] = "CERT_NONE"

        request_kwargs["urllib3_proxy_kwargs"] = urllib3_kwargs
    else:
        logger.info("未使用代理")

        # 即使不用代理，也可能需要禁用 SSL 验证
        if disable_ssl_verify:
            logger.warning("⚠️ SSL 证书验证已禁用。这可能存在安全风险。")
            # 在不使用代理时，我们需要以其他方式禁用 SSL 验证
            # 这里采用全局方式，但仅用于 Telegram 接口
            create_default_context = ssl._create_default_https_context  # noqa: F841
            ssl._create_default_https_context = ssl._create_unverified_context

    # 移除不兼容的错误处理时钟函数
    # request_kwargs['error_handling_backoff'] = linear_backoff_clock

    return request_kwargs


def linear_backoff_clock(total_retry_count: int) -> float:
    """
    线性回退时钟，避免过快重试

    参数：
        total_retry_count: 已重试次数

    返回：
        float: 等待时间 (秒)
    """
    return min(1 + total_retry_count, 10)


def test_connectivity(timeout: int = 5, use_proxy: bool = True) -> bool:
    """
    测试 Telegram API 的连接性

    参数：
        timeout: 连接超时时间
        use_proxy: 是否使用代理

    返回：
        bool: 连接是否成功
    """
    proxy = None
    if use_proxy:
        http_proxy = os.environ.get("http_proxy")
        https_proxy = os.environ.get("https_proxy")
        all_proxy = os.environ.get("all_proxy")

        # 优先使用 HTTPS 代理
        proxy = https_proxy or http_proxy or all_proxy

    # 检测是否禁用 SSL 验证
    disable_ssl_verify = os.environ.get(
        "DISABLE_TELEGRAM_SSL_VERIFY", "False"
    ).lower() in ("true", "1", "t", "yes")

    # 尝试几个不同的 URL 和配置组合
    test_urls = [
        "https://api.telegram.org/",
        "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/getMe",
    ]

    for url in test_urls:
        try:
            proxies = {}
            if proxy:
                proxies = {"http": proxy, "https": proxy}

            response = requests.get(
                url,
                proxies=proxies if proxy else None,
                timeout=timeout,
                verify=not disable_ssl_verify,
            )

            if response.status_code != 404:  # 任何响应（即使是错误）也表示连接成功
                logger.info(f"连接测试成功：{url}, 状态码：{response.status_code}")
                return True

        except requests.RequestException as e:
            logger.warning(f"连接测试失败 ({url}): {e}")
            continue

    logger.error("所有连接测试均失败")
    return False


def check_network_conditions() -> Dict:
    """
    检查网络状况，分析延迟和可靠性

    返回：
        Dict: 包含网络状况分析的字典
    """
    results = {
        "status": "unknown",
        "latency_ms": 0,
        "reliability": 0,
        "recommendation": "",
    }

    # 测试延迟
    hosts = ["api.telegram.org"]
    latencies = []

    for host in hosts:
        try:
            start = time.time()
            socket.getaddrinfo(host, 443)
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
        except socket.gaierror:
            continue

    if not latencies:
        results["status"] = "unreachable"
        results["recommendation"] = "网络连接不可用，请检查网络或代理设置"
        return results

    # 计算平均延迟
    avg_latency = sum(latencies) / len(latencies)
    results["latency_ms"] = round(avg_latency, 2)

    # 根据延迟评估网络质量
    if avg_latency < 100:
        results["status"] = "excellent"
        results["reliability"] = 0.95
        results["recommendation"] = "网络状况良好，使用默认设置"
    elif avg_latency < 300:
        results["status"] = "good"
        results["reliability"] = 0.8
        results["recommendation"] = "网络状况正常，建议增加超时参数"
    elif avg_latency < 800:
        results["status"] = "fair"
        results["reliability"] = 0.6
        results["recommendation"] = "网络延迟较高，建议增加超时和重试参数"
    else:
        results["status"] = "poor"
        results["reliability"] = 0.3
        results["recommendation"] = "网络状况较差，建议使用稳定的代理并配置长超时"

    return results
