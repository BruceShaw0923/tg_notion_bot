"""
Zotero 客户端模块 - 处理 Zotero API 连接

提供 Zotero API 客户端初始化和单例模式实现
"""

import logging
import os

from dotenv import load_dotenv
from pyzotero import zotero

from config import ZOTERO_API_KEY, ZOTERO_USER_ID

# 加载环境变量
load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

# 单例实例
_zotero_service_instance = None


class ZoteroService:
    def __init__(self):
        """初始化 ZoteroService，设置 API 凭证和 PDF 存储路径"""
        self.api_key = ZOTERO_API_KEY
        self.user_id = ZOTERO_USER_ID
        self.zot = zotero.Zotero(self.user_id, "user", self.api_key)

        # 从环境变量获取 PDF 存储路径，如果没有则使用默认值
        self.pdf_storage_path = os.environ.get(
            "ZOTERO_PDF_PATH", "/Users/wangruochen/Zotero/storage/pdfs"
        )
        # 记录 PDF 存储路径，方便调试
        logger.info(f"Using PDF storage path: {self.pdf_storage_path}")
        # 检查路径是否存在
        if not os.path.exists(self.pdf_storage_path):
            logger.warning(f"PDF storage path does not exist: {self.pdf_storage_path}")

    def get_all_collections(self):
        """获取所有 Zotero 收藏集"""
        try:
            collections = self.zot.collections()
            return collections
        except Exception as e:
            logger.error(f"Error getting collections: {str(e)}")
            return []

    # 添加兼容性方法 - 为从实例调用而设计的代理方法
    def format_collection_list_for_telegram(self):
        """代理到 collection 模块中的同名函数"""
        from .collection import format_collection_list_for_telegram

        return format_collection_list_for_telegram()

    def validate_collection_id(self, collection_id):
        """代理到 collection 模块中的同名函数"""
        from .collection import validate_collection_id

        return validate_collection_id(collection_id)

    def extract_metadata(self, item):
        """代理到 items 模块中的同名函数"""
        from .items import extract_metadata

        return extract_metadata(item)

    def get_pdf_attachment(self, item_key):
        """代理到 items 模块中的同名函数"""
        from .items import get_pdf_attachment

        return get_pdf_attachment(item_key)

    def get_recent_items(self, collection_id=None, filter_type="count", value=5):
        """代理到 items 模块中的同名函数"""
        from .items import get_recent_items

        return get_recent_items(collection_id, filter_type, value)

    def sync_items_to_notion(self, items):
        """代理到 sync 模块中的同名函数"""
        from .sync import sync_items_to_notion

        return sync_items_to_notion(items)

    def sync_papers_to_notion(self, collection_id=None, filter_type="count", value=5):
        """代理到 sync 模块中的同名函数"""
        from .sync import sync_papers_to_notion

        return sync_papers_to_notion(collection_id, filter_type, value)

    def sync_recent_papers_by_count(self, collection_id=None, count=5):
        """代理到 sync 模块中的同名函数"""
        from .sync import sync_recent_papers_by_count

        return sync_recent_papers_by_count(collection_id, count)

    def sync_recent_papers_by_days(self, collection_id=None, days=7):
        """代理到 sync 模块中的同名函数"""
        from .sync import sync_recent_papers_by_days

        return sync_recent_papers_by_days(collection_id, days)


def get_zotero_service():
    """获取 ZoteroService 的单例实例"""
    global _zotero_service_instance
    if _zotero_service_instance is None:
        _zotero_service_instance = ZoteroService()
    return _zotero_service_instance
