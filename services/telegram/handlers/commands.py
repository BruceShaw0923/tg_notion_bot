"""
命令处理器模块

此模块包含处理 Telegram 机器人命令的函数。
"""

from telegram import Update
from telegram.ext import CallbackContext
import logging
from config import ALLOWED_USER_IDS

# 配置日志
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
