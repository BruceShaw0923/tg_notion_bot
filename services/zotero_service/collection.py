"""
Zotero 收藏集模块 - 处理 Zotero 收藏集相关功能
"""

import logging
from .client import get_zotero_service

# 配置日志
logger = logging.getLogger(__name__)

def format_collection_list_for_telegram():
    """将收藏集列表格式化为 Telegram 显示格式"""
    service = get_zotero_service()
    collections = service.get_all_collections()
    if not collections:
        return "No collections found."
    
    formatted_list = "Available collections:\n\n"
    for coll in collections:
        formatted_list += f"📚 {coll['data']['name']}\n"
        formatted_list += f"ID: {coll['key']}\n\n"
    return formatted_list

def validate_collection_id(collection_id):
    """验证收藏集 ID 是否有效"""
    try:
        service = get_zotero_service()
        service.zot.collection(collection_id)
        return True
    except Exception:
        return False
