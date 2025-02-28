"""配置模块"""

import os
from typing import List
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = [int(user_id.strip()) for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",") if user_id.strip()]

# Notion 配置
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_PAPERS_DATABASE_ID = os.getenv("NOTION_PAPERS_DATABASE_ID", "")
NOTION_TODO_DATABASE_ID = os.getenv("NOTION_TODO_DATABASE_ID", "")

# Gemini API 配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Zotero 配置
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY", "")
ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID", "")
ZOTERO_FOLDER_ID = os.getenv("ZOTERO_FOLDER_ID", "")  # 默认文件夹 ID

# 周报配置
WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "Sunday")
WEEKLY_REPORT_HOUR = int(os.getenv("WEEKLY_REPORT_HOUR", "20"))

# 预定义标签类别
PREDEFINED_TAG_CATEGORIES = [
    "tools", "academic", "knowledge", "mental", 
    "technology", "math", "management"
]

# 检查必要的配置
if not TELEGRAM_BOT_TOKEN:
    logging.error("错误：TELEGRAM_BOT_TOKEN 未设置")
    
if not NOTION_TOKEN or not NOTION_DATABASE_ID:
    logging.error("错误：NOTION_TOKEN 或 NOTION_DATABASE_ID 未设置")

if not GEMINI_API_KEY:
    logging.error("错误：GEMINI_API_KEY 未设置")

# 检查 Zotero 配置
if not ZOTERO_API_KEY or not ZOTERO_USER_ID:
    logging.warning("警告：ZOTERO_API_KEY 或 ZOTERO_USER_ID 未设置，Zotero 功能将不可用")

# OpenAI API 配置 (如果使用)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")