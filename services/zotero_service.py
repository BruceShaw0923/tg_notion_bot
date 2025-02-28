import requests
import tempfile
import os
import time
import logging
from datetime import datetime, timedelta
from config import ZOTERO_API_KEY, ZOTERO_USER_ID
from urllib.parse import urlparse, unquote
from dateutil.parser import parse
import pytz

logger = logging.getLogger(__name__)

# Zotero API 基础 URL
API_BASE_URL = "https://api.zotero.org"

def get_headers():
    """
    获取 Zotero API 请求头
    """
    return {
        "Zotero-API-Key": ZOTERO_API_KEY,
        "Zotero-API-Version": "3"
    }

def get_recent_items_by_date_range(days=7):
    """
    使用替代方法获取最近几天添加或修改的条目
    
    参数：
    days (int): 最近几天的时间范围
    
    返回：
    list: 条目列表
    """
    if not ZOTERO_API_KEY or not ZOTERO_USER_ID:
        logger.error("未配置 Zotero API 密钥或用户 ID")
        return []
    
    # 计算时间范围 - 使用带时区的 datetime
    end_date = datetime.now(pytz.UTC)  
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"获取 {start_date.isoformat()} 到 {end_date.isoformat()} 期间添加的条目")
    
    # 不使用 since 参数
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/items/top"
    params = {
        "format": "json",
        "limit": 100,
        "sort": "dateAdded",
        "direction": "desc"
    }
    
    try:
        items = []
        while url:
            response = requests.get(url, params=params, headers=get_headers())
            
            if response.status_code != 200:
                logger.error(f"API 请求失败：{response.status_code} - {response.text}")
                response.raise_for_status()
            
            batch_items = response.json()
            
            # 根据添加日期过滤
            for item in batch_items:
                try:
                    date_str = item['data'].get('dateAdded', '')
                    if not date_str:
                        continue
                        
                    # 解析日期并确保它有时区信息
                    date_added = parse(date_str)
                    
                    # 如果解析出的日期没有时区信息，则添加 UTC 时区
                    if date_added.tzinfo is None:
                        date_added = date_added.replace(tzinfo=pytz.UTC)
                    
                    # 现在可以安全地比较日期，因为两者都有时区信息
                    if start_date <= date_added <= end_date:
                        items.append(item)
                        
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"解析条目日期时出错：{e}, 日期字符串：{date_str if 'date_str' in locals() else 'unknown'}")
            
            logger.info(f"已获取 {len(items)} 条符合日期条件的条目")
            
            # 处理分页
            links = response.links if hasattr(response, 'links') else {}
            next_url = links.get('next', {}).get('url')
            if next_url:
                url = next_url
                params = None
            else:
                url = None
                
            # 避免过快请求
            time.sleep(0.5)
        
        # 获取子条目
        for item in items[:]:
            item_key = item.get('data', {}).get('key')
            if item_key:
                child_items = get_item_attachments(item_key)
                # 将父条目信息添加到子条目中
                for child in child_items:
                    child['parentItem'] = item
                    items.append(child)
        
        return items
    
    except Exception as e:
        logger.error(f"获取 Zotero 条目时出错：{e}")
        return []

def get_recent_items(days=7, format="json"):
    """
    获取最近几天添加或修改的条目
    
    参数：
    days (int): 最近几天的时间范围
    format (str): 返回格式，默认为 JSON
    
    返回：
    list: 条目列表
    """
    if not ZOTERO_API_KEY or not ZOTERO_USER_ID:
        logger.error("未配置 Zotero API 密钥或用户 ID")
        return []
    
    # 使用 UTC 时间避免时区问题
    current_time = datetime.utcnow()
    since_date = current_time - timedelta(days=days)
    
    # 检查日期是否有效
    if since_date > current_time:
        logger.error(f"计算的 since_date ({since_date.isoformat()}) 在当前时间之后，修正为当前时间减去 {days} 天")
        since_date = current_time - timedelta(days=days)
    
    # 格式化为 ISO 8601 UTC 格式
    since_timestamp = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    logger.info(f"获取自 {since_timestamp} 以来的条目（当前 UTC 时间：{current_time.strftime('%Y-%m-%dT%H:%M:%SZ')}）")
    
    # 构建 API 请求 URL
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/items"
    params = {
        "format": format,
        "limit": 50,
        "since": since_timestamp,
        "sort": "dateAdded",
        "direction": "desc"
    }
    
    try:
        # 显示完整请求详情以便调试
        logger.debug(f"Zotero API 请求：{url}?{'&'.join(f'{k}={v}' for k, v in params.items())}")
        
        response = requests.get(url, params=params, headers=get_headers())
        
        # 记录请求信息用于调试
        if response.status_code != 200:
            logger.error(f"API 请求失败：{response.status_code} - {response.text}")
            logger.error(f"请求 URL：{response.url}")
            response.raise_for_status()
        
        items = response.json()
        logger.info(f"从 Zotero 获取到 {len(items)} 条最近添加/修改的条目")
        return items
    
    except Exception as e:
        logger.error(f"获取 Zotero 条目时出错：{e}")
        return []

