import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import CallbackContext

from services.gemini_service import generate_weekly_summary
from services.notion_service import (
    create_weekly_report,
    generate_weekly_content,
    get_weekly_entries,
)

logger = logging.getLogger(__name__)


def weekly_report_command(update: Update, context: CallbackContext) -> None:
    """处理 /weekly 命令，生成并发送周报链接，包含 AI 生成的内容和所有消息链接"""
    chat_id = update.effective_chat.id

    # 发送正在处理的消息
    message = context.bot.send_message(
        chat_id=chat_id,
        text="正在生成本周周报，使用 AI 分析内容并创建内链，这可能需要一点时间...",
        disable_notification=True,
    )

    try:
        # 获取本周条目
        entries = get_weekly_entries(days=7)

        if not entries:
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text="本周没有添加任何内容，无法生成周报。",
            )
            return

        # 获取本周日期范围
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        week_number = today.isocalendar()[1]

        # 创建周报标题
        title = f"周报 {today.year} 第{week_number}周 ({start_of_week.strftime('%m.%d')}-{end_of_week.strftime('%m.%d')})"

        # 生成基本周报内容（包含所有条目的内链）
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="正在整理本周内容并创建内链...",
        )
        base_content = generate_weekly_content(entries)

        # 使用 AI 生成增强的周报分析，包含引用
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="正在使用 AI 生成周报总结，创建内容引用...",
        )
        ai_summary = generate_weekly_summary(entries)

        # 组合基本内容和 AI 生成的内容
        complete_content = f"{base_content}\n\n{ai_summary}"

        # 创建周报并获取链接
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text="正在创建 Notion 页面并处理内链引用...",
        )
        report_url = create_weekly_report(title, complete_content)

        # 更新消息
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text=f"✅ 周报已生成！\n\n包含本周内容摘要和 AI 总结，所有引用均已创建为 Notion 内链。\n\n在 Notion 中查看：{report_url}",
        )

    except Exception as e:
        logger.error(f"生成周报时出错：{e}")
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text=f"❌ 生成周报时出错：{str(e)}",
        )
