"""
Zotero 条目模块 - 处理 Zotero 条目和元数据
"""

import logging
import os
import tempfile
import shutil
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .client import get_zotero_service

# 配置日志
logger = logging.getLogger(__name__)

def get_recent_items(collection_id=None, filter_type="count", value=5):
    """
    获取最近的条目，支持按数量或天数筛选
    
    参数：
        collection_id: 可选的 Zotero 收藏集 ID
        filter_type: 过滤类型，可以是"count"或"days"
        value: 对应过滤类型的值（篇数或天数）
        
    返回：
        最近的条目列表
    """
    service = get_zotero_service()
    try:
        if (filter_type == "count"):
            if collection_id:
                items = service.zot.collection_items(collection_id, limit=value)
            else:
                items = service.zot.items(limit=value)
        else:  # filter_type == "days"
            cutoff_date = datetime.now() - timedelta(days=value)
            if collection_id:
                items = service.zot.collection_items(collection_id)
            else:
                items = service.zot.items()
            items = [item for item in items 
                    if datetime.fromisoformat(item['data']['dateAdded'].replace('Z', '+00:00')) 
                    >= cutoff_date]
        return items
    except Exception as e:
        logger.error(f"Error getting recent items: {str(e)}")
        return []

def extract_metadata(item):
    """
    从 Zotero 条目中提取元数据
    
    参数：
        item: Zotero 条目数据
        
    返回：
        包含所有提取元数据的字典
    """
    service = get_zotero_service()
    data = item['data']
    
    # 提取基本元数据
    metadata = {
        'title': data.get('title', '未知标题'),
        'abstract': data.get('abstractNote', ''),
        'doi': data.get('DOI', ''),
        'url': data.get('url', ''),
        'date_added': data.get('dateAdded', ''),
        'item_type': data.get('itemType', ''),
        'authors': [],
        'publication': data.get('publicationTitle', ''),
        'date': data.get('date', '')[:4] if data.get('date') else '',
        'tags': [tag['tag'] for tag in data.get('tags', [])],
        'zotero_id': item['key'],
        'collections': data.get('collections', []),
        # 文件名信息将在后续处理中添加
        'attachment_info': [],
    }
    
    # 提取作者
    creators = data.get('creators', [])
    for creator in creators:
        if creator.get('creatorType') == 'author':
            name = []
            if creator.get('firstName'):
                name.append(creator.get('firstName', ''))
            if creator.get('lastName'):
                name.append(creator.get('lastName', ''))
            full_name = ' '.join(name).strip()
            if full_name:
                metadata['authors'].append(full_name)
    
    # 转换作者列表为字符串
    metadata['authors_text'] = ', '.join(metadata['authors'])
    
    return metadata

def get_pdf_attachment(item_key):
    """
    获取条目的 PDF 附件
    
    参数：
        item_key: Zotero 条目的唯一键
        
    返回：
        本地临时 PDF 文件路径，如果找不到则返回 None
    """
    service = get_zotero_service()
    try:
        # 获取条目
        item = service.zot.item(item_key)
        
        metadata = extract_metadata(item)
        logger.info(f"Processing paper: {metadata['title']}")
        # 获取条目的所有子条目 (附件)
        children = service.zot.children(item_key)
        
        pdf_attachments = []
        for child in children:
            child_data = child.get('data', {})
            
            # 只处理 PDF 附件
            if (child_data.get('itemType') == 'attachment' and 
                child_data.get('contentType') == 'application/pdf'):
                
                # 获取附件的文件名
                filename = child_data.get('filename', '')
                title = child_data.get('title', '')
                
                if filename or title:
                    pdf_attachments.append({
                        'key': child.get('key'),
                        'filename': filename or title,
                        'title': title
                    })
                    logger.info(f"Found PDF attachment: {filename or title}")
        
        if not pdf_attachments:
            logger.warning(f"No PDF attachments found for item {item_key}")
            return None
        
        # 优先使用第一个 PDF 附件
        attachment = pdf_attachments[0]
        filename = attachment['filename']
        
        # 确保文件名有.pdf 后缀
        if not filename.lower().endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        # 尝试在本地存储路径中查找文件
        source_path = os.path.join(service.pdf_storage_path, filename)
        logger.info(f"Looking for file at: {source_path}")
        if os.path.exists(source_path):
            logger.info(f"在本地找到 PDF: {source_path}")
            try:
                # 创建临时目录
                temp_dir = tempfile.mkdtemp()
                logger.info(f"创建临时目录：{temp_dir}")
                # 生成临时文件名 - 使用原始文件名
                target_path = os.path.join(temp_dir, os.path.basename(filename))
                # 使用 shutil.copy2 复制文件
                shutil.copy2(source_path, target_path)
                if os.path.exists(target_path):
                    logger.info(f"PDF 文件成功复制到：{target_path}")
                    return target_path
                else:
                    logger.error("PDF 文件复制失败")
            except Exception as e:
                logger.error(f"复制 PDF 文件时发生错误：{str(e)}")
        else:
            logger.warning(f"未在本地找到 PDF: {source_path}")
    except Exception as e:
        logger.error(f"获取 PDF 附件时出错：{str(e)}")
    
    return None
