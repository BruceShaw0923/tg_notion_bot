import re
from datetime import datetime
import logging
import requests
import os

logger = logging.getLogger(__name__)

def extract_url_from_text(text):
    """从文本中提取 URL"""
    if not text:
        return ""
    
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    urls = re.findall(url_pattern, text)
    return urls[0] if urls else ""

def format_datetime(dt):
    """格式化日期时间"""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)

def truncate_text(text, max_length=2000):
    """
    截断文本，确保不超过指定长度
    
    参数：
    text (str): 要截断的文本
    max_length (int): 最大允许长度
    
    返回：
    str: 截断后的文本
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # 尽量在句子结束处截断
    cutoff = max_length - 3  # 为 "..." 保留空间
    punctuation_positions = [
        text.rfind(". ", 0, cutoff),
        text.rfind("? ", 0, cutoff),
        text.rfind("! ", 0, cutoff),
        text.rfind("\n", 0, cutoff)
    ]
    
    best_position = max(punctuation_positions)
    
    # 如果没有找到好的断点，就在单词边界处截断
    if best_position == -1:
        best_position = text.rfind(" ", 0, cutoff)
    
    # 如果仍然没有找到，就直接在指定位置截断
    if best_position == -1:
        return text[:cutoff] + "..."
    
    return text[:best_position+1] + "..."

def is_url_only(text):
    """检查文本是否只包含 URL"""
    if not text:
        return False
    
    # 去除空白字符
    text = text.strip()
    
    # 使用正则表达式检查是否为纯 URL
    url_pattern = re.compile(r'^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+$')
    return bool(url_pattern.match(text))

def download_file(url, local_path=None):
    """
    下载文件到本地
    
    参数：
    url (str): 文件 URL
    local_path (str, optional): 保存路径，如果不提供则返回文件内容
    
    返回：
    bytes 或 str: 如果提供 local_path 则返回保存路径，否则返回文件内容
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        if local_path:
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            with open(local_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            return local_path
        else:
            return response.content
    
    except Exception as e:
        logger.error(f"下载文件时出错：{e}")
        raise

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
            if value and format_type in ["bold", "italic", "strikethrough", "underline", "code"]:
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
