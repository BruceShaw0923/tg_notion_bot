"""
URL 处理器模块

此模块包含处理 URL 相关消息的函数。
"""

from telegram import Update
from telegram.ext import CallbackContext
import logging
import os
from services.notion_service import add_to_notion, add_to_papers_database, is_pdf_url, download_pdf
from services.gemini_service import analyze_content, analyze_pdf_content
from services.url_service import extract_url_content

# 配置日志
logger = logging.getLogger(__name__)

def handle_url_message(update: Update, url, created_at):
    """处理纯 URL 消息
    
    Args:
        update: Telegram 更新对象
        url: 要处理的 URL
        created_at: 消息创建时间
    """
    # 首先检查是否是 PDF URL
    if is_pdf_url(url):
        update.message.reply_text("检测到 PDF 链接，正在下载并解析论文内容，请稍候...")
        handle_pdf_url(update, url, created_at)
        return
    
    update.message.reply_text("正在解析 URL 内容，请稍候...")
    
    try:
        # 提取网页内容
        content = extract_url_content(url)
        
        if not content:
            update.message.reply_text("⚠️ 无法提取 URL 内容")
            return
        
        # 分析内容
        analysis_result = analyze_content(content)
        
        # 存入 Notion
        page_id = add_to_notion(
            content=content,
            summary=analysis_result["summary"],
            tags=analysis_result["tags"],
            url=url,
            created_at=created_at
        )
        
        update.message.reply_text(f"✅ {url} 内容已成功解析并保存到 Notion！")
    
    except Exception as e:
        logger.error(f"处理 URL 时出错：{e}")
        update.message.reply_text(f"⚠️ 处理 {url} 时出错：{str(e)}")

def handle_multiple_urls_message(update: Update, content, urls, created_at):
    """处理包含多个 URL 的消息
    
    Args:
        update: Telegram 更新对象
        content: 消息内容
        urls: URL 列表
        created_at: 消息创建时间
    """
    update.message.reply_text(f"检测到 {len(urls)} 个链接，正在处理消息内容...")
    
    # 创建一个包含原始消息和 URL 标记的文本
    rich_content = content
    
    # 使用 Gemini 直接分析原始消息内容，不访问 URL
    analysis_result = analyze_content(rich_content)
    
    # 存入 Notion，将 URLs 作为参考信息
    try:
        # 主要 URL 使用第一个链接
        primary_url = urls[0] if urls else ""
        
        # 创建 URL 列表作为附加信息
        url_list_content = f"消息中包含的链接：\n"
        for i, url in enumerate(urls, 1):
            url_list_content += f"{i}. {url}\n"
        
        # 合并原始内容和 URL 列表
        combined_content = f"{rich_content}\n\n{url_list_content}"
        
        # 创建 Notion 页面
        page_id = add_to_notion(
            content=combined_content,
            summary=analysis_result["summary"],
            tags=analysis_result["tags"],
            url=primary_url,  # 主 URL 使用第一个
            created_at=created_at
        )
        
        # 返回成功消息
        update.message.reply_text(f"✅ 消息内容及 {len(urls)} 个链接的引用已保存到 Notion!")
    except Exception as e:
        logger.error(f"处理多 URL 消息时出错：{e}")
        update.message.reply_text(f"⚠️ 处理消息时出错：{str(e)}")

def handle_pdf_url(update: Update, url, created_at):
    """处理 PDF URL，下载并解析为论文
    
    Args:
        update: Telegram 更新对象
        url: PDF 的 URL
        created_at: 消息创建时间
    """
    try:
        # 从 URL 下载 PDF
        pdf_path, file_size = download_pdf(url)
        
        if not pdf_path:
            update.message.reply_text(f"⚠️ 无法下载 {url} 文件")
            return
        
        # 提取文件名
        import os
        from urllib.parse import urlparse
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
