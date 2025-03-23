import logging
import os

from services.gemini_service import analyze_pdf_content
from services.notion_service import add_to_papers_database

logger = logging.getLogger(__name__)


def handle_pdf(update, context, pdf_path, url=None):
    """
    处理 PDF 文件并添加到 Notion 数据库

    参数：
    update: Telegram 更新对象
    context: Telegram 上下文对象
    pdf_path (str): PDF 文件的本地路径
    url (str, optional): PDF 的原始 URL
    """
    try:
        # 发送状态消息
        status_message = update.message.reply_text("正在分析 PDF 文件，请稍候...")

        # 使用 Gemini 分析 PDF 内容
        analysis_result = analyze_pdf_content(pdf_path, url)

        if analysis_result:
            # 添加到 Notion 论文数据库
            notion_response = add_to_papers_database(
                title=analysis_result.get("title", "未命名论文"),
                analysis={
                    "brief_summary": analysis_result.get("brief_summary", ""),
                    "details": analysis_result.get("details", ""),
                },
                pdf_url=url,
            )

            if notion_response:
                status_message.edit_text(
                    f"PDF 已成功添加到 Notion 数据库！\n\n标题：{analysis_result.get('title', '未命名论文')}"
                )
            else:
                status_message.edit_text(
                    "无法将 PDF 添加到 Notion 数据库，请查看日志了解详情。"
                )
        else:
            status_message.edit_text("无法分析 PDF 内容，请尝试其他文件。")

    except Exception as e:
        logger.error(f"处理 PDF 文件时出错：{e}")
        update.message.reply_text(f"处理 PDF 文件时出错：{str(e)}")
    finally:
        # 清理临时文件
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"临时 PDF 文件已删除：{pdf_path}")
        except Exception as e:
            logger.warning(f"删除临时 PDF 文件时出错：{e}")
