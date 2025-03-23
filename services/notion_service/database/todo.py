import logging
from datetime import datetime, timedelta

import pytz

from config import NOTION_TODO_DATABASE_ID
from utils.helpers import truncate_text

from ..client import get_notion_client

logger = logging.getLogger(__name__)
notion = get_notion_client()


def add_to_todo_database(content, created_at=None, duration_hours=None):
    """
    将待办事项添加到 Notion 待办事项数据库

    参数：
    content (str): 待办事项内容
    created_at (datetime): 创建时间
    duration_hours (float): 任务持续时间（小时）

    返回：
    str: 创建的页面 ID
    """
    if not NOTION_TODO_DATABASE_ID:
        logger.error("未设置待办事项数据库 ID")
        raise ValueError("未设置待办事项数据库 ID")

    if not created_at:
        created_at = datetime.now()

    # 确保 created_at 有时区信息
    if created_at.tzinfo is None:
        beijing_tz = pytz.timezone("Asia/Shanghai")
        created_at = beijing_tz.localize(created_at)

    # 计算结束时间
    if duration_hours is not None:
        end_time = created_at + timedelta(hours=duration_hours)
    else:
        # 默认设置 24 小时
        end_time = created_at + timedelta(hours=24)

    # 截取标题
    title = truncate_text(content, 100)

    try:
        # 准备日期属性，包含开始和结束时间
        date_property = {"start": created_at.isoformat()}

        # 添加结束时间
        date_property["end"] = end_time.isoformat()

        new_page = notion.pages.create(
            parent={"database_id": NOTION_TODO_DATABASE_ID},
            properties={
                "Name": {"title": [{"text": {"content": title}}]},
                "Status": {"select": {"name": "待办"}},
                "Priority": {"select": {"name": "中"}},
                "Created": {"date": date_property},
            },
            children=[
                {
                    "object": "block",
                    "paragraph": {"rich_text": [{"text": {"content": content}}]},
                }
            ],
        )
        logger.info(f"成功创建待办事项：{new_page['id']}")
        return new_page["id"]

    except Exception as e:
        logger.error(f"创建待办事项时出错：{e}")
        raise
