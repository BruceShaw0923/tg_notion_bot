from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
import os
import tempfile
import urllib3
import warnings
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS

# 尽早导入并使用 SSL 配置
from utils.ssl_helper import configure_ssl_verification

# 禁用不安全请求的警告（虽然在 ssl_helper 中已经设置，但保留这行作为备份）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 添加自定义警告记录
if os.environ.get('DISABLE_TELEGRAM_SSL_VERIFY', 'False').lower() in ('true', '1', 't', 'yes'):
    logging.warning("SSL 证书验证已禁用。这可能存在安全风险，仅建议在特殊网络环境中使用。")

from services.notion_service import (
    add_to_notion, add_to_todo_database, add_to_papers_database,
    is_pdf_url, download_pdf
)
from services.gemini_service import analyze_content, analyze_pdf_content
from services.url_service import extract_url_content
from utils.helpers import extract_url_from_text, extract_all_urls_from_text, is_url_only, download_file
from datetime import datetime, timedelta
import re
import requests
import pytz

# 导入论文处理器# 导入论文处理器 (同步版本)
from handlers.paper_handlers import (
    list_collections, 
    sync_papers_by_count, 
    sync_papers_by_days
)

# 配置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    """发送开始消息"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        update.message.reply_text('对不起，您没有权限使用此机器人。')
        return
    
    update.message.reply_text(
        '欢迎使用 TG-Notion 自动化机器人!\n'
        '您可以直接发送消息、链接或文件，机器人会将其保存到 Notion 数据库。\n'
        '\n'
        '特殊功能:\n'
        '- 发送纯 URL 会自动解析网页内容\n'
        '- 发送 PDF 文件会解析论文内容\n'
        '- 使用 #todo 标签可将任务添加到待办事项\n'
        '\n'
        'Zotero 功能:\n'
        '- /collections - 列出所有收藏集\n'
        '- /sync_papers - 同步最新论文\n'
        '- /sync_days - 同步近期论文\n'
        '\n'
        '输入 /help 查看详细使用说明'
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """发送帮助信息"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    update.message.reply_text(
        '使用指南:\n'
        '1. 直接发送任何消息，机器人会自动处理并保存到 Notion\n'
        '2. 发送纯链接时会自动提取网页内容并分析\n'
        '3. 发送 PDF 文件会进行论文解析并存入专用数据库\n'
        '4. 在消息中使用 #todo 标签将任务添加到待办事项列表\n'
        '5. 内容会被 AI 自动分析并生成摘要和标签\n'
        '6. 每周自动生成周报总结\n'
        '\n'
        'Zotero 相关命令:\n'
        '- /collections - 列出所有 Zotero 收藏集\n'
        '- /sync_papers [收藏集 ID] [数量] - 同步最近添加的指定数量论文\n'
        '- /sync_days [收藏集 ID] [天数] - 同步指定天数内添加的所有论文\n'
        '\n'
        '其他命令:\n'
        '- /start - 显示欢迎信息\n'
        '- /help - 显示此帮助信息\n'
        '- /weekly - 手动触发生成本周周报'
    )

def process_message(update: Update, context: CallbackContext) -> None:
    """处理收到的消息"""
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

def handle_multiple_urls_message(update: Update, content, urls, created_at):
    """处理包含多个 URL 的消息"""
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

def handle_url_message(update: Update, url, created_at):
    """处理纯 URL 消息"""
    # 首先检查是否是 PDF URL
    # 移除内部导入，使用顶部导入的函数
    
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

def handle_pdf_url(update: Update, url, created_at):
    """处理 PDF URL，下载并解析为论文"""
    try:
        # 从 URL 下载 PDF，使用顶部导入的函数
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

def handle_todo_message(update: Update, content, created_at):
    """处理带有 #todo 标签的消息"""
    try:
        # 提取持续时间参数（如果有）
        duration_match = re.search(r'#todo\s+(\d+(\.\d+)?h)', content, re.IGNORECASE)
        
        if duration_match:
            # 如果找到持续时间参数，提取小时数
            duration_str = duration_match.group(1)
            duration_hours = float(duration_str.rstrip('hH'))
            
            # 移除持续时间参数和 #todo 标签
            task_content = re.sub(r'#todo\s+\d+(\.\d+)?h', '', content, flags=re.IGNORECASE).strip()
        else:
            # 移除 #todo 标签
            task_content = content.replace("#todo", "").strip()
            
            # 根据当前时间计算默认持续时间
            beijing_tz = pytz.timezone('Asia/Shanghai')
            current_time = datetime.now(beijing_tz)
            
            if current_time.hour >= 12:
                # 如果晚于 12 点，设置 24 小时
                duration_hours = 24
            else:
                # 如果早于 12 点，设置到当天 24 点
                end_of_day = beijing_tz.localize(datetime(
                    current_time.year, 
                    current_time.month, 
                    current_time.day, 
                    23, 59, 59
                ))
                duration_hours = (end_of_day - current_time).total_seconds() / 3600
        
        # 添加到 Todo 数据库
        page_id = add_to_todo_database(task_content, created_at, duration_hours)
        
        update.message.reply_text(f"✅ 任务 {task_content} 已成功添加到待办事项列表！持续时间：{duration_hours:.1f}小时")
    except Exception as e:
        logger.error(f"添加待办事项时出错：{e}")
        update.message.reply_text(f"⚠️ 添加待办事项时出错：{str(e)}")

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

def extract_metadata_from_filename(filename):
    """
    尝试从文件名提取元数据，适用于常见的学术论文命名模式
    例如：Author_Year_Title.pdf 或 Title_Journal_Year.pdf
    
    参数：
    filename (str): PDF 文件名
    
    返回：
    dict: 提取的元数据
    """
    metadata = {}
    
    # 去除扩展名
    name_only = os.path.splitext(filename)[0]
    
    # 尝试分割常见分隔符
    parts = re.split(r'[_\-\s]+', name_only)
    
    # 尝试识别年份
    year_pattern = r'(19|20)\d{2}'
    years = []
    for part in parts:
        if re.match(year_pattern, part):
            years.append(part)
    
    if years:
        metadata['date'] = years[0]
    
    return metadata

def weekly_report_command(update: Update, context: CallbackContext) -> None:
    """手动触发生成周报"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    from services.weekly_report import generate_weekly_report
    
    update.message.reply_text("正在生成本周周报，请稍候...")
    
    try:
        report_url = generate_weekly_report()
        if report_url:
            update.message.reply_text(f"✅ 周报已生成！查看链接：{report_url}")
        else:
            update.message.reply_text("⚠️ 本周没有内容，无法生成周报")
    except Exception as e:
        logger.error(f"生成周报时出错：{e}")
        update.message.reply_text(f"⚠️ 生成周报时出错：{str(e)}")

def enrich_analysis_with_metadata(analysis: dict, metadata: dict) -> dict:
    """
    将 Zotero 元数据添加到 Gemini 分析结果
    
    参数：
        analysis: Gemini 分析结果
        metadata: Zotero 元数据
        
    返回：
        enriched_analysis: 添加元数据后的分析结果
    """
    result = analysis.copy() if analysis else {}
    
    # 使用元数据中的标题（如果存在且分析中未提供）
    if metadata.get('title') and not result.get('title'):
        result['title'] = metadata['title']
    
    # 添加作者信息
    if metadata.get('authors'):
        result['authors'] = metadata['authors']
    
    # 添加 DOI
    if metadata.get('doi'):
        result['doi'] = metadata['doi']
    
    # 添加出版信息
    if metadata.get('publication'):
        result['publication'] = metadata['publication']
    
    # 添加日期
    if metadata.get('date'):
        result['date'] = metadata['date']
    
    # 添加 URL（如果元数据中有而分析中没有）
    if metadata.get('url') and not result.get('url'):
        result['url'] = metadata['url']
    
    # 添加摘要（如果元数据中有而分析中没有）
    if metadata.get('abstract') and not result.get('brief_summary'):
        result['brief_summary'] = metadata['abstract']
    
    # 添加 Zotero 标签
    if metadata.get('tags'):
        result['zotero_tags'] = metadata['tags']
    
    # 添加 Zotero 键值
    if metadata.get('zotero_key'):
        result['zotero_key'] = metadata['zotero_key']
    
    return result

def prepare_metadata_for_notion(metadata):
    """
    从 Zotero 元数据准备 Notion 需要的元数据格式
    
    参数：
    metadata (dict): Zotero 元数据
    
    返回：
    dict: Notion 格式的元数据
    """
    notion_metadata = {}
    
    # 处理作者
    if metadata.get('creators'):
        authors = []
        for creator in metadata.get('creators', []):
            if creator.get('firstName') or creator.get('lastName'):
                author = f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
                authors.append(author)
        if authors:
            notion_metadata['authors'] = authors
    
    # 处理出版物信息
    if metadata.get('publicationTitle'):
        notion_metadata['publication'] = metadata.get('publicationTitle')
    
    # 处理日期
    if metadata.get('date'):
        notion_metadata['date'] = metadata.get('date')
    
    # 处理 DOI - 确保保存为小写以便一致性比较
    if metadata.get('DOI'):
        notion_metadata['doi'] = metadata.get('DOI', '').lower().strip()
    
    # 处理 Zotero 链接
    if metadata.get('zotero_key'):
        notion_metadata['zotero_link'] = f"zotero://select/library/items/{metadata.get('zotero_key')}"
    
    # 处理标签
    if metadata.get('tags'):
        tags = []
        for tag_obj in metadata.get('tags', []):
            if tag_obj.get('tag'):
                tags.append(tag_obj.get('tag'))
        if tags:
            notion_metadata['tags'] = tags
    
    return notion_metadata

def error_handler(update, context):
    """处理 Telegram 机器人运行中的错误"""
    # 日志记录错误详情
    logger.error(f"更新 {update} 导致错误：{context.error}")
    
    # 如果可能，向用户发送错误通知
    if update and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"抱歉，处理您的请求时发生了错误。错误已被记录，我们会尽快解决。"
        )

def setup_telegram_bot(updater=None):
    """设置并启动 Telegram 机器人"""
    # 如果已提供 updater，则使用它
    if updater:
        dispatcher = updater.dispatcher
        logger.info("使用已初始化的 updater 实例")
    else:
        # 设置更长的超时时间和重试连接逻辑
        request_kwargs = {
            'connect_timeout': 30.0,  # 连接超时时间
            'read_timeout': 30.0,     # 读取超时时间
            'con_pool_size': 10,      # 连接池大小
        }
        
        # 检查并添加代理设置
        proxy_url = os.environ.get('https_proxy') or os.environ.get('http_proxy') or os.environ.get('all_proxy')
        if proxy_url and proxy_url.strip():
            logger.info(f"Telegram 服务使用代理：{proxy_url}")
            request_kwargs['proxy_url'] = proxy_url
            
            # 设置 urllib3 代理参数
            urllib3_kwargs = {
                'timeout': 30
            }
            
            # 检查是否需要禁用证书验证
            if os.environ.get('DISABLE_TELEGRAM_SSL_VERIFY', 'False').lower() in ('true', '1', 't', 'yes'):
                urllib3_kwargs['cert_reqs'] = 'CERT_NONE'
                logger.info("Telegram 服务已禁用 SSL 证书验证")
            
            # 设置代理参数
            request_kwargs['urllib3_proxy_kwargs'] = urllib3_kwargs
        
        # 创建 Updater 并提供网络设置
        updater = Updater(TELEGRAM_BOT_TOKEN, request_kwargs=request_kwargs)
        dispatcher = updater.dispatcher
    
    # 创建用户过滤器
    user_filter = Filters.user(user_id=ALLOWED_USER_IDS) if ALLOWED_USER_IDS else None
    
    # 注册处理程序
    dispatcher.add_handler(CommandHandler("start", start, filters=user_filter))
    dispatcher.add_handler(CommandHandler("help", help_command, filters=user_filter))
    dispatcher.add_handler(CommandHandler("weekly", weekly_report_command, filters=user_filter))
    
    # 添加论文处理命令
    dispatcher.add_handler(CommandHandler("collections", list_collections, filters=user_filter))
    dispatcher.add_handler(CommandHandler("sync_papers", sync_papers_by_count, filters=user_filter))
    dispatcher.add_handler(CommandHandler("sync_days", sync_papers_by_days, filters=user_filter))
    
    # 添加消息处理器
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_message))
    dispatcher.add_handler(MessageHandler(Filters.photo, process_message))
    dispatcher.add_handler(MessageHandler(Filters.document, process_document))
    dispatcher.add_handler(MessageHandler(Filters.video, process_message))
    
    # 添加错误处理器
    dispatcher.add_error_handler(error_handler)
    logger.info("已添加命令和消息处理器")
    
    return updater

# 确保函数被正确导出
__all__ = ['setup_telegram_bot', 'start', 'help_command', 'process_message', 
           'handle_url_message', 'handle_todo_message', 'process_document', 
           'handle_pdf_document', 'weekly_report_command', 'handle_pdf_url',
           'handle_multiple_urls_message', 'enrich_analysis_with_metadata']
