from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
import os
import urllib3
import warnings
from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS

# 尽早导入并使用 SSL 配置
from utils.ssl_helper import configure_ssl_verification

# 禁用不安全请求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 设置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加自定义警告记录
if os.environ.get('DISABLE_TELEGRAM_SSL_VERIFY', 'False').lower() in ('true', '1', 't', 'yes'):
    logging.warning("SSL 证书验证已禁用。这可能存在安全风险，仅建议在特殊网络环境中使用。")

def error_handler(update, context):
    """处理 Telegram 机器人运行中的错误"""
    # 日志记录错误详情
    logger.error(f"更新 {update} 导致错误：{context.error}")
    
    # 如果可能，向用户发送错误通知
    if update and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"抱歉，处理您的请求时发生了错误。错误已被记录，我们会尽快解决。"
        )

def setup_telegram_bot(updater=None):
    """设置并启动 Telegram 机器人"""
    # 如果已提供 updater，则使用它
    if updater:
        dispatcher = updater.dispatcher
        logger.info("使用已初始化的 updater 实例")
    else:
        # 设置更长的超时时间和重试连接逻辑
        request_kwargs = {
            'connect_timeout': 30.0,  # 连接超时时间
            'read_timeout': 30.0,     # 读取超时时间
            'con_pool_size': 10,      # 连接池大小
        }
        
        # 检查并添加代理设置
        proxy_url = os.environ.get('https_proxy') or os.environ.get('http_proxy') or os.environ.get('all_proxy')
        if proxy_url and proxy_url.strip():
            logger.info(f"Telegram 服务使用代理：{proxy_url}")
            request_kwargs['proxy_url'] = proxy_url
            
            # 设置 urllib3 代理参数
            urllib3_kwargs = {
                'timeout': 30
            }
            
            # 检查是否需要禁用证书验证
            if os.environ.get('DISABLE_TELEGRAM_SSL_VERIFY', 'False').lower() in ('true', '1', 't', 'yes'):
                urllib3_kwargs['cert_reqs'] = 'CERT_NONE'
                logger.info("Telegram 服务已禁用 SSL 证书验证")
            
            # 设置代理参数
            request_kwargs['urllib3_proxy_kwargs'] = urllib3_kwargs
        
        # 创建 Updater 并提供网络设置
        updater = Updater(TELEGRAM_BOT_TOKEN, request_kwargs=request_kwargs)
        dispatcher = updater.dispatcher
    
    # 导入处理函数
    from .handlers.command_handlers import start, help_command, weekly_report_command
    from .handlers.message_handlers import process_message, process_document
    from handlers.paper_handlers import list_collections, sync_papers_by_count, sync_papers_by_days
    
    # 创建用户过滤器
    user_filter = Filters.user(user_id=ALLOWED_USER_IDS) if ALLOWED_USER_IDS else None
    
    # 注册处理程序
    dispatcher.add_handler(CommandHandler("start", start, filters=user_filter))
    dispatcher.add_handler(CommandHandler("help", help_command, filters=user_filter))
    dispatcher.add_handler(CommandHandler("weekly", weekly_report_command, filters=user_filter))
    
    # 添加论文处理命令
    dispatcher.add_handler(CommandHandler("collections", list_collections, filters=user_filter))
    dispatcher.add_handler(CommandHandler("sync_papers", sync_papers_by_count, filters=user_filter))
    dispatcher.add_handler(CommandHandler("sync_days", sync_papers_by_days, filters=user_filter))
    
    # 添加消息处理器
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_message))
    dispatcher.add_handler(MessageHandler(Filters.photo, process_message))
    dispatcher.add_handler(MessageHandler(Filters.document, process_document))
    dispatcher.add_handler(MessageHandler(Filters.video, process_message))
    
    # 添加错误处理器
    dispatcher.add_error_handler(error_handler)
    logger.info("已添加命令和消息处理器")
    
    return updater