def get_item_attachments(item_key):
    """
    获取特定条目的附件列表
    
    参数：
    item_key (str): 条目的唯一标识
    
    返回：
    list: 附件列表
    """
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/items/{item_key}/children"
    params = {"format": "json"}
    
    try:
        response = requests.get(url, params=params, headers=get_headers())
        response.raise_for_status()
        
        attachments = response.json()
        return attachments
    
    except Exception as e:
        logger.error(f"获取条目 {item_key} 的附件时出错：{e}")
        return []

def get_pdf_attachments(days=7):
    """
    获取最近添加的 PDF 附件
    
    参数：
    days (int): 最近几天的范围
    
    返回：
    list: PDF 附件信息列表
    """
    # 使用新的函数获取条目
    items = get_recent_items_by_date_range(days)
    pdf_attachments = []
    
    # 直接检查所有条目是否为 PDF 附件
    for item in items:
        item_data = item.get('data', {})
        item_type = item_data.get('itemType')
        
        # 如果是 PDF 附件，直接添加
        if item_type == 'attachment' and item_data.get('contentType') == 'application/pdf':
            pdf_attachments.append(item)
    
    logger.info(f"找到 {len(pdf_attachments)} 个 PDF 附件")
    return pdf_attachments

def download_attachment_file(attachment):
    """
    下载 PDF 附件文件
    
    参数：
    attachment (dict): 附件信息
    
    返回：
    tuple: (本地文件路径，文件名称，文献元数据)
    """
    # 提取文件信息
    attachment_data = attachment.get('data', {})
    key = attachment_data.get('key')
    filename = attachment_data.get('filename', 'unknown.pdf')
    
    # 在下载前检查附件类型和链接模式
    linkMode = attachment_data.get('linkMode')
    
    # 如果是链接附件（非存储附件），尝试获取直接 URL
    if linkMode == 'linked_url' or linkMode == 'imported_url':
        logger.warning(f"附件 {key} 是链接文件而非存储文件，尝试从原始 URL 下载")
        try:
            # 从附件 URL 字段获取链接
            url = attachment_data.get('url')
            if not url:
                logger.error(f"附件 {key} 未提供 URL")
                return None, filename, {}
            
            # 下载链接文件
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                os.close(fd)
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"成功从原始 URL 下载文件：{filename} 到 {temp_path}")
                
                # 尝试获取父条目的元数据
                parent_item = attachment.get('parentItem', {})
                parent_data = parent_item.get('data', {}) if parent_item else {}
                
                # 如果有父条目，获取更完整的元数据
                if parent_item and parent_data.get('key'):
                    parent_key = parent_data.get('key')
                    complete_metadata = get_item_metadata(parent_key)
                    if complete_metadata:
                        parent_data = complete_metadata
                
                # 构建元数据
                metadata = {
                    'title': parent_data.get('title', filename),
                    'creators': parent_data.get('creators', []),
                    'abstractNote': parent_data.get('abstractNote', ''),
                    'publicationTitle': parent_data.get('publicationTitle', ''),
                    'date': parent_data.get('date', ''),
                    'DOI': parent_data.get('DOI', ''),
                    'url': url,  # 使用原始 URL
                    'tags': parent_data.get('tags', []),
                    'zotero_key': parent_data.get('key', '') or attachment_data.get('key', ''),
                    'itemType': parent_data.get('itemType', ''),
                    'journal': parent_data.get('journalAbbreviation', ''),
                    'volume': parent_data.get('volume', ''),
                    'issue': parent_data.get('issue', ''),
                    'pages': parent_data.get('pages', ''),
                    'publisher': parent_data.get('publisher', '')
                }
                
                return temp_path, filename, metadata
            else:
                logger.error(f"从原始 URL 下载附件 {key} 失败：{response.status_code}")
                return None, filename, {}
        except Exception as e:
            logger.error(f"尝试从原始 URL 下载附件 {key} 时出错：{e}")
            return None, filename, {}
    
    # 链接文件模式检查
    if linkMode not in ['imported_file', 'embedded_image', None]:
        logger.error(f"附件 {key} 使用不支持的链接模式：{linkMode}")
        return None, filename, {}
    
    # 尝试获取父条目的元数据
    parent_item = attachment.get('parentItem', {})
    parent_data = parent_item.get('data', {}) if parent_item else {}
    
    # 如果有父条目，获取更完整的元数据
    if parent_item and parent_data.get('key'):
        parent_key = parent_data.get('key')
        complete_metadata = get_item_metadata(parent_key)
        if complete_metadata:
            parent_data = complete_metadata
    
    # 构建元数据
    metadata = {
        'title': parent_data.get('title', filename),
        'creators': parent_data.get('creators', []),
        'abstractNote': parent_data.get('abstractNote', ''),
        'publicationTitle': parent_data.get('publicationTitle', ''),
        'date': parent_data.get('date', ''),
        'DOI': parent_data.get('DOI', ''),
        'url': parent_data.get('url', ''),
        'tags': parent_data.get('tags', []),
        'zotero_key': parent_data.get('key', '') or attachment_data.get('key', ''),
        'itemType': parent_data.get('itemType', ''),
        'journal': parent_data.get('journalAbbreviation', ''),
        'volume': parent_data.get('volume', ''),
        'issue': parent_data.get('issue', ''),
        'pages': parent_data.get('pages', ''),
        'publisher': parent_data.get('publisher', '')
    }
    
    # 构建下载 URL
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/items/{key}/file"
    
    try:
        # 先检查附件是否可下载
        check_response = requests.head(url, headers=get_headers())
        if check_response.status_code != 200:
            logger.error(f"附件 {key} 不可下载，状态码：{check_response.status_code}")
            logger.error("这可能是因为：1) 文件不是存储在 Zotero 服务器上，2) API 密钥权限不足，或 3) 文件已被删除")
            
            # 尝试获取其他下载方式
            alt_url = attachment_data.get('url')
            if alt_url:
                logger.info(f"尝试从替代 URL 下载：{alt_url}")
                try:
                    alt_response = requests.get(alt_url, stream=True, timeout=30)
                    if alt_response.status_code == 200:
                        # 下载成功
                        fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                        os.close(fd)
                        
                        with open(temp_path, 'wb') as f:
                            for chunk in alt_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        logger.info(f"成功从替代 URL 下载文件：{filename} 到 {temp_path}")
                        return temp_path, filename, metadata
                except Exception as alt_e:
                    logger.error(f"从替代 URL 下载失败：{alt_e}")
            
            # 如果没有替代下载方式或替代下载失败，则尝试使用元数据中的 DOI 或 URL
            if metadata.get('DOI'):
                logger.info(f"提供 DOI 链接作为替代：{metadata.get('DOI')}")
                metadata['url'] = f"https://doi.org/{metadata.get('DOI')}"
            elif metadata.get('url'):
                logger.info(f"使用元数据中的 URL 作为替代：{metadata.get('url')}")
            
            # 返回空路径但保留元数据，这样即使无法下载文件也能保存元数据
            return None, filename, metadata
        
        # 如果检查通过，发送请求获取文件
        response = requests.get(url, headers=get_headers(), stream=True)
        response.raise_for_status()
        
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        
        # 写入文件内容
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"成功下载文件：{filename} 到 {temp_path}")
        return temp_path, filename, metadata
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"文件 {key} 未找到，这可能是因为：1) 该文件是链接附件而非存储附件，2) API 密钥权限不足")
        else:
            logger.error(f"下载附件 {key} 时出错：{e}")
        
        # 尝试直接从 PDF URL 下载（如果有）
        pdf_url = attachment_data.get('url')
        if pdf_url and pdf_url.lower().endswith('.pdf'):
            try:
                logger.info(f"尝试直接从 URL 下载 PDF：{pdf_url}")
                direct_response = requests.get(pdf_url, stream=True, timeout=30)
                if direct_response.status_code == 200:
                    fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                    os.close(fd)
                    
                    with open(temp_path, 'wb') as f:
                        for chunk in direct_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"成功从直接 URL 下载文件：{filename} 到 {temp_path}")
                    metadata['url'] = pdf_url  # 更新 URL
                    return temp_path, filename, metadata
            except Exception as direct_e:
                logger.error(f"直接下载失败：{direct_e}")
        
        return None, filename, metadata
    
    except Exception as e:
        logger.error(f"下载附件 {key} 时出错：{e}")
        return None, filename, metadata

