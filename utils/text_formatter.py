import logging
import re

logger = logging.getLogger(__name__)

# MarkdownV2 需要转义的字符
MARKDOWN_V2_SPECIAL_CHARS = r"_*[]()~>#+-=|{}.!"


def escape_markdown_v2(text):
    """
    转义 MarkdownV2 格式中的特殊字符

    参数：
    text (str): 要转义的文本

    返回：
    str: 转义后的文本
    """
    if not text:
        return ""

    result = ""
    for char in text:
        if char in MARKDOWN_V2_SPECIAL_CHARS:
            result += f"\\{char}"
        else:
            result += char

    return result


def parse_message_entities(text, entities):
    """
    解析消息中的实体，提取格式化文本信息

    参数：
    text (str): 消息文本
    entities (list): MessageEntity 对象列表

    返回：
    dict: 包含提取的格式化信息（链接、格式等）
    """
    if not text or not entities:
        return {"text": text, "links": [], "format_entities": []}

    # 按照偏移量排序实体
    sorted_entities = sorted(entities, key=lambda e: e.offset)

    # 提取链接
    links = []
    format_entities = []

    for entity in sorted_entities:
        entity_text = text[entity.offset : entity.offset + entity.length]
        entity_type = entity.type

        if entity_type == "text_link" and hasattr(entity, "url"):
            # 文本链接，包含显示文本和 URL
            links.append(
                {
                    "text": entity_text,
                    "url": entity.url,
                    "offset": entity.offset,
                    "length": entity.length,
                }
            )
        elif entity_type == "url":
            # 纯 URL 链接
            links.append(
                {
                    "text": entity_text,
                    "url": entity_text,
                    "offset": entity.offset,
                    "length": entity.length,
                }
            )
        else:
            # 其他格式实体（粗体、斜体等）
            format_entities.append(
                {
                    "type": entity_type,
                    "text": entity_text,
                    "offset": entity.offset,
                    "length": entity.length,
                }
            )

    logger.debug(f"解析到 {len(links)} 个链接和 {len(format_entities)} 个格式实体")
    return {"text": text, "links": links, "format_entities": format_entities}


def format_for_notion(text):
    """
    处理 Telegram 格式化文本，转换为 Notion 可接受的 Markdown 格式

    参数：
    text (str): 可能包含格式标记的原始文本

    返回：
    str: 处理后适合 Notion 存储的文本
    """
    if not text:
        return ""

    # 由于已经使用 MarkdownV2 解析模式，文本可能已经包含格式标记
    # 这里我们主要处理已经解析的格式化文本

    # 保留原始格式标记，因为这些格式 Notion 也能理解
    return text


def extract_urls_from_entities(text, entities):
    """
    从消息实体中提取所有 URL

    参数：
    text (str): 消息文本
    entities (list): MessageEntity 对象列表

    返回：
    list: 提取的 URL 列表
    """
    urls = []
    if not text or not entities:
        return urls

    for entity in entities:
        if entity.type == "url":
            # 直接 URL
            url = text[entity.offset : entity.offset + entity.length]
            if url not in urls:
                urls.append(url)
        elif entity.type == "text_link" and hasattr(entity, "url"):
            # 文本链接
            if entity.url not in urls:
                urls.append(entity.url)

    # 如果没有通过实体找到 URL，尝试使用正则表达式
    if not urls:
        urls = extract_urls_from_text(text)

    return urls


def extract_urls_from_text(text):
    """
    从文本中提取所有 URL

    参数：
    text (str): 可能包含 URL 的文本

    返回：
    list: 提取的 URL 列表
    """
    # 匹配标准 URL
    url_pattern = r"https?://[^\s\)\]\"\']+(?:\.[^\s\)\]\"\']+)+"

    # 找到所有 URL
    urls = re.findall(url_pattern, text)

    # 去重
    unique_urls = []
    for url in urls:
        if url not in unique_urls:
            unique_urls.append(url)

    return unique_urls
