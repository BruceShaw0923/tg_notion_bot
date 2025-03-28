"""
Gemini API 结果缓存模块

提供缓存机制，减少重复 API 调用
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path("./cache/gemini")
# 缓存有效期（默认 24 小时）
DEFAULT_CACHE_TTL = 24 * 60 * 60  # 秒


def get_content_hash(content):
    """
    计算内容的哈希值，用于缓存标识

    参数：
        content: 要计算哈希的内容

    返回：
        str: 内容的哈希值
    """
    if isinstance(content, str):
        content_str = content
    else:
        # 尝试转换为 JSON 字符串
        try:
            content_str = json.dumps(content, sort_keys=True)
        except Exception:
            content_str = str(content)

    # 计算 MD5 哈希值
    return hashlib.md5(content_str.encode("utf-8")).hexdigest()


def get_from_cache(content_key, prompt_key=None, ttl=DEFAULT_CACHE_TTL):
    """
    从缓存中获取结果

    参数：
        content_key: 内容键（哈希值或唯一标识符）
        prompt_key: 提示模板键（可选）
        ttl: 缓存有效期（秒）

    返回：
        dict/None: 缓存的结果或 None（如果缓存不存在或已过期）
    """
    # 确保缓存目录存在
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 构建缓存文件路径
    cache_key = f"{content_key}"
    if prompt_key:
        cache_key = f"{prompt_key}_{content_key}"

    cache_file = CACHE_DIR / f"{cache_key}.json"

    # 检查缓存是否存在
    if not cache_file.exists():
        return None

    try:
        # 读取缓存
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        # 检查缓存是否过期
        if time.time() - cache_data.get("timestamp", 0) > ttl:
            logger.debug(f"缓存已过期：{cache_key}")
            return None

        logger.info(f"从缓存获取结果：{cache_key}")
        return cache_data.get("result")

    except Exception as e:
        logger.warning(f"读取缓存失败：{e}")
        return None


def save_to_cache(content_key, result, prompt_key=None):
    """
    保存结果到缓存

    参数：
        content_key: 内容键（哈希值或唯一标识符）
        result: 要缓存的结果
        prompt_key: 提示模板键（可选）
    """
    # 确保缓存目录存在
    os.makedirs(CACHE_DIR, exist_ok=True)

    # 构建缓存文件路径
    cache_key = f"{content_key}"
    if prompt_key:
        cache_key = f"{prompt_key}_{content_key}"

    cache_file = CACHE_DIR / f"{cache_key}.json"

    try:
        # 保存缓存
        cache_data = {"timestamp": time.time(), "result": result}

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        logger.debug(f"结果已缓存：{cache_key}")

    except Exception as e:
        logger.warning(f"保存缓存失败：{e}")