def get_item_metadata(item_key):
    """
    获取条目的详细元数据
    
    参数：
    item_key (str): 条目的唯一标识
    
    返回：
    dict: 条目元数据
    """
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/items/{item_key}"
    params = {"format": "json"}
    
    try:
        response = requests.get(url, params=params, headers=get_headers())
        response.raise_for_status()
        
        item_data = response.json()
        return item_data.get('data', {})
    
    except Exception as e:
        logger.error(f"获取条目 {item_key} 的元数据时出错：{e}")
        return {}

def sync_recent_pdfs(days=7, collection_id=None):
    """
    同步最近添加的 PDF 文件
    
    参数：
    days (int): 最近几天的范围
    collection_id (str, optional): 特定集合的 ID，如果提供则只同步该集合
    
    返回：
    list: 处理的文件信息列表 [(路径，文件名，元数据)]
    """
    # 确保 days 参数有效
    if not isinstance(days, int) or days <= 0:
        logger.warning(f"无效的 days 参数：{days}，使用默认值 7")
        days = 7
    
    # 如果指定了集合 ID，先验证集合是否存在
    if collection_id:
        if collection_exists(collection_id):
            logger.info(f"同步集合 {collection_id} 中最近 {days} 天添加的 PDF")
            return sync_collection_pdfs(collection_id, days)
        else:
            logger.error(f"集合 {collection_id} 不存在或无法访问")
            return []
    
    # 否则，使用默认文件夹 ID（如果配置了的话）
    from config import ZOTERO_FOLDER_ID
    if ZOTERO_FOLDER_ID:
        if collection_exists(ZOTERO_FOLDER_ID):
            logger.info(f"使用默认集合 {ZOTERO_FOLDER_ID} 同步最近 {days} 天添加的 PDF")
            return sync_collection_pdfs(ZOTERO_FOLDER_ID, days)
        else:
            logger.error(f"默认集合 {ZOTERO_FOLDER_ID} 不存在或无法访问")
    
    # 如果没有有效的集合 ID，同步所有最近的 PDF
    logger.info(f"同步所有最近 {days} 天添加的 PDF")
    pdf_attachments = get_pdf_attachments(days)
    
    # 筛选重复的 PDF (基于文件名)
    seen_filenames = set()
    unique_attachments = []
    
    for attachment in pdf_attachments:
        filename = attachment.get('data', {}).get('filename', '')
        if filename and filename not in seen_filenames:
            seen_filenames.add(filename)
            unique_attachments.append(attachment)
    
    # 下载 PDF 文件
    results = []
    for attachment in unique_attachments:
        pdf_path, filename, metadata = download_attachment_file(attachment)
        # 即使 pdf_path 为 None，也将元数据添加到结果中
        if pdf_path or metadata:
            results.append((pdf_path, filename, metadata))
            # 避免请求过于频繁
            time.sleep(1)
    
    logger.info(f"成功处理 {len(results)} 个条目")
    return results

