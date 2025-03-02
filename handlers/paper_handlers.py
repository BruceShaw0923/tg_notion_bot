"""
处理与论文和 Zotero 相关的 Telegram 命令
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext
import re

from services.zotero_service import (
    get_zotero_service,  # 导入服务实例获取函数
    sync_papers_to_notion,  # 导入新的统一同步函数
    validate_collection_id
)

logger = logging.getLogger(__name__)

def list_collections(update: Update, context: CallbackContext) -> None:
    """
    列出所有 Zotero 收藏集
    命令格式：/collections
    """
    try:
        # 获取 Zotero 服务实例
        zotero_service = get_zotero_service()
        # 获取格式化的收藏集列表
        collections_text = zotero_service.format_collection_list_for_telegram()
        
        update.message.reply_text(collections_text)
    except Exception as e:
        logger.error(f"列出 Zotero 收藏集时出错：{e}")
        update.message.reply_text(f"⚠️ 获取 Zotero 收藏集时出错：{str(e)}")

def sync_papers_by_count(update: Update, context: CallbackContext) -> None:
    """
    按数量同步最近的论文
    命令格式：/sync_papers [收藏集 ID] [数量]
    默认同步所有收藏集的 5 篇最新论文
    """
    args = context.args
    collection_id = None
    count = 5  # 默认同步 5 篇
    
    # 解析参数
    if args:
        # 检查第一个参数
        if len(args) >= 1:
            # 如果第一个参数看起来像是收藏集 ID（8 位字母数字字符）
            if re.match(r'^[A-Z0-9]{8}$', args[0], re.I):
                collection_id = args[0]
                # 确认是否是有效的收藏集 ID
                if not validate_collection_id(collection_id):
                    update.message.reply_text(f"⚠️ 无效的收藏集 ID: {collection_id}")
                    return
                # 如果有第二个参数，尝试解析为数量
                if len(args) >= 2:
                    try:
                        count = int(args[1])
                    except ValueError:
                        update.message.reply_text("⚠️ 无效的数量参数，使用默认值 5")
            else:
                # 第一个参数不是收藏集 ID，尝试解析为数量
                try:
                    count = int(args[0])
                except ValueError:
                    update.message.reply_text("⚠️ 无效的参数，使用默认值：所有收藏集的 5 篇最新论文")
    
    # 执行同步并提供反馈
    update.message.reply_text(f"正在同步{'指定收藏集' if collection_id else '所有收藏集'}的 {count} 篇最新论文...")
    
    try:
        # 使用统一函数，指定过滤类型为"count"
        result_message = sync_papers_to_notion(collection_id, "count", count)
        update.message.reply_text(result_message)
    except Exception as e:
        logger.error(f"同步论文时出错：{e}")
        update.message.reply_text(f"⚠️ 同步论文时出错：{str(e)}")

def sync_papers_by_days(update: Update, context: CallbackContext) -> None:
    """
    同步最近几天内添加的所有论文
    命令格式：/sync_days [收藏集 ID] [天数]
    默认同步所有收藏集 7 天内的论文
    """
    args = context.args
    collection_id = None
    days = 7  # 默认同步 7 天内的论文
    
    # 解析参数
    if args:
        # 检查第一个参数
        if len(args) >= 1:
            # 如果第一个参数看起来像是收藏集 ID
            if re.match(r'^[A-Z0-9]{8}$', args[0], re.I):
                collection_id = args[0]
                # 确认是否是有效的收藏集 ID
                if not validate_collection_id(collection_id):
                    update.message.reply_text(f"⚠️ 无效的收藏集 ID: {collection_id}")
                    return
                # 如果有第二个参数，尝试解析为天数
                if len(args) >= 2:
                    try:
                        days = int(args[1])
                    except ValueError:
                        update.message.reply_text("⚠️ 无效的天数参数，使用默认值 7")
            else:
                # 第一个参数不是收藏集 ID，尝试解析为天数
                try:
                    days = int(args[0])
                except ValueError:
                    update.message.reply_text("⚠️ 无效的参数，使用默认值：所有收藏集的 7 天内论文")
    
    # 执行同步并提供反馈
    update.message.reply_text(f"正在同步{'指定收藏集' if collection_id else '所有收藏集'}的最近 {days} 天内添加的论文...")
    
    try:
        # 使用统一函数，指定过滤类型为"days"
        result_message = sync_papers_to_notion(collection_id, "days", days)
        update.message.reply_text(result_message)
    except Exception as e:
        logger.error(f"同步论文时出错：{e}")
        update.message.reply_text(f"⚠️ 同步论文时出错：{str(e)}")
