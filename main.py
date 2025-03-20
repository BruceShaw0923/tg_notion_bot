#!/usr/bin/env python3
"""
Telegram Notion Bot 主程序入口
整合 bot_main 和 main 的功能，统一处理 SSL 证书验证和机器人初始化
"""

import os
import sys
import logging
import schedule
import time
import threading
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

# 首先加载环境变量，确保设置可用
load_dotenv()

# 导入保活模块
from utils.keep_alive import KEEP_ALIVE

# 导入智能代理设置（替代 SSL helper）
from utils.smart_proxy import configure_proxy_for_telegram, test_connectivity

# 然后导入 telegram 相关模块
import telegram
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.utils.request import Request
from telegram.error import (TelegramError, Unauthorized, BadRequest, 
                           TimedOut, ChatMigrated, NetworkError)

# 导入其他服务和配置
from config import (LOG_LEVEL, TELEGRAM_BOT_TOKEN,
                    ALLOWED_USER_IDS, WEEKLY_REPORT_DAY, WEEKLY_REPORT_HOUR)
import services.notion_service as notion_service
from services.telegram_service import setup_telegram_bot
from services.weekly_report import generate_weekly_report

# 导入参数验证工具
from utils.telegram_helper import validate_request_kwargs, monitor_telegram_webhook, clear_webhook

# 确保日志目录存在
os.makedirs(os.path.join(root_dir, "logs"), exist_ok=True)

# 配置日志系统
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler(os.path.join(root_dir, "logs", "bot.log"), mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局设置
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds
should_exit = False
connection_check_interval = 600  # 10 分钟检查一次连接

def init_bot(token: str, disable_certificate_verification: bool = False) -> Optional[Updater]:
    """
    初始化 Telegram 机器人，提供证书验证选项
    
    参数：
        token: Telegram Bot API 令牌
        disable_certificate_verification: 是否禁用 SSL 证书验证
        
    返回：
        Updater 对象，如果初始化成功
    """
    retry_count = 0
    max_retries = MAX_RETRIES
    
    while retry_count < max_retries:
        try:
            # 使用智能代理配置获取请求参数
            request_kwargs = configure_proxy_for_telegram()
            
            # 验证和过滤请求参数
            valid_request_kwargs = validate_request_kwargs(request_kwargs)
            
            # 创建请求对象
            logger.debug(f"Request 参数：{valid_request_kwargs}")
            request = Request(**valid_request_kwargs)
            
            # 创建 Bot 对象
            bot = telegram.Bot(token=token, request=request)
            
            # 确保没有活动的 webhook（webhook 会阻止轮询工作）
            if monitor_telegram_webhook(bot):
                logger.warning("发现活动的 webhook 配置，正在尝试清除...")
                clear_webhook(bot)
            
            # 测试连接
            logger.info("正在测试与 Telegram API 的连接...")
            bot_info = bot.get_me()
            logger.info(f"成功连接到 Telegram! 机器人名称：{bot_info.first_name}")
            
            # 创建并返回 updater
            updater = Updater(bot=bot)
            # 打印 updater 信息以确认初始化成功
            logger.info(f"成功创建 Updater 实例：{updater}")
            return updater
            
        except telegram.error.NetworkError as e:
            retry_count += 1
            err_msg = str(e)
            # 对一些特定错误提供更详细的诊断
            if "EOF occurred in violation of protocol" in err_msg:
                logger.warning(f"SSL 连接中断错误，可能是代理问题：{e}")
            elif "certificate verify failed" in err_msg:
                logger.warning(f"SSL 证书验证失败：{e}")
            else:
                logger.warning(f"网络错误：{e}")
                
            logger.warning(f"尝试重新连接 ({retry_count}/{max_retries})...")
            time.sleep(RETRY_DELAY * (retry_count ** 0.5))  # 逐渐增加等待时间
            
        except Exception as e:
            logger.error(f"初始化机器人时出错：{e}", exc_info=True)
            return None
    
    logger.error(f"在 {max_retries} 次尝试后仍无法连接到 Telegram")
    return None

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

def check_connection():
    """定期检查并维护连接"""
    global should_exit
    
    while not should_exit:
        try:
            # 测试与 Telegram API 的连接
            test_result = test_connectivity()
            if not test_result:
                logger.warning("检测到连接问题，尝试重新配置代理...")
                # 重新配置代理
                configure_proxy_for_telegram()
        except Exception as e:
            logger.error(f"连接检查时出错：{e}")
        
        # 等待下次检查
        time.sleep(connection_check_interval)

def signal_handler(sig, frame):
    """处理进程信号，优雅退出"""
    global should_exit
    logger.info("接收到中断信号，准备停止机器人...")
    should_exit = True

def main():
    """主函数，启动机器人"""
    logger.info("启动 TG-Notion 机器人...")
    
    # 加载环境变量
    load_dotenv()
    
    # 确认配置
    token = TELEGRAM_BOT_TOKEN 
    if not token:
        logger.error("错误：未设置 Telegram 机器人令牌")
        return 1
    
    if not ALLOWED_USER_IDS:
        logger.warning("警告：未设置允许的用户 ID，任何人都可以访问机器人")
    
    # 获取环境变量中的 SSL 证书验证设置
    disable_ssl_verify = os.environ.get('DISABLE_TELEGRAM_SSL_VERIFY', 'False').lower() in ('true', '1', 't', 'yes')
    
    if disable_ssl_verify:
        logger.warning("警告：SSL 证书验证已禁用。这可能会导致安全风险。")
    
    # 初始化机器人
    updater = init_bot(token, disable_certificate_verification=disable_ssl_verify)
    
    if not updater:
        logger.error("无法初始化机器人，程序将退出")
        return 1
        
    # 注册命令处理程序
    updater = setup_telegram_bot(updater)
    
    # 设置定时任务
    schedule_weekly_report()
    
    # 在单独的线程中运行调度器
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # 启动连接检查线程
    if KEEP_ALIVE:
        logger.info("启动连接保活线程...")
        connection_thread = threading.Thread(target=check_connection)
        connection_thread.daemon = True
        connection_thread.start()
    
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动机器人
    try:
        logger.info("启动机器人轮询...")
        
        # 使用更优的轮询参数
        updater.start_polling(
            timeout=30,           # 长轮询连接超时秒数
            drop_pending_updates=True,  # 启动时删除待处理的更新
            allowed_updates=["message", "callback_query", "chat_member", "inline_query"],  # 仅接收这些类型的更新
            bootstrap_retries=5,  # 重试连接次数
        )
        
        logger.info("机器人已成功启动，正在监听消息")
        # 等待，直到收到停止信号
        updater.idle()
    except Exception as e:
        logger.error(f"启动机器人时发生错误：{e}", exc_info=True)
        return 1
    
    logger.info("机器人已停止")
    return 0

# 启动程序
if __name__ == "__main__":
    sys.exit(main())
