from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
import os
import tempfile
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
from services.notion_service import add_to_notion, add_to_todo_database, add_to_papers_database
from services.gemini_service import analyze_content, analyze_pdf_content
from services.url_service import extract_url_content
from utils.helpers import extract_url_from_text, extract_all_urls_from_text, is_url_only, download_file
from services.zotero_service import sync_recent_pdfs, get_collections
from datetime import datetime
import re

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
        '特殊功能:\n'
        '- 发送纯 URL 会自动解析网页内容\n'
        '- 发送 PDF 文件会解析论文内容\n'
        '- 使用 #todo 标签可将任务添加到待办事项\n'
        '\n'
        '命令列表:\n'
        '/start - 显示此帮助信息\n'
        '/help - 显示帮助信息\n'
        '/weekly - 手动触发生成本周周报'
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
        '7. 使用 /weekly 命令可手动触发生成本周周报\n'
        '8. 使用 /zotero [天数] [collection:集合 ID] 同步 Zotero 内容\n'
        '9. 使用 /collections 查看所有 Zotero 集合列表'
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
    
    # 检查是否有多个 URL
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
    from services.notion_service import is_pdf_url
    
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
        # 从 URL 下载 PDF
        from services.notion_service import download_pdf
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
        # 移除 #todo 标签
        task_content = content.replace("#todo", "").strip()
        
        # 添加到 Todo 数据库
        page_id = add_to_todo_database(task_content, created_at)
        
        update.message.reply_text(f"✅ 任务 {content} 已成功添加到待办事项列表！")
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

