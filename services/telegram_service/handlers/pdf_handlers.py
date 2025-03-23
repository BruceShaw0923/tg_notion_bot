from telegram import Update
from telegram.ext import CallbackContext
import logging
import os
import tempfile
from urllib.parse import urlparse
from services.gemini_service import analyze_pdf_content
from services.notion_service import add_to_papers_database, download_pdf
from ..utils import extract_metadata_from_filename

# 配置日志
logger = logging.getLogger(__name__)

def handle_pdf_document(update: Update, context: CallbackContext):
    """处理 PDF 文档，特别是学术论文"""
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

def handle_pdf_url(update: Update, url, created_at):
    """处理 PDF URL，下载并解析为论文"""
    try:
        # 从 URL 下载 PDF
        pdf_path, file_size = download_pdf(url)
        
        if not pdf_path:
            update.message.reply_text(f"⚠️ 无法下载 {url} 文件")
            return
        
        # 提取文件名
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path) or "document.pdf"
        
        # 使用 Gemini 分析 PDF 内容
        pdf_analysis = analyze_pdf_content(pdf_path)
        
        # 添加到论文数据库
        page_id = add_to_papers_database(
            title=filename,
            analysis=pdf_analysis,
            created_at=created_at,
            pdf_url=url  # 使用原始 URL，而不是本地路径
        )
        
        # 清理临时文件
        try:
            os.unlink(pdf_path)
        except:
            pass
        
        update.message.reply_text(f"✅ {url} 论文已成功解析并添加到 Notion 数据库！\n包含详细分析和原始 PDF 文件链接。")
    
    except Exception as e:
        logger.error(f"处理 PDF {url} 时出错：{e}")
        update.message.reply_text(f"⚠️ 处理 PDF {url} 时出错：{str(e)}")
        # 确保清理临时文件
        try:
            if 'pdf_path' in locals() and pdf_path and os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except:
            pass
