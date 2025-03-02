import os
import sys
import logging
import schedule
import time
from datetime import datetime
import threading
import signal
from telegram.ext import CommandHandler, Filters
from pathlib import Path
from services.telegram_service import setup_telegram_bot
from services.weekly_report import generate_weekly_report
from config import WEEKLY_REPORT_DAY, WEEKLY_REPORT_HOUR, TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, LOG_LEVEL
from telegram.error import (TelegramError, Unauthorized, BadRequest, 
                           TimedOut, ChatMigrated, NetworkError)

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler(os.path.join(root_dir, "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局设置
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds
should_exit = False

def schedule_weekly_report():
    """安排周报生成任务"""
    schedule_day = WEEKLY_REPORT_DAY.lower()
    schedule_hour = f"{WEEKLY_REPORT_HOUR:02d}:00"
    
    if schedule_day == "monday":
        schedule.every().monday.at(schedule_hour).do(generate_weekly_report)
    elif schedule_day == "tuesday":
        schedule.every().tuesday.at(schedule_hour).do(generate_weekly_report)
    elif schedule_day == "wednesday":
        schedule.every().wednesday.at(schedule_hour).do(generate_weekly_report)
    elif schedule_day == "thursday":
        schedule.every().thursday.at(schedule_hour).do(generate_weekly_report)
    elif schedule_day == "friday":
        schedule.every().friday.at(schedule_hour).do(generate_weekly_report)
    elif schedule_day == "saturday":
        schedule.every().saturday.at(schedule_hour).do(generate_weekly_report)
    else:  # 默认周日
        schedule.every().sunday.at(schedule_hour).do(generate_weekly_report)
    
    logger.info(f"已安排周报生成任务：每{WEEKLY_REPORT_DAY} {schedule_hour}")

def run_scheduler():
    """运行定时任务"""
    while not should_exit:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
        except Exception as e:
            logger.error(f"定时任务执行错误：{e}")
            time.sleep(300)  # 出错后等待 5 分钟再继续

def signal_handler(sig, frame):
    """处理进程信号，优雅退出"""
    global should_exit
    logger.info("接收到中断信号，准备停止机器人...")
    should_exit = True

def start_polling(updater, retry_count=0):
    """启动轮询，添加重试逻辑"""
    try:
        logger.info("启动机器人轮询...")
        updater.start_polling()
        logger.info("机器人已成功启动，正在监听消息")
    except NetworkError as e:
        retry_count += 1
        if retry_count <= MAX_RETRIES:
            logger.warning(f"网络错误：{e}. 尝试重新连接 ({retry_count}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)
            start_polling(updater, retry_count)
        else:
            logger.error(f"重试连接次数达到上限 ({MAX_RETRIES})，无法启动机器人")
            raise
    except Exception as e:
        logger.error(f"启动机器人时发生错误：{e}")
        raise

def main():
    """主函数"""
    logger.info("启动 TG-Notion 机器人...")
    
    # 确认配置
    if not TELEGRAM_BOT_TOKEN:
        logger.error("错误：未设置 Telegram 机器人令牌")
        return 1
    
    if not ALLOWED_USER_IDS:
        logger.warning("警告：未设置允许的用户 ID，任何人都可以访问机器人")
    
    # 设置机器人
    updater = setup_telegram_bot()
    
    # 设置定时任务
    schedule_weekly_report()
    
    # 在单独的线程中运行调度器
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # 启动机器人，添加重试逻辑
    start_polling(updater)
    
    # 等待，直到收到停止信号
    updater.idle()
    
    logger.info("机器人已停止")
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
