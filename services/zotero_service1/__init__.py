"""
Zotero 服务模块 - 提供与 Zotero API 交互的功能

主要功能：
1. 获取 Zotero 收藏集和论文条目
2. 从 Zotero 条目中提取元数据
3. 处理 PDF 附件
4. 将 Zotero 条目同步到 Notion
"""

# 导入模块内容
from .client import get_zotero_service, ZoteroService
from .collection import format_collection_list_for_telegram, validate_collection_id
from .items import extract_metadata, get_pdf_attachment, get_recent_items
from .sync import (
    sync_items_to_notion, 
    sync_papers_to_notion, 
    sync_recent_papers_by_count, 
    sync_recent_papers_by_days,
    format_sync_result
)

# 导出函数和类，保持 API 兼容性
__all__ = [
    'get_zotero_service',
    'ZoteroService',
    'format_collection_list_for_telegram',
    'validate_collection_id',
    'extract_metadata',
    'get_pdf_attachment',
    'get_recent_items',
    'sync_items_to_notion',
    'sync_papers_to_notion',
    'sync_recent_papers_by_count',
    'sync_recent_papers_by_days',
    'format_sync_result'
]