def extract_zotero_pdf_url(url):
    """
    从 Zotero PDF URL 中提取条目 ID
    例如：zotero://select/library/items/A1B2C3D4
    
    参数：
    url (str): Zotero URL
    
    返回：
    str: 条目 ID，如果无法解析则返回 None
    """
    if not url or not url.startswith('zotero://'):
        return None
    
    parsed = urlparse(url)
    path = unquote(parsed.path)
    
    # 尝试提取 ID
    parts = path.split('/')
    if len(parts) >= 4 and parts[-2] == 'items':
        return parts[-1]
    
    return None

def get_collections():
    """
    获取所有 Zotero 集合（文件夹）信息
    
    返回：
    list: 集合信息列表
    """
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/collections"
    params = {"format": "json"}
    
    try:
        response = requests.get(url, params=params, headers=get_headers())
        response.raise_for_status()
        
        collections = response.json()
        logger.info(f"获取到 {len(collections)} 个 Zotero 集合")
        return collections
    
    except Exception as e:
        logger.error(f"获取 Zotero 集合时出错：{e}")
        return []

def get_collection_items(collection_id, days=7):
    """
    获取特定集合中的最近添加的条目
    
    参数：
    collection_id (str): 集合 ID
    days (int): 最近几天的时间范围
    
    返回：
    list: 条目列表
    """
    # 先检查集合是否存在
    if not collection_exists(collection_id):
        logger.error(f"集合 {collection_id} 不存在或无法访问")
        return []
    
    # 修复时间计算问题 - 确保使用正确的时区和有效的过去日期
    # 使用 UTC 时间以避免时区问题
    current_time = datetime.utcnow()
    since_date = current_time - timedelta(days=days)
    
    # 检查日期是否有效（不在未来）
    if since_date > current_time:
        logger.error(f"计算的 since_date ({since_date.isoformat()}) 在当前时间之后，使用当前时间减去 {days} 天")
        since_date = current_time - timedelta(days=days)
    
    # 格式化为 ISO 8601 UTC 格式
    since_timestamp = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    logger.info(f"获取自 {since_timestamp} 以来的集合 {collection_id} 条目（当前 UTC 时间：{current_time.strftime('%Y-%m-%dT%H:%M:%SZ')}）")
    
    # 构建 API 请求 URL
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/collections/{collection_id}/items"
    params = {
        "format": "json",
        "limit": 50,
        "since": since_timestamp,
        "sort": "dateAdded",
        "direction": "desc"
    }
    
    try:
        # 显示完整请求详情以便调试
        request_url = f"{url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        logger.debug(f"Zotero API 请求：{request_url}")
        
        # 将 params 传递给 requests，而不是手动构建 URL，以确保正确的 URL 编码
        response = requests.get(url, params=params, headers=get_headers())
        
        # 如果出现错误，记录详细的请求信息
        if response.status_code != 200:
            logger.error(f"API 请求失败：{response.status_code} - {response.text}")
            logger.error(f"请求 URL：{response.url}")
            logger.error(f"请求头：{get_headers()}")
            response.raise_for_status()
        
        items = response.json()
        logger.info(f"从集合 {collection_id} 获取到 {len(items)} 条最近添加的条目")
        return items
    
    except requests.exceptions.HTTPError as e:
        # 提供更详细的错误信息
        error_msg = f"获取集合 {collection_id} 条目时出错：{e}"
        if hasattr(e, 'response') and e.response:
            error_msg += f"\n响应状态码：{e.response.status_code}"
            error_msg += f"\n响应内容：{e.response.text[:500]}"  # 限制响应内容长度
        logger.error(error_msg)
        return []
    except Exception as e:
        logger.error(f"获取集合 {collection_id} 条目时出错：{e}")
        return []

