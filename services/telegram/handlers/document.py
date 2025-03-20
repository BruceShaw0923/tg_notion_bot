"""
文档处理器模块

此模块包含处理文档消息的函数，特别是 PDF 文件。
"""

from telegram import Update
from telegram.ext import CallbackContext
import logging
import os
import tempfile
from config import ALLOWED_USER_IDS
from services.gemini_service import analyze_pdf_content
from services.notion_service import add_to_papers_database
# 修复导入路径
from services.telegram.utils import extract_metadata_from_filename

# 配置日志
logger = logging.getLogger(__name__)

def process_document(update: Update, context: CallbackContext) -> None:
    """处理文档文件，特别是 PDF
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    message = update.message
    
    # 检查是否是 PDF 文件
    if message.document.file_name.lower().endswith('.pdf'):
        handle_pdf_document(update, context)
    else:
        # 对于非 PDF 文件，使用常规处理 - 修复导入路径
        from services.telegram.handlers.message import process_message
        process_message(update, context)

def handle_pdf_document(update: Update, context: CallbackContext):
    """处理 PDF 文档，特别是学术论文
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    update.message.reply_text("正在处理 PDF 文件，这可能需要几分钟...")
    
    message = update.message
    document = message.document
    created_at = message.date
    
    try:
        # 下载文件
        file = context.bot.get_file(document.file_id)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.download(custom_path=temp_file.name)
            pdf_path = temp_file.name
        
        # 使用 Gemini 分析 PDF 内容
        pdf_analysis = analyze_pdf_content(pdf_path)
        
        # 从文件名提取可能的元数据
        filename_metadata = extract_metadata_from_filename(document.file_name)
        
        # 添加到论文数据库
        page_id = add_to_papers_database(
            title=document.file_name,
            analysis=pdf_analysis,
            created_at=created_at,
            pdf_url=pdf_path,  # 临时文件路径
            metadata=filename_metadata  # 可能从文件名提取的元数据
        )
        
        update.message.reply_text(f"✅ PDF 论文已成功解析并添加到 Notion 数据库！\n包含详细分析和原始 PDF 文件。")
    
    except Exception as e:
        logger.error(f"处理 {document.file_id} 文件时出错：{e}")
        update.message.reply_text(f"⚠️ 处理 {document.file_id} 文件时出错：{str(e)}")
        # 确保清理任何临时文件
        try:
            if 'pdf_path' in locals():
                os.unlink(pdf_path)
        except:
            pass