"""
Zotero 收藏集模块 - 处理 Zotero 收藏集
"""

import logging

from .client import get_zotero_service

# 配置日志
logger = logging.getLogger(__name__)


# 如果函数定义中有 self 参数，需要移除它
def format_collection_list_for_telegram() -> str:
    """
    格式化 Zotero 收藏集列表用于 Telegram 显示

    返回：
        格式化后的收藏集列表文本
    """
    service = get_zotero_service()
    try:
        collections = service.get_all_collections()
        if not collections:
            return "❌ 未找到收藏集"

        result = "📚 Zotero 收藏集列表：\n\n"
        for collection in collections:
            collection_id = collection["key"]
            collection_name = collection["data"]["name"]
            result += f"📁 {collection_name}\n"
            result += f"   ID: `{collection_id}`\n\n"

        result += "\n使用方法：\n"
        result += "/sync_papers [收藏集 ID] [数量] - 同步指定收藏集的最新论文\n"
        result += "/sync_days [收藏集 ID] [天数] - 同步指定收藏集最近几天内的论文"

        return result
    except Exception as e:
        logger.error(f"格式化收藏集列表时出错：{e}")
        return f"❌ 获取收藏集列表时出错：{str(e)}"


# 如果函数定义中有 self 参数，需要移除它
def validate_collection_id(collection_id: str) -> bool:
    """
    验证收藏集 ID 是否有效

    参数：
        collection_id: 要验证的收藏集 ID

    返回：
        如果 ID 有效返回 True，否则返回 False
    """
    service = get_zotero_service()
    try:
        collections = service.get_all_collections()
        return any(collection["key"] == collection_id for collection in collections)
    except Exception as e:
        logger.error(f"验证收藏集 ID 时出错：{e}")
        return False
