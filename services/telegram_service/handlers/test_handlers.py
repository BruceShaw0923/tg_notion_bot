import logging

from telegram import Update

# 配置日志
logger = logging.getLogger(__name__)


def handle_test_message(update: Update, parsed_content):
    """
    处理带有 #test 标签的消息，显示解析结果和实体信息

    参数：
    update (Update): 更新对象
    parsed_content (dict): 解析后的消息内容，包含文本和实体信息
    """
    logger.info("处理测试消息")

    # 提取聊天和消息信息
    chat_id = update.effective_chat.id
    message_id = update.message.message_id

    # 转发原消息
    update.message.reply_text(
        "📝 收到测试消息！以下是原始消息：", parse_mode=None
    )  # 禁用 Markdown 解析

    try:
        update.message.bot.forward_message(
            chat_id=chat_id, from_chat_id=chat_id, message_id=message_id
        )
    except Exception as e:
        logger.error(f"转发消息失败：{e}")
        update.message.reply_text(
            f"消息转发失败：{str(e)}", parse_mode=None
        )  # 禁用 Markdown 解析

    # 显示解析结果
    clean_text = parsed_content["text"].replace("#test", "").strip()

    # 构建实体信息报告
    entity_report = "解析到的格式实体：\n"

    # 报告链接
    if parsed_content["links"]:
        entity_report += "\n链接：\n"
        for i, link in enumerate(parsed_content["links"], 1):
            entity_report += f"{i}. 文本：'{link['text']}' → URL: {link['url']}\n"

    # 报告其他格式实体
    if parsed_content["format_entities"]:
        entity_report += "\n格式标记：\n"
        for i, entity in enumerate(parsed_content["format_entities"], 1):
            entity_report += f"{i}. 类型：{entity['type']}, 文本：'{entity['text']}'\n"

    # 如果没有实体
    if not parsed_content["links"] and not parsed_content["format_entities"]:
        entity_report += "未检测到任何格式化实体\n"

    # 发送解析报告
    update.message.reply_text(entity_report, parse_mode=None)  # 禁用 Markdown 解析

    # 显示处理后的纯文本内容
    update.message.reply_text(
        f"处理后的纯文本内容：\n\n{clean_text}",
        parse_mode=None,  # 禁用 Markdown 解析
    )

    return True
