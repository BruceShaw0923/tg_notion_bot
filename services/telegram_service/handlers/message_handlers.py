from telegram import Update
from telegram.ext import CallbackContext
import logging
from config import ALLOWED_USER_IDS

from utils.helpers import is_url_only, extract_all_urls_from_text
from services.gemini_service import analyze_content

# 导入处理器
from .url_handlers import handle_url_message, handle_multiple_urls_message
from .todo_handlers import handle_todo_message
from .pdf_handlers import handle_pdf_document

# 配置日志
logger = logging.getLogger(__name__)

def process_message(update: Update, context: CallbackContext) -> None:
    """处理收到的消息"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    message = update.message
    
    # 检查消息是否包含图片
    contains_photo = message.photo and len(message.photo) > 0
    
    # 获取文本内容，如果是图片消息则获取其标题文字 (caption)
    content = message.text or message.caption or ""
    created_at = message.date
    
    # 如果消息包含图片
    if contains_photo:
        logger.info(f"接收到包含图片的消息，用户 ID: {update.effective_user.id}，将只处理文字部分")
        
        # 如果图片消息没有文字说明
        if not content:
            update.message.reply_text(
                "⚠️ 收到图片但没有文字说明。请添加说明后重新发送，或者单独发送要保存的文字内容。"
            )
            return
        
        # 给原始内容添加前缀，表明它来自包含图片的消息
        content = f"[此内容来自包含图片的消息] {content}"
        logger.info(f"处理图片消息的文字内容，长度：{len(content)} 字符")
    
    # 检查是否有 #todo 标签
    if "#todo" in content:
        handle_todo_message(update, content, created_at)
        return
    
    # 检查是否是纯 URL (包括括号内 URL 格式)
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
        # 通知用户正在处理消息
        processing_msg = "正在处理消息..." if not contains_photo else "正在处理图片消息的文字内容..."
        update.message.reply_text(processing_msg)
        
        # 仍需使用 Gemini API 分析提取标签
        analysis_result = analyze_content(content)
        
        # 存入 Notion，但使用原始内容作为摘要
        try:
            from services.notion_service import add_to_notion
            # 注意：此处传递的 content 只包含文本，不包含任何图片数据
            page_id = add_to_notion(
                content=content,  # 只传递文本内容
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
    
    # 长内容处理：通知用户正在处理
    processing_msg = "正在处理较长消息，这可能需要一点时间..." if not contains_photo else "正在处理图片消息中的较长文字内容，这可能需要一点时间..."
    update.message.reply_text(processing_msg)
    
    # 使用 Gemini API 完整分析内容
    analysis_result = analyze_content(content)
    
    # 存入 Notion
    try:
        from services.notion_service import add_to_notion
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

def process_document(update: Update, context: CallbackContext) -> None:
    """处理文档文件，特别是 PDF"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    message = update.message
    
    # 检查是否是 PDF 文件
    if message.document.file_name.lower().endswith('.pdf'):
        handle_pdf_document(update, context)
    else:
        # 对于非 PDF 文件，使用常规处理
        process_message(update, context)
