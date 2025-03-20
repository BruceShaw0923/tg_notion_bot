"""
Telegram 处理器模块

此包包含所有的Telegram消息和命令处理器。
"""

from services.telegram.handlers.commands import start, help_command, weekly_report_command, error_handler
from services.telegram.handlers.message import process_message
from services.telegram.handlers.document import process_document
from services.telegram.handlers.url import handle_url_message, handle_multiple_urls_message, handle_pdf_url
from services.telegram.handlers.todo import handle_todo_message

# 从paper_handlers导入(假设这是已有的模块)
from handlers.paper_handlers import list_collections, sync_papers_by_count, sync_papers_by_days

__all__ = [
    'start', 'help_command', 'weekly_report_command', 'error_handler',
    'process_message', 'process_document',
    'handle_url_message', 'handle_multiple_urls_message', 'handle_pdf_url',
    'handle_todo_message',
    'list_collections', 'sync_papers_by_count', 'sync_papers_by_days'
]
