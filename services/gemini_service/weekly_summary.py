"""
周报生成模块

提供基于 Gemini 的周报内容生成和分析功能
"""

import hashlib
import json
import logging
from datetime import datetime

from config.prompts import WEEKLY_SUMMARY_PROMPT
from utils.gemini_cache import get_from_cache, save_to_cache

from .client import model
from .utils import (
    extract_date,
    extract_multi_select,
    extract_property_text,
    extract_url,
)

logger = logging.getLogger(__name__)


def generate_weekly_summary(entries):
    """
    使用 Gemini 生成周报总结，并为内容添加引用标记

    参数：
    entries (list): Notion 页面条目列表

    返回：
    str: 生成的周报总结，包含 Notion 内链引用
    """
    try:
        # 无内容时返回提示
        if not entries:
            return "本周没有添加任何内容。"

        # 提取条目中的关键信息
        entries_data = []
        entry_ids = []

        for entry in entries:
            # 跳过周报本身
            if "Tags" in entry["properties"] and any(
                tag.get("name") == "周报"
                for tag in entry["properties"]["Tags"].get("multi_select", [])
            ):
                continue

            # 收集所有条目 ID 用于缓存键
            entry_ids.append(entry["id"])

            entry_data = {
                "id": entry["id"],
                "title": extract_property_text(entry, "Name", "title"),
                "summary": extract_property_text(entry, "Summary", "rich_text"),
                "tags": extract_multi_select(entry, "Tags"),
                "created": extract_date(entry, "Created"),
                "url": extract_url(entry, "URL"),
            }

            # 智能预览：仅为没有充分摘要的条目获取内容预览
            if not entry_data["summary"] or len(entry_data["summary"]) < 30:
                entry_data["content_preview"] = get_content_preview(entry["id"])
            else:
                # 使用已有摘要，避免额外调用
                entry_data["content_preview"] = entry_data["summary"][:300]

            entries_data.append(entry_data)

        # 无内容时返回提示
        if not entries_data:
            return "本周没有添加任何内容。"

        # 检查是否有上周生成的相同内容的周报缓存
        # 创建一个基于条目 ID 和日期的哈希键
        current_week = datetime.now().strftime("%Y-W%W")
        entries_hash = hashlib.md5(
            (",".join(sorted(entry_ids)) + current_week).encode()
        ).hexdigest()

        cached_summary = get_from_cache(
            entries_hash, "weekly_summary", ttl=7 * 24 * 60 * 60
        )  # 一周缓存
        if cached_summary:
            logger.info("使用缓存的周报总结")
            return cached_summary

        # 将条目转换为 JSON 格式
        entries_json = json.dumps(entries_data, ensure_ascii=False, indent=2)

        # 使用 Gemini 模型生成分析
        prompt = WEEKLY_SUMMARY_PROMPT.format(entries_json=entries_json)

        # 记录生成请求
        logger.info(f"发送周报总结生成请求，包含 {len(entries_data)} 个条目")

        response = model.generate_content(prompt)

        if response.text:
            # 检查生成的内容是否包含引用标记
            if "[" in response.text and "ref:" in response.text:
                logger.info("周报生成成功，包含引用标记")
            else:
                logger.warning("周报生成成功，但未包含引用标记")

            # 缓存生成的周报
            save_to_cache(entries_hash, response.text, "weekly_summary")
            return response.text
        else:
            return "无法生成周报总结，请稍后再试。"

    except Exception as e:
        logger.error(f"生成周报总结时出错：{e}")
        return f"生成周报时遇到错误：{str(e)}"


def get_content_preview(page_id, max_length=300):
    """
    获取页面内容的预览，带缓存功能

    参数：
    page_id (str): Notion 页面 ID
    max_length (int): 预览最大长度

    返回：
    str: 页面内容预览
    """
    # 检查缓存
    cached_preview = get_from_cache(
        page_id, "content_preview", ttl=3 * 24 * 60 * 60
    )  # 3 天缓存
    if cached_preview:
        logger.debug(f"使用缓存的内容预览：{page_id[:8]}...")
        return cached_preview

    try:
        from services.notion_service import extract_notion_block_content, notion

        # 获取页面内容块
        blocks = notion.blocks.children.list(block_id=page_id).get("results", [])

        # 提取文本内容
        content = extract_notion_block_content(blocks)

        # 限制长度
        if len(content) > max_length:
            preview = content[:max_length] + "..."
        else:
            preview = content

        # 缓存预览
        if preview:
            save_to_cache(page_id, preview, "content_preview")

        return preview
    except Exception as e:
        logger.warning(f"获取页面内容预览时出错：{e}")
        return ""