def collection_exists(collection_id):
    """
    检查集合是否存在且可访问
    
    参数：
    collection_id (str): 集合 ID
    
    返回：
    bool: 如果集合存在且可访问则返回 True
    """
    # 如果集合 ID 为空，返回 False
    if not collection_id or not collection_id.strip():
        return False
    
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/collections/{collection_id}"
    
    try:
        response = requests.get(url, headers=get_headers())
        return response.status_code == 200
    except:
        return False

def get_collection_items_by_date_range(collection_id, days=7):
    """
    使用替代方法获取特定集合中的最近添加的条目
    
    参数：
    collection_id (str): 集合 ID
    days (int): 最近几天的时间范围
    
    返回：
    list: 条目列表
    """
    # 检查集合是否存在
    if not collection_exists(collection_id):
        logger.error(f"集合 {collection_id} 不存在或无法访问")
        return []
    
    # 计算时间范围 - 确保所有日期都是 aware datetime (带有时区信息)
    end_date = datetime.now(pytz.UTC)  # 使用带时区的 datetime
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"获取 {start_date.isoformat()} 到 {end_date.isoformat()} 期间添加的条目")
    
    # 不使用 since 参数，而是通过客户端过滤
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/collections/{collection_id}/items/top"
    params = {
        "format": "json",
        "limit": 100,  # 增加限制以获取更多条目
        "sort": "dateAdded",
        "direction": "desc"
    }
    
    try:
        items = []
        while url:
            logger.debug(f"请求 URL: {url}")
            response = requests.get(url, params=params, headers=get_headers())
            
            if response.status_code != 200:
                logger.error(f"API 请求失败：{response.status_code} - {response.text}")
                logger.error(f"请求 URL：{response.url}")
                response.raise_for_status()
            
            # 提取数据
            batch_items = response.json()
            
            # 根据添加日期过滤
            for item in batch_items:
                try:
                    date_str = item['data'].get('dateAdded', '')
                    if not date_str:
                        continue
                        
                    # 解析日期并确保它有时区信息
                    date_added = parse(date_str)
                    
                    # 如果解析出的日期没有时区信息，则添加 UTC 时区
                    if date_added.tzinfo is None:
                        date_added = date_added.replace(tzinfo=pytz.UTC)
                    
                    # 现在可以安全地比较日期，因为两者都有时区信息
                    if start_date <= date_added <= end_date:
                        items.append(item)
                        
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"解析条目日期时出错：{e}, 日期字符串：{date_str if 'date_str' in locals() else 'unknown'}")
            
            logger.info(f"已获取 {len(items)} 条符合日期条件的条目")
            
            # 处理分页 - 检查是否有下一页
            links = response.links if hasattr(response, 'links') else {}
            next_url = links.get('next', {}).get('url')
            if next_url:
                url = next_url
                params = None  # 因为 next_url 已经包含了所有参数
            else:
                url = None
            
            # 避免过快请求
            time.sleep(0.5)
        
        # 获取子条目的 PDF 附件
        for item in items[:]:
            item_key = item.get('data', {}).get('key')
            if item_key:
                child_items = get_item_attachments(item_key)
                # 将父条目信息添加到子条目中
                for child in child_items:
                    child['parentItem'] = item
                    items.append(child)
        
        return items
    
    except Exception as e:
        logger.error(f"获取集合 {collection_id} 条目时出错：{e}")
        return []

