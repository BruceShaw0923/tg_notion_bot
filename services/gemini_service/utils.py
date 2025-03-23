"""
工具函数模块

提供 Gemini 服务所需的各种辅助函数
"""

import logging

logger = logging.getLogger(__name__)


def extract_property_text(entry, property_name, field_type):
    """
    从 Notion 条目中提取文本属性

    参数：
    entry (dict): Notion 页面对象
    property_name (str): 属性名称
    field_type (str): 字段类型，如 'title' 或 'rich_text'

    返回：
    str: 提取的文本
    """
    if property_name not in entry["properties"]:
        return ""

    prop = entry["properties"][property_name]

    if field_type == "title" and prop.get("title"):
        text_objects = prop["title"]
        if text_objects and "plain_text" in text_objects[0]:
            return text_objects[0]["plain_text"]
        elif (
            text_objects
            and "text" in text_objects[0]
            and "content" in text_objects[0]["text"]
        ):
            return text_objects[0]["text"]["content"]

    elif field_type == "rich_text" and prop.get("rich_text"):
        text_objects = prop["rich_text"]
        if text_objects and "plain_text" in text_objects[0]:
            return text_objects[0]["plain_text"]
        elif (
            text_objects
            and "text" in text_objects[0]
            and "content" in text_objects[0]["text"]
        ):
            return text_objects[0]["text"]["content"]

    return ""


def extract_multi_select(entry, property_name):
    """
    从 Notion 条目中提取多选项属性

    参数：
    entry (dict): Notion 页面对象
    property_name (str): 属性名称

    返回：
    list: 多选项值列表
    """
    if property_name not in entry["properties"]:
        return []

    prop = entry["properties"][property_name]

    if prop.get("multi_select"):
        return [item.get("name", "") for item in prop["multi_select"] if "name" in item]

    return []


def extract_date(entry, property_name):
    """
    从 Notion 条目中提取日期属性

    参数：
    entry (dict): Notion 页面对象
    property_name (str): 属性名称

    返回：
    str: 日期字符串
    """
    if property_name not in entry["properties"]:
        return ""

    prop = entry["properties"][property_name]

    if prop.get("date") and prop["date"].get("start"):
        return prop["date"]["start"]

    return ""


def extract_url(entry, property_name):
    """
    从 Notion 条目中提取 URL 属性

    参数：
    entry (dict): Notion 页面对象
    property_name (str): 属性名称

    返回：
    str: URL 字符串
    """
    if property_name not in entry["properties"]:
        return ""

    prop = entry["properties"][property_name]

    if prop.get("url"):
        return prop["url"]

    return ""