def sync_zotero_command(update: Update, context: CallbackContext) -> None:
    """同步 Zotero 最近的 PDF 文件"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    # 解析参数
    args = context.args
    days = 3  # 默认天数
    collection_id = None
    
    # 处理参数
    if args:
        for arg in args:
            # 检查是否是数字（天数）
            if arg.isdigit():
                days = int(arg)
            # 检查是否是集合指定参数
            elif arg.startswith("collection:") or arg.startswith("c:"):
                collection_id = arg.split(":", 1)[1]
    
    # 验证 days 参数
    if days <= 0:
        update.message.reply_text("⚠️ 天数必须大于 0，已设为默认值 3 天")
        days = 3
    elif days > 30:
        update.message.reply_text("⚠️ 天数过大可能导致性能问题，已限制为最多 30 天")
        days = 30
    
    # 记录本地和 UTC 时间，帮助调试
    local_time = datetime.now()
    utc_time = datetime.utcnow()
    logger.info(f"当前本地时间：{local_time.isoformat()}, UTC 时间：{utc_time.isoformat()}")
    
    # 根据是否指定集合显示不同消息
    if collection_id:
        from services.zotero_service import collection_exists
        
        # 先验证集合是否存在
        if not collection_exists(collection_id):
            update.message.reply_text(f"⚠️ 集合 {collection_id} 不存在或无法访问。使用 /collections 命令查看可用集合列表。")
            return
            
        update.message.reply_text(f"开始同步 Zotero 集合 {collection_id} 中最近 {days} 天添加的 PDF 文件...")
    else:
        update.message.reply_text(f"开始同步 Zotero 中最近 {days} 天添加的 PDF 文件...")
    
    try:
        # 获取并处理 PDF 文件
        pdf_files = sync_recent_pdfs(days, collection_id)
        
        if not pdf_files:
            update.message.reply_text("未找到最近添加的 PDF 文件")
            return
        
        update.message.reply_text(f"找到 {len(pdf_files)} 个条目，开始处理...")
        
        # 逐个处理 PDF 文件
        success_count = 0
        metadata_only_count = 0
        
        for pdf_path, filename, metadata in pdf_files:
            try:
                # 检查是否只有元数据没有 PDF 文件
                if pdf_path is None:
                    update.message.reply_text(f"⚠️ 无法下载文件：{filename}，但将存储其元数据")
                    metadata_only_count += 1
                    
                    # 将元数据直接添加到 Notion，不包含 PDF 分析
                    title = metadata.get('title', '') or filename
                    
                    # 创建简单的分析结果
                    simple_analysis = {
                        "title": title,
                        "brief_summary": metadata.get('abstractNote', '无摘要'),
                        "details": f"## 元数据\n\n**标题**: {title}无法下载 PDF 文件，仅显示元数据。",
                        "insight": "无法下载 PDF 文件进行分析。"
                    }
                    
                    # 准备元数据字典
                    notion_metadata = prepare_metadata_for_notion(metadata)
                    
                    # 添加到 Notion 数据库
                    page_id = add_to_papers_database(
                        title=title,
                        analysis=simple_analysis,
                        created_at=datetime.now(),
                        pdf_url=metadata.get('url', ''),  # 可能是 DOI 链接或原始 URL
                        metadata=notion_metadata
                    )
                    
                    success_count += 1
                    continue
                
                update.message.reply_text(f"正在处理：{filename}...")
                
                # 使用 Gemini 分析 PDF 内容
                pdf_analysis = analyze_pdf_content(pdf_path, metadata.get('url', ''))
                
                # 标题优先使用元数据中的标题
                title = metadata.get('title', '') or filename
                
                # 添加元数据到分析结果
                enriched_analysis = enrich_analysis_with_metadata(pdf_analysis, metadata)
                
                # 准备元数据字典
                notion_metadata = prepare_metadata_for_notion(metadata)
                
                # 添加到 Notion 数据库
                page_id = add_to_papers_database(
                    title=title,
                    analysis=enriched_analysis,
                    created_at=datetime.now(),
                    pdf_url=metadata.get('url', ''),
                    metadata=notion_metadata
                )
                
                success_count += 1
                
                # 清理临时文件
                try:
                    os.unlink(pdf_path)
                except:
                    pass
                
            except Exception as e:
                logger.error(f"处理 PDF 文件 {filename} 时出错：{e}")
                update.message.reply_text(f"⚠️ 处理 {filename} 时出错：{str(e)}")
        
        # 显示结果统计
        if metadata_only_count > 0:
            update.message.reply_text(f"✅ Zotero 同步完成！成功处理 {success_count}/{len(pdf_files)} 个条目，其中 {metadata_only_count} 个仅包含元数据（无法下载 PDF 文件）。")
        else:
            update.message.reply_text(f"✅ Zotero 同步完成！成功处理 {success_count}/{len(pdf_files)} 个条目。")
    
    except Exception as e:
        logger.error(f"Zotero 同步过程中出错：{e}")
        update.message.reply_text(f"⚠️ Zotero 同步过程中出错：{str(e)}")

def list_zotero_collections_command(update: Update, context: CallbackContext) -> None:
    """列出所有 Zotero 集合（文件夹）"""
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    
    update.message.reply_text("正在获取 Zotero 集合列表...")
    
    try:
        collections = get_collections()
        
        if not collections:
            update.message.reply_text("未找到 Zotero 集合")
            return
        
        # 构建集合列表消息
        message = "Zotero 集合列表：\n\n"
        for i, collection in enumerate(collections, 1):
            collection_data = collection.get('data', {})
            collection_id = collection_data.get('key', '')
            collection_name = collection_data.get('name', f'未命名集合 {i}')
            message += f"{i}. {collection_name}\n   ID: {collection_id}\n\n"
        
        message += "\n使用方法：/zotero [天数] collection:集合 ID"
        
        update.message.reply_text(message)
    
    except Exception as e:
        logger.error(f"获取 Zotero 集合列表时出错：{e}")
        update.message.reply_text(f"⚠️ 获取 Zotero 集合列表时出错：{str(e)}")

def enrich_analysis_with_metadata(analysis, metadata):
    """
    使用元数据丰富分析结果
    
    参数：
    analysis (dict): PDF 分析结果
    metadata (dict): Zotero 元数据
    
    返回：
    dict: 丰富后的分析结果
    """
    # 如果分析结果为空，创建一个新字典
    if not analysis:
        analysis = {
            "title": "",
            "brief_summary": "",
            "details": "",
            "insight": ""
        }
    
    # 用元数据补充分析结果
    if metadata.get('title') and not analysis.get('title'):
        analysis['title'] = metadata.get('title')
    
    if metadata.get('abstractNote') and not analysis.get('brief_summary'):
        analysis['brief_summary'] = metadata.get('abstractNote')
    
    # 添加元数据部分
    meta_section = "\n\n## 文献元数据\n\n"
    
    # 添加作者
    creators = metadata.get('creators', [])
    if creators:
        authors = [f"{c.get('firstName', '')} {c.get('lastName', '')}" for c in creators]
        meta_section += f"**作者**: {', '.join(authors)}\n\n"
    
    # 添加发表信息
    if metadata.get('publicationTitle'):
        meta_section += f"**发表于**: {metadata.get('publicationTitle')}\n\n"
    
    # 添加日期
    if metadata.get('date'):
        meta_section += f"**日期**: {metadata.get('date')}\n\n"
    
    # 添加 DOI
    if metadata.get('DOI'):
        meta_section += f"**DOI**: {metadata.get('DOI')}\n\n"
    
    # 添加标签
    tags = metadata.get('tags', [])
    if tags:
        tag_names = [tag.get('tag', '') for tag in tags]
        meta_section += f"**标签**: {', '.join(tag_names)}\n\n"
    
    # 添加 Zotero 链接
    if metadata.get('zotero_key'):
        meta_section += f"**Zotero**: zotero://select/library/items/{metadata.get('zotero_key')}\n\n"
    
    # 将元数据部分附加到详细信息中
    analysis['details'] = analysis.get('details', '') + meta_section
    
    return analysis

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
    
    # 处理 DOI
    if metadata.get('DOI'):
        notion_metadata['doi'] = metadata.get('DOI')
    
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

def setup_telegram_bot():
    """设置并启动 Telegram 机器人"""
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher
    
    # 注册处理程序
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("weekly", weekly_report_command))
    dispatcher.add_handler(CommandHandler("zotero", sync_zotero_command))
    dispatcher.add_handler(CommandHandler("collections", list_zotero_collections_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_message))
    dispatcher.add_handler(MessageHandler(Filters.photo, process_message))
    dispatcher.add_handler(MessageHandler(Filters.document, process_document))
    dispatcher.add_handler(MessageHandler(Filters.video, process_message))
    
    return updater

# 确保函数被正确导出
__all__ = ['setup_telegram_bot', 'start', 'help_command', 'process_message', 
           'handle_url_message', 'handle_todo_message', 'process_document', 
           'handle_pdf_document', 'weekly_report_command', 'handle_pdf_url', 'handle_multiple_urls_message']
