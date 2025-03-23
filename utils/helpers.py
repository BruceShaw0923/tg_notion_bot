import logging
import os
import re
import tempfile
from datetime import datetime
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def truncate_text(text, max_length=100):
    """截断文本至指定长度"""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def extract_url_from_text(text):
    """
    从文本中提取第一个 URL

    参数：
    text (str): 要分析的文本

    返回：
    str: 提取的 URL 或空字符串
    """
    urls = extract_all_urls_from_text(text)
    return urls[0] if urls else ""


def extract_all_urls_from_text(text):
    """
    从文本中提取所有 URL，包括括号内的 URL 和 Telegram 格式化链接

    参数：
    text (str): 要分析的文本

    返回：
    list: 提取的 URL 列表
    """

    # 使用多个正则表达式模式
    # 1. 标准 URL 模式
    standard_url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

    # 2. 括号内 URL 模式 - 特别匹配 (http://example.com) 格式
    bracketed_url_pattern = r"\((http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)\)"

    # 3. Telegram/Markdown 格式化链接 - [文本](URL)
    formatted_link_pattern = r"\[.+?\]\((http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)\)"

    # 提取各种格式的 URLs
    standard_urls = re.findall(standard_url_pattern, text)
    bracketed_urls = re.findall(bracketed_url_pattern, text)
    formatted_urls = re.findall(formatted_link_pattern, text)

    # 合并结果，确保所有 URL 都被识别
    all_urls = standard_urls + bracketed_urls + formatted_urls

    # 去重
    unique_urls = list(dict.fromkeys(all_urls))

    # 清理 URL，移除可能的后缀标点
    cleaned_urls = []
    for url in unique_urls:
        # 移除 URL 末尾的标点符号
        while url and url[-1] in ".,;:?!":
            url = url[:-1]
        cleaned_urls.append(url)

    return cleaned_urls


def format_datetime(dt):
    """格式化日期时间"""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def is_url_only(text):
    """
    检查文本是否只包含 URL（可能包含在括号内）

    参数：
    text (str): 要检查的文本

    返回：
    bool: 如果文本仅为 URL 则为 True
    """

    # 去除空白字符
    text = text.strip()

    # 检查是否是标准 URL
    standard_url_pattern = r"^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+$"

    # 检查是否是括号内 URL
    bracketed_url_pattern = r"^\((http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)\)$"

    is_standard_url = bool(re.match(standard_url_pattern, text))
    bracketed_match = re.match(bracketed_url_pattern, text)

    # 如果是括号内 URL，返回提取的 URL
    if bracketed_match:
        return True

    return is_standard_url


def download_file(url, file_extension=None):
    """从 URL 下载文件到临时位置

    参数：
    url (str): 文件 URL
    file_extension (str, optional): 文件扩展名，如'.pdf'

    返回：
    tuple: (本地文件路径，文件大小) 或 (None, 0)
    """
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            # 获取文件大小
            file_size = int(response.headers.get("content-length", 0))

            # 确定文件扩展名
            if not file_extension:
                # 尝试从 URL 中获取扩展名
                parsed_url = urlparse(url)
                path = parsed_url.path
                ext = os.path.splitext(path)[1]
                if ext:
                    file_extension = ext
                else:
                    # 尝试从 Content-Type 获取扩展名
                    content_type = response.headers.get("content-type", "")
                    if "pdf" in content_type:
                        file_extension = ".pdf"
                    elif "image" in content_type:
                        file_extension = ".jpg"  # 默认图片扩展名
                    else:
                        file_extension = ""

            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(suffix=file_extension)
            os.close(fd)

            # 写入文件内容
            with open(temp_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            logger.info(f"文件已下载到：{temp_path}")
            return temp_path, file_size
        else:
            logger.error(f"下载失败，状态码：{response.status_code}")
            return None, 0
    except Exception as e:
        logger.error(f"下载文件时出错：{e}")
        return None, 0


def format_notion_text(text, formatting=None):
    """
    格式化文本以符合 Notion API 格式

    参数：
    text (str): 要格式化的文本
    formatting (dict, optional): 格式化选项，如 {"bold": True, "italic": False, "code": False}

    返回：
    dict: 格式化后的 Notion 文本对象
    """
    text_obj = {"text": {"content": text}}

    if formatting:
        for format_type, value in formatting.items():
            if value and format_type in [
                "bold",
                "italic",
                "strikethrough",
                "underline",
                "code",
            ]:
                text_obj[format_type] = value

    return text_obj


def extract_tags_from_categories(content, categories):
    """
    从预定义类别中提取标签

    参数：
    content (str): 文本内容
    categories (list): 预定义类别列表

    返回：
    list: 匹配的类别列表
    """
    matched_categories = []
    content_lower = content.lower()

    for category in categories:
        # 简单匹配，实际应用中可能需要更复杂的匹配逻辑
        if category.lower() in content_lower:
            matched_categories.append(category)

    return matched_categories
