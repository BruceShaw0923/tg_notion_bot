"""
消息处理器模块

此模块包含处理基本消息的函数。
"""

from telegram import Update
from telegram.ext import CallbackContext
import logging
from config import ALLOWED_USER_IDS
from services.gemini_service import analyze_content
from services.notion_service import add_to_notion
# 修复导入路径
from services.telegram.handlers.url import handle_url_message, handle_multiple_urls_message
from services.telegram.handlers.todo import handle_todo_message
from utils.helpers import extract_all_urls_from_text, is_url_only

# 配置日志
logger = logging.getLogger(__name__)

def process_message(update: Update, context: CallbackContext) -> None:
    """处理收到的消息
    
    处理各种类型的消息，包括文本、图片或带有标签的消息。
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    message = update.message
    content = message.text or message.caption or ""
    created_at = message.date
    
    # 检查是否有 #todo 标签
    if "#todo" in content:
        handle_todo_message(update, content, created_at)
        return
    
    # 检查是否是纯 URL
    if is_url_only(content):
        handle_url_message(update, content, created_at)
        return
    
    # 检查是否有多个 URL，使用增强的 URL 提取
    urls = extract_all_urls_from_text(content)
    
    if len(urls) > 1:
        handle_multiple_urls_message(update, content, urls, created_at)
        return
    elif len(urls) == 1:
        url = urls[0]  # 仅有一个 URL 时保持原有逻辑
    else:
        url = ""  # 没有 URL
    
    # 短内容处理：如果内容不是纯 URL 且少于 200 字符，直接将内容作为摘要
    if len(content) < 200:
        # 仍需使用 Gemini API 分析提取标签
        analysis_result = analyze_content(content)
        
        # 存入 Notion，但使用原始内容作为摘要
        try:
            page_id = add_to_notion(
                content=content,
                summary=content,  # 直接使用原始内容作为摘要
                tags=analysis_result["tags"],
                url=url,
                created_at=created_at
            )
            update.message.reply_text(f"✅ 内容已成功保存到 Notion!")
        except Exception as e:
            logger.error(f"添加到 Notion 时出错：{e}")
            update.message.reply_text(f"⚠️ 保存到 Notion 时出错：{str(e)}")
        return
    
    # 长内容处理：使用 Gemini API 完整分析内容
    analysis_result = analyze_content(content)
    
    # 存入 Notion
    try:
        page_id = add_to_notion(
            content=content,
            summary=analysis_result["summary"],
            tags=analysis_result["tags"],
            url=url,
            created_at=created_at
        )
        update.message.reply_text(f"✅ 内容已成功保存到 Notion!")
    except Exception as e:
        logger.error(f"添加到 Notion 时出错：{e}")
        update.message.reply_text(f"⚠️ 保存到 Notion 时出错：{str(e)}")