import logging
from telegram import Update
from telegram.ext import CallbackContext
from services.notion_service import add_to_notion
from services.gemini_service import analyze_content
import tempfile
import os
from utils.helpers import extract_links, download_pdf, extract_pdf_text
import time
from config import ENABLE_GEMINI

logger = logging.getLogger(__name__)

def handle_message(update: Update, context: CallbackContext):
    """处理用户发送的消息"""
    try:
        message = update.message
        chat_id = message.chat_id
        message_text = message.text or ""
        
        # 告知用户我们正在处理
        processing_msg = message.reply_text("正在处理您的消息，请稍候...")
        
        # 检查消息是否包含链接
        urls = extract_links(message_text)
        url = urls[0] if urls else ""
        
        # 分析内容获取摘要和标签
        analysis = analyze_content(message_text)
        summary = analysis.get("summary", "")
        tags = analysis.get("tags", [])
        
        # 将内容添加到 Notion
        page_id = add_to_notion(message_text, summary, tags, url)
        
        # 通知用户处理完成
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=processing_msg.message_id,
            text=f"✅ 消息已成功添加到 Notion！\n\n📝 摘要：{summary}\n\n🏷️ 标签：{', '.join(tags)}"
        )
        
    except Exception as e:
        logger.error(f"处理消息时出错：{e}")
        try:
            context.bot.edit_message_text(
                chat_id=processing_msg.chat_id,
                message_id=processing_msg.message_id,
                text=f"处理消息时出错：{str(e)}"
            )
        except:
            update.message.reply_text(f"处理消息时出错：{str(e)}")

def handle_document(update: Update, context: CallbackContext):
    """处理用户发送的文档（PDF 等）"""
    try:
        message = update.message
        chat_id = message.chat_id
        document = message.document
        
        # 检查文件是否为 PDF
        if not document.mime_type == "application/pdf":
            message.reply_text("目前只支持处理 PDF 文件。")
            return
            
        # 告知用户我们正在处理
        processing_msg = message.reply_text("正在处理您的 PDF 文件，可能需要一些时间...")
        
        # 下载文件
        file = context.bot.get_file(document.file_id)
        temp_path = os.path.join(tempfile.gettempdir(), f"{document.file_name}")
        file.download(temp_path)
        
        try:
            # 提取 PDF 文本
            pdf_text = extract_pdf_text(temp_path)
            
            if ENABLE_GEMINI:
                # 使用 Gemini 分析 PDF 内容
                from services.gemini_service import analyze_pdf_content
                analysis = analyze_pdf_content(pdf_text, document.file_name)
            else:
                # 基本分析
                analysis = analyze_content(pdf_text[:1000])  # 仅分析前 1000 个字符
                
            # 将内容添加到 Notion
            title = analysis.get("title", document.file_name)
            summary = analysis.get("summary", "")
            tags = analysis.get("tags", [])
            
            # 添加到 Notion
            page_id = add_to_notion(
                content=pdf_text[:15000],  # 限制内容长度
                summary=summary,
                tags=tags,
                url=""  # 本地文件没有 URL
            )
            
            # 通知用户处理完成
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text=f"✅ PDF 已成功添加到 Notion！\n\n📄 标题：{title}\n\n📝 摘要：{summary[:100]}...\n\n🏷️ 标签：{', '.join(tags)}"
            )
            
        finally:
            # 清理临时文件
            try:
                os.remove(temp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"处理 PDF 文件时出错：{e}")
        message.reply_text(f"处理 PDF 文件时出错：{str(e)}")
