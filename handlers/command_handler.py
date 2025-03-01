import logging
from services.notion_service import create_auto_weekly_report, add_to_todo_database
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

def start_command(update: Update, context: CallbackContext):
    """处理 /start 命令"""
    update.message.reply_text(
        "欢迎使用 Telegram Notion 助手！\n\n"
        "您可以发送任何消息给我，我会将其添加到您的 Notion 数据库中。\n"
        "使用 /help 查看更多命令和功能。"
    )

def help_command(update: Update, context: CallbackContext):
    """处理 /help 命令"""
    help_text = (
        "🤖 *Telegram Notion 助手使用指南*\n\n"
        "*基本功能：*\n"
        "- 发送任何文本消息，我会将其保存到 Notion\n"
        "- 发送链接，我会提取内容并保存\n"
        "- 发送 PDF 文件，我会解析并保存摘要\n\n"
        "*命令列表：*\n"
        "/start - 启动机器人\n"
        "/help - 显示此帮助信息\n"
        "/weekly - 生成本周总结报告\n"
        "/todo <内容> - 添加待办事项到 Todo 数据库\n\n"
        "*提示：*\n"
        "消息会经过 AI 分析，自动生成摘要和标签"
    )
    update.message.reply_text(help_text, parse_mode='Markdown')

def weekly_command(update: Update, context: CallbackContext):
    """处理 /weekly 命令，生成周报"""
    try:
        update.message.reply_text("正在生成本周总结报告，请稍候...")
        report_url = create_auto_weekly_report()
        update.message.reply_text(f"周报已创建成功！\n\n查看链接：{report_url}")
    except Exception as e:
        logger.error(f"生成周报时出错：{e}")
        update.message.reply_text(f"生成周报时出错：{e}")

def todo_command(update: Update, context: CallbackContext):
    """处理 /todo 命令，添加待办事项"""
    try:
        # 获取命令之后的文本
        todo_text = ' '.join(context.args)
        if not todo_text:
            update.message.reply_text("请提供待办事项内容，格式：/todo 待办事项内容")
            return
            
        # 添加到 Notion Todo 数据库
        page_id = add_to_todo_database(todo_text)
        update.message.reply_text(f"待办事项已添加到 Notion！")
    except Exception as e:
        logger.error(f"添加待办事项时出错：{e}")
        update.message.reply_text(f"添加待办事项时出错：{e}")
