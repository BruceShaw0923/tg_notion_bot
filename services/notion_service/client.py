from notion_client import Client
import logging
from config import NOTION_TOKEN

logger = logging.getLogger(__name__)

# 在 client.py 中
notion = None

def get_notion_client():
    """获取 Notion 客户端"""
    global notion
    if notion is None:
        notion = Client(auth=NOTION_TOKEN)
    return notion

