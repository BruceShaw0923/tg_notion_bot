from telegram import Update
import logging
import re
from services.url_service import extract_url_content
from services.gemini_service import analyze_content
from services.notion_service import add_to_notion
from .pdf_handlers import handle_pdf_url
from services.notion_service import is_pdf_url
from utils.helpers import extract_all_urls_from_text

# 配置日志
logger = logging.getLogger(__name__)

def extract_url_from_text(text):
    """
    从文本中提取 URL，支持括号内的 URL 格式和 Telegram 格式化链接
    
    参数：
    text (str): 可能包含 URL 的文本
    
    返回：
    str: 提取的 URL，如果没有找到则返回原始文本
    """
    # 检查是否为括号内 URL 格式
    bracketed_url_match = re.search(r'\((https?://[^\s\)]+)\)', text)
    if bracketed_url_match:
        return bracketed_url_match.group(1)
    
    # 检查是否为 Telegram/Markdown 格式化链接 [文本](URL)
    formatted_link_match = re.search(r'\[.+?\]\((https?://[^\s\)]+)\)', text)
    if formatted_link_match:
        return formatted_link_match.group(1)
    
    # 尝试使用标准 URL 模式直接匹配
    standard_url_match = re.search(r'(https?://[^\s]+)', text)
    if standard_url_match:
        # 清理 URL 末尾可能的标点符号
        url = standard_url_match.group(1)
        while url and url[-1] in '.,;:?!':
            url = url[:-1]
        return url
    
    # 返回原始文本（假设它已经是 URL 或将由其他函数处理）
    return text

def handle_url_message(update: Update, url, created_at):
    """处理纯 URL 消息"""
    # 提取可能在括号内的 URL 或 Telegram 格式化链接
    url = extract_url_from_text(url)
    
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
    """处理包含多个 URL 的消息"""
    # 处理可能在括号内的 URLs
    processed_urls = [extract_url_from_text(url) for url in urls]
    
    update.message.reply_text(f"检测到 {len(processed_urls)} 个链接，正在处理消息内容...")
    
    # 创建一个包含原始消息和 URL 标记的文本
    rich_content = content
    
    # 使用 Gemini 直接分析原始消息内容，不访问 URL
    analysis_result = analyze_content(rich_content)
    
    # 存入 Notion，将 URLs 作为参考信息
    try:
        # 主要 URL 使用第一个链接
        primary_url = processed_urls[0] if processed_urls else ""
        
        # 创建 URL 列表作为附加信息
        url_list_content = f"消息中包含的链接：\n"
        for i, url in enumerate(processed_urls, 1):
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
        update.message.reply_text(f"✅ 消息内容及 {len(processed_urls)} 个链接的引用已保存到 Notion!")
    except Exception as e:
        logger.error(f"处理多 URL 消息时出错：{e}")
        update.message.reply_text(f"⚠️ 处理消息时出错：{str(e)}")