def get_collection_pdf_attachments(collection_id, days=7):
    """
    获取特定集合中最近添加的 PDF 附件
    
    参数：
    collection_id (str): 集合 ID
    days (int): 最近几天的范围
    
    返回：
    list: PDF 附件信息列表
    """
    # 使用新的函数获取条目
    items = get_collection_items_by_date_range(collection_id, days)
    pdf_attachments = []
    
    # 直接检查所有条目是否为 PDF 附件
    for item in items:
        item_data = item.get('data', {})
        item_type = item_data.get('itemType')
        
        # 如果是 PDF 附件，直接添加
        if item_type == 'attachment' and item_data.get('contentType') == 'application/pdf':
            pdf_attachments.append(item)
    
    logger.info(f"在集合 {collection_id} 中找到 {len(pdf_attachments)} 个 PDF 附件")
    return pdf_attachments

def sync_collection_pdfs(collection_id, days=7):
    """
    同步特定集合中最近添加的 PDF 文件
    
    参数：
    collection_id (str): 集合 ID
    days (int): 最近几天的范围
    
    返回：
    list: 处理的文件信息列表 [(路径，文件名，元数据)]
    """
    pdf_attachments = get_collection_pdf_attachments(collection_id, days)
    
    # 筛选重复的 PDF (基于文件名)
    seen_filenames = set()
    unique_attachments = []
    
    for attachment in pdf_attachments:
        filename = attachment.get('data', {}).get('filename', '')
        if filename and filename not in seen_filenames:
            seen_filenames.add(filename)
            unique_attachments.append(attachment)
    
    # 下载 PDF 文件
    results = []
    for attachment in unique_attachments:
        pdf_path, filename, metadata = download_attachment_file(attachment)
        # 即使 pdf_path 为 None，也将元数据添加到结果中
        # 这样即使无法下载文件，也能将元数据添加到 Notion
        if pdf_path or metadata:
            results.append((pdf_path, filename, metadata))
            # 避免请求过于频繁
            time.sleep(1)
    
    logger.info(f"成功处理集合 {collection_id} 中的 {len(results)} 个条目")
    return results
