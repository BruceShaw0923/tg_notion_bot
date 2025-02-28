from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
import os
import tempfile
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS
from services.notion_service import add_to_notion, add_to_todo_database, add_to_papers_database
from services.gemini_service import analyze_content, analyze_pdf_content
from services.url_service import extract_url_content
from utils.helpers import extract_url_from_text, is_url_only, download_file
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
        '7. 使用 /weekly 命令可手动触发生成本周周报'
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
    
    # 检查是否有 URL
    url = extract_url_from_text(content)
    
    # 使用 Gemini API 分析内容
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
        
        # 添加到论文数据库，使用正确的参数名称 pdf_url 而不是 file_path
        page_id = add_to_papers_database(
            title=document.file_name,
            analysis=pdf_analysis,
            created_at=created_at,
            pdf_url=pdf_path  # 修改为正确的参数名称
        )
        
        # 清理临时文件 (可选，如果想保留文件可以注释掉这一行)
        # os.unlink(pdf_path)
        
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

def setup_telegram_bot():
    """设置并启动 Telegram 机器人"""
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher
    
    # 注册处理程序
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("weekly", weekly_report_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_message))
    dispatcher.add_handler(MessageHandler(Filters.photo, process_message))
    dispatcher.add_handler(MessageHandler(Filters.document, process_document))
    dispatcher.add_handler(MessageHandler(Filters.video, process_message))
    
    return updater

# 确保函数被正确导出
__all__ = ['setup_telegram_bot', 'start', 'help_command', 'process_message', 
           'handle_url_message', 'handle_todo_message', 'process_document', 
           'handle_pdf_document', 'weekly_report_command', 'handle_pdf_url']
