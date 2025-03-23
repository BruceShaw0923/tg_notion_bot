from telegram import Update
import logging
import re
from datetime import datetime
import pytz
from services.notion_service import add_to_todo_database

# 配置日志
logger = logging.getLogger(__name__)

def handle_todo_message(update: Update, content, created_at):
    """处理带有 #todo 标签的消息"""
    try:
        # 提取持续时间参数（如果有）
        duration_match = re.search(r'#todo\s+(\d+(\.\d+)?h)', content, re.IGNORECASE)
        
        if duration_match:
            # 如果找到持续时间参数，提取小时数
            duration_str = duration_match.group(1)
            duration_hours = float(duration_str.rstrip('hH'))
            
            # 移除持续时间参数和 #todo 标签
            task_content = re.sub(r'#todo\s+\d+(\.\d+)?h', '', content, flags=re.IGNORECASE).strip()
        else:
            # 移除 #todo 标签
            task_content = content.replace("#todo", "").strip()
            
            # 根据当前时间计算默认持续时间
            beijing_tz = pytz.timezone('Asia/Shanghai')
            current_time = datetime.now(beijing_tz)
            
            if current_time.hour >= 12:
                # 如果晚于 12 点，设置 24 小时
                duration_hours = 24
            else:
                # 如果早于 12 点，设置到当天 24 点
                end_of_day = beijing_tz.localize(datetime(
                    current_time.year, 
                    current_time.month, 
                    current_time.day, 
                    23, 59, 59
                ))
                duration_hours = (end_of_day - current_time).total_seconds() / 3600
        
        # 添加到 Todo 数据库
        page_id = add_to_todo_database(task_content, created_at, duration_hours)
        
        update.message.reply_text(f"✅ 任务 {task_content} 已成功添加到待办事项列表！持续时间：{duration_hours:.1f}小时")
    except Exception as e:
        logger.error(f"添加待办事项时出错：{e}")
        update.message.reply_text(f"⚠️ 添加待办事项时出错：{str(e)}")
