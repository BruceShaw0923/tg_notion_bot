import logging
from notion_client import Client
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_TODO_DATABASE_ID, NOTION_PAPERS_DATABASE_ID

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_papers_database():
    """确保论文数据库有必要的属性"""
    if not NOTION_PAPERS_DATABASE_ID:
        logger.error("未设置论文数据库 ID")
        return False
    
    try:
        notion = Client(auth=NOTION_TOKEN)
        
        # 获取当前数据库结构
        database = notion.databases.retrieve(database_id=NOTION_PAPERS_DATABASE_ID)
        
        # 检查是否已有 Abstract 属性
        if "Abstract" not in database["properties"]:
            # 添加 Abstract 属性
            notion.databases.update(
                database_id=NOTION_PAPERS_DATABASE_ID,
                properties={
                    "Abstract": {
                        "rich_text": {}
                    }
                }
            )
            logger.info("已成功添加 Abstract 属性到论文数据库")
        else:
            logger.info("Abstract 属性已存在于论文数据库中")
        
        return True
    except Exception as e:
        logger.error(f"设置论文数据库时出错：{e}")
        return False

if __name__ == "__main__":
    logger.info("正在设置 Notion 数据库...")
    setup_papers_database()
    logger.info("数据库设置完成")
