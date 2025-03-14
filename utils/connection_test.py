#!/usr/bin/env python3
"""
连接测试工具

自动测试不同代理和 SSL 设置组合，找到最佳配置
"""

import os
import requests
import logging
import time
from typing import Dict, Tuple, List, Optional

logger = logging.getLogger(__name__)

def test_all_configurations() -> Dict:
    """
    测试所有可能的配置组合，找出最佳配置
    
    返回：
        Dict: 最佳配置参数
    """
    # 获取代理设置
    http_proxy = os.environ.get('http_proxy', '')
    https_proxy = os.environ.get('https_proxy', '')
    socks_proxy = os.environ.get('all_proxy', '')
    
    # 测试配置矩阵
    configs = []
    
    # 1. HTTP 代理 + SSL 验证
    if https_proxy:
        configs.append({
            'name': 'HTTPS 代理 + SSL 验证',
            'proxy': https_proxy,
            'verify_ssl': True
        })
    
    # 2. HTTP 代理 + 禁用 SSL
    if https_proxy:
        configs.append({
            'name': 'HTTPS 代理 + 禁用 SSL',
            'proxy': https_proxy,
            'verify_ssl': False
        })
    
    # 3. SOCKS 代理 + SSL 验证
    if socks_proxy and 'socks' in socks_proxy.lower():
        configs.append({
            'name': 'SOCKS 代理 + SSL 验证',
            'proxy': socks_proxy,
            'verify_ssl': True
        })
    
    # 4. SOCKS 代理 + 禁用 SSL
    if socks_proxy and 'socks' in socks_proxy.lower():
        configs.append({
            'name': 'SOCKS 代理 + 禁用 SSL',
            'proxy': socks_proxy,
            'verify_ssl': False
        })
    
    # 5. 直接连接 + SSL 验证
    configs.append({
        'name': '直接连接 + SSL 验证',
        'proxy': None,
        'verify_ssl': True
    })
    
    # 测试配置
    results = []
    for config in configs:
        success, time_cost = test_configuration(config)
        if success:
            results.append((config, time_cost))
    
    # 选择最快的成功配置
    if results:
        best_config = min(results, key=lambda x: x[1])[0]
        logger.info(f"最佳配置：{best_config['name']}, 耗时：{min(results, key=lambda x: x[1])[1]:.2f}秒")
        
        # 构建请求参数
        request_kwargs = {}
        if best_config['proxy']:
            request_kwargs['proxy_url'] = best_config['proxy']
            request_kwargs['urllib3_proxy_kwargs'] = {
                'timeout': 30
            }
            if not best_config['verify_ssl']:
                request_kwargs['urllib3_proxy_kwargs']['cert_reqs'] = 'CERT_NONE'
                logger.warning("⚠️ 安全警告：检测到最佳配置需要禁用 SSL 验证。这降低了连接的安全性。")
                logger.warning("建议：考虑更新您的代理配置或系统证书库。")
        
        return request_kwargs
    
    # 所有配置都失败，返回默认配置
    logger.warning("所有配置测试均失败，使用默认 HTTPS 代理配置")
    return {'proxy_url': https_proxy or http_proxy or socks_proxy}

def test_configuration(config: Dict) -> Tuple[bool, float]:
    """
    测试特定配置
    
    参数：
        config: 配置字典
        
    返回：
        Tuple[bool, float]: 是否成功和耗时
    """
    logger.info(f"测试配置：{config['name']}")
    start_time = time.time()
    
    try:
        # 设置代理
        proxies = {}
        if config['proxy']:
            if 'socks' in config['proxy'].lower():
                proxies = {
                    'http': config['proxy'],
                    'https': config['proxy']
                }
            else:
                proxies = {
                    'http': config['proxy'],
                    'https': config['proxy']
                }
        
        # 发送请求
        response = requests.get(
            "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/getMe",
            proxies=proxies,
            verify=config['verify_ssl'],
            timeout=10
        )
        
        # 计算耗时
        elapsed = time.time() - start_time
        logger.info(f"配置成功！状态码：{response.status_code}, 耗时：{elapsed:.2f}秒")
        return True, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(f"配置失败：{str(e)}, 耗时：{elapsed:.2f}秒")
        return False, float('inf')

# 测试运行
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    best_config = test_all_configurations()
    print(f"推荐配置：{best_config}")
