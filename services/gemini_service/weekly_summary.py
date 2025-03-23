"""
周报生成模块

提供基于 Gemini 的周报内容生成和分析功能
"""

import json
import logging

from config.prompts import WEEKLY_SUMMARY_PROMPT

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
        # 提取条目中的关键信息
        entries_data = []
        for entry in entries:
            # 跳过周报本身
            if "Tags" in entry["properties"] and any(
                tag.get("name") == "周报"
                for tag in entry["properties"]["Tags"].get("multi_select", [])
            ):
                continue

            entry_data = {
                "id": entry["id"],
                "title": extract_property_text(entry, "Name", "title"),
                "summary": extract_property_text(entry, "Summary", "rich_text"),
                "tags": extract_multi_select(entry, "Tags"),
                "created": extract_date(entry, "Created"),
                "url": extract_url(entry, "URL"),
                # 添加原始内容的前 300 个字符，帮助 AI 理解内容
                "content_preview": get_content_preview(entry["id"]),
            }
            entries_data.append(entry_data)

        # 无内容时返回提示
        if not entries_data:
            return "本周没有添加任何内容。"

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

            return response.text
        else:
            return "无法生成周报总结，请稍后再试。"

    except Exception as e:
        logger.error(f"生成周报总结时出错：{e}")
        return f"生成周报时遇到错误：{str(e)}"


def get_content_preview(page_id, max_length=300):
    """
    获取页面内容的预览

    参数：
    page_id (str): Notion 页面 ID
    max_length (int): 预览最大长度

    返回：
    str: 页面内容预览
    """
    try:
        from services.notion_service import extract_notion_block_content, notion

        # 获取页面内容块
        blocks = notion.blocks.children.list(block_id=page_id).get("results", [])

        # 提取文本内容
        content = extract_notion_block_content(blocks)

        # 限制长度
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content
    except Exception as e:
        logger.warning(f"获取页面内容预览时出错：{e}")
        return ""
