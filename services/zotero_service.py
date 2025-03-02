"""
Zotero 服务：提供 Zotero API 相关功能，包括获取收藏集、同步论文到 Notion 等
"""

import logging
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from urllib.parse import urlparse, unquote

from pyzotero import zotero
import requests
from dotenv import load_dotenv

from config import ZOTERO_API_KEY, ZOTERO_USER_ID

# 修改导入方式，不再导入 NotionService 和 GeminiService 类
import services.notion_service as notion_service
import services.gemini_service as gemini_service

# 加载环境变量
load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

# 单例实例
_zotero_service_instance = None

class ZoteroService:
    """Zotero 服务类，处理与 Zotero API 的所有交互"""
    
    def __init__(self):
        """初始化 Zotero 服务"""
        # 从环境变量获取 Zotero API 配置
        user_id = os.getenv("ZOTERO_USER_ID")
        api_key = os.getenv("ZOTERO_API_KEY")
        library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")  # 默认为用户库
        
        # 检查配置完整性
        if not user_id or not api_key:
            raise ValueError("缺少 Zotero API 配置。请检查环境变量 ZOTERO_USER_ID 和 ZOTERO_API_KEY")
        
        # 初始化 Zotero API 客户端
        self.zot = zotero.Zotero(user_id, library_type, api_key)
        
        # 获取存储临时文件的目录
        self.temp_dir = os.getenv("TEMP_DIR", "/tmp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Zotero 本地存储路径
        self.zotero_storage_path = os.getenv("ZOTERO_STORAGE_PATH", "")
        os.makedirs(self.zotero_storage_path, exist_ok=True)
        
        # 获取直接本地存储路径
        self.zotero_local_path = os.getenv("ZOTERO_LOCAL_PATH", "")
        if self.zotero_local_path and os.path.exists(self.zotero_local_path):
            logger.info(f"使用 Zotero 本地路径：{self.zotero_local_path}")
        else:
            logger.warning(f"Zotero 本地路径不存在或未设置：{self.zotero_local_path}")
            
        # 添加常见的子目录名称列表，用于搜索
        self.common_subdirs = ["pdfs", "attachments", "storage"]
    
    def get_all_collections(self) -> List[Dict]:
        """
        获取所有收藏集
        
        返回：
            List[Dict]: 收藏集列表
        """
        try:
            collections = self.zot.collections()
            logger.info(f"成功获取 {len(collections)} 个收藏集")
            return collections
        except Exception as e:
            logger.error(f"获取收藏集时出错：{e}")
            raise
    
    def format_collection_list_for_telegram(self) -> str:
        """
        格式化收藏集列表，供 Telegram 显示
        
        返回：
            str: 格式化的收藏集列表文本
        """
        collections = self.get_all_collections()
        
        if not collections:
            return "未找到收藏集"
        
        result = "📚 Zotero 收藏集列表：\n\n"
        for coll in collections:
            result += f"• {coll['data']['name']} (ID: `{coll['data']['key']}`)\n"
        
        result += "\n使用方法：\n"
        result += "- 同步最新论文：`/sync_papers [收藏集 ID] [数量]`\n"
        result += "- 同步指定天数内的论文：`/sync_days [收藏集 ID] [天数]`"
        
        return result
    
    def get_recent_items(self, collection_id: Optional[str] = None, 
                          filter_type: str = "count", value: int = 5) -> List[Dict]:
        """
        获取最近的论文项目，支持按数量或天数筛选
        
        参数：
            collection_id: 收藏集 ID，如果为 None 则获取所有收藏集
            filter_type: 筛选类型，'count'表示按数量，'days'表示按天数
            value: 要获取的数量或天数
            
        返回：
            List[Dict]: 论文条目列表
        """
        try:
            if filter_type == "count":
                # 按数量获取最新论文
                sort_params = {
                    'sort': 'dateAdded',
                    'direction': 'desc',
                    'limit': value
                }
                
                # 根据是否提供收藏集 ID 选择获取方式
                if collection_id:
                    items = self.zot.collection_items(collection_id, **sort_params)
                else:
                    items = self.zot.items(**sort_params)
                
                # 过滤，只保留论文类型的条目
                papers = [item for item in items if item['data'].get('itemType') in 
                          ['journalArticle', 'preprint', 'book', 'conferencePaper']]
                
                logger.info(f"成功获取 {len(papers)} 篇最近添加的论文")
                return papers
                
            elif filter_type == "days":
                # 按天数范围获取论文
                target_date = datetime.now() - timedelta(days=value)
                target_date_str = target_date.strftime('%Y-%m-%d')
                
                query_params = {
                    'sort': 'dateAdded',
                    'direction': 'desc',
                    'limit': 100  # 设置一个较大的限制，可能需要分页处理
                }
                
                all_items = []
                start = 0
                
                while True:
                    # 根据是否提供收藏集 ID 选择获取方式
                    if collection_id:
                        items = self.zot.collection_items(collection_id, start=start, **query_params)
                    else:
                        items = self.zot.items(start=start, **query_params)
                    
                    if not items:
                        break
                        
                    # 过滤项目类型和日期
                    for item in items:
                        if item['data'].get('itemType') in ['journalArticle', 'preprint', 'book', 'conferencePaper']:
                            date_added = item['data'].get('dateAdded', '')
                            if date_added and date_added.split('T')[0] >= target_date_str:
                                all_items.append(item)
                            elif date_added and date_added.split('T')[0] < target_date_str:
                                # 由于已经按日期排序，如果找到早于目标日期的条目，可以停止查询
                                return all_items
                    
                    # 增加起始索引以获取下一页结果
                    start += len(items)
                    
                    # 避免过于频繁的 API 请求
                    if start > 0:
                        time.sleep(1)
                
                logger.info(f"成功获取 {len(all_items)} 篇最近 {value} 天内添加的论文")
                return all_items
            
            else:
                raise ValueError(f"不支持的筛选类型：{filter_type}")
                
        except Exception as e:
            logger.error(f"获取最近论文时出错：{e}")
            raise
    
    def extract_metadata(self, item: Dict) -> Dict:
        """
        从 Zotero 条目中提取元数据
        
        参数：
            item: Zotero 条目数据
            
        返回：
            Dict: 包含所有提取元数据的字典
        """
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
            'zotero_key': item['key'],
            'collections': data.get('collections', []),
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
    
    def get_pdf_attachment(self, item_key: str) -> Optional[str]:
        """
        获取论文的 PDF 附件
        
        参数：
            item_key: Zotero 条目的 key
            
        返回：
            Optional[str]: 下载的 PDF 文件路径，如果失败则返回 None
        """
        try:
            logger.info(f"开始获取条目 {item_key} 的 PDF 附件")
            # 获取附件
            attachments = self.zot.children(item_key)
            
            # 如果没有附件，直接返回 None
            if not attachments:
                logger.info(f"条目 {item_key} 没有附件")
                return None
            
            logger.info(f"条目 {item_key} 共找到 {len(attachments)} 个附件")
                
            # 查找 PDF 附件
            pdf_attachment = None
            filename = None
            pdf_filename = None
            
            for attachment in attachments:
                # 详细记录附件信息，便于调试
                attachment_data = attachment.get('data', {})
                content_type = attachment_data.get('contentType')
                link_mode = attachment_data.get('linkMode')
                
                if content_type == 'application/pdf':
                    pdf_attachment = attachment
                    
                    # 智能获取文件名 - 尝试多种可能的字段
                    filename = attachment_data.get('filename')
                    if not filename:
                        # 尝试从路径获取
                        path = attachment_data.get('path', '')
                        if path:
                            if path.startswith('file:///'):
                                path = unquote(path.replace('file://', ''))
                            filename = os.path.basename(path)
                            pdf_filename = path  # 保存完整路径
                        
                        # 尝试从 URL 获取
                        if not filename and attachment_data.get('url'):
                            url_path = urlparse(attachment_data.get('url', '')).path
                            if url_path and url_path.endswith('.pdf'):
                                filename = os.path.basename(url_path)
                        
                        # 尝试从标题获取
                        if not filename and attachment_data.get('title'):
                            filename = attachment_data.get('title')
                            if not filename.lower().endswith('.pdf'):
                                filename += '.pdf'
                    
                    logger.info(f"找到 PDF 附件：{attachment['key']}, 链接模式：{link_mode}, 文件名：{filename or '未知'}")
                    if pdf_filename:
                        logger.info(f"附件完整路径：{pdf_filename}")
                    logger.debug(f"附件完整数据：{attachment_data}")
                    break
            
            # 如果没有找到 PDF 附件，返回 None
            if not pdf_attachment:
                logger.info(f"条目 {item_key} 没有 PDF 附件")
                return None
            
            # 准备输出文件路径
            output_pdf_filename = f"{self.temp_dir}/{item_key}.pdf"
            
            # 如果有完整路径，直接尝试使用
            if pdf_filename and os.path.exists(pdf_filename) and os.path.isfile(pdf_filename):
                logger.info(f"尝试从完整路径获取 PDF: {pdf_filename}")
                with open(pdf_filename, 'rb') as src, open(output_pdf_filename, 'wb') as dst:
                    dst.write(src.read())
                logger.info(f"成功从完整路径获取 PDF: {pdf_filename}")
                return output_pdf_filename
            
            # 优先策略：如果有文件名，首先尝试从 ZOTERO_LOCAL_PATH 直接获取或进行广度优先搜索
            if filename:
                # 1. 先检查直接路径
                direct_local_paths = [
                    os.path.join(self.zotero_local_path, filename)
                ]
                
                # 2. 检查常见子目录
                for subdir in self.common_subdirs:
                    direct_local_paths.append(os.path.join(self.zotero_local_path, subdir, filename))
                
                # 尝试直接路径
                for path in direct_local_paths:
                    logger.info(f"尝试从路径获取 PDF: {path}")
                    if os.path.exists(path) and os.path.isfile(path):
                        with open(path, 'rb') as src, open(output_pdf_filename, 'wb') as dst:
                            dst.write(src.read())
                        logger.info(f"成功从路径获取 PDF: {path}")
                        return output_pdf_filename
                
                # 3. 进行广度优先搜索
                found_path = self._find_file_bfs(self.zotero_local_path, filename)
                if found_path:
                    with open(found_path, 'rb') as src, open(output_pdf_filename, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"通过广度优先搜索找到并复制 PDF: {found_path}")
                    return output_pdf_filename
            
            # 获取附件信息
            attachment_key = pdf_attachment['key']
            attachment_data = pdf_attachment['data']
            
            # 如果前面没有从直接路径找到，尝试其他方法
            # 尝试不同的下载方法
            download_methods = [
                self._get_from_direct_local_path,  # 先尝试从存储目录直接获取
                self._copy_from_local_path,
                self._download_from_original_url
            ]
            
            # 链接附件优先尝试从原始 URL 下载
            link_mode = attachment_data.get('linkMode')
            if link_mode in ['linked_url', 'imported_url']:
                url = attachment_data.get('url')
                if url:
                    logger.info(f"尝试从链接 URL 下载 PDF: {url[:60]}...")
                    if self._download_from_url(url, output_pdf_filename):
                        return output_pdf_filename
            
            # 尝试所有下载方法
            for method in download_methods:
                method_name = method.__name__
                logger.info(f"尝试使用 {method_name} 方法获取 PDF")
                
                # 对于直接获取方法，传递文件名和输出路径
                if method == self._get_from_direct_local_path:
                    if filename and method(filename, output_pdf_filename):
                        return output_pdf_filename
                # 其他方法使用原来的参数
                elif method(pdf_attachment, output_pdf_filename):
                    return output_pdf_filename
                    
            logger.warning(f"无法获取条目 {item_key} 的 PDF 附件，所有下载方法均失败")
            return None
                
        except Exception as e:
            logger.error(f"获取 PDF 附件时出错：{e}")
            return None
    
    def _find_file_bfs(self, root_dir: str, target_filename: str, max_depth: int = 4) -> Optional[str]:
        """
        使用广度优先搜索在目录中查找文件，增强对特殊字符的处理
        
        参数：
            root_dir: 起始目录
            target_filename: 要查找的文件名
            max_depth: 最大搜索深度，防止搜索过大的目录树
            
        返回：
            Optional[str]: 找到的文件路径，如果未找到则返回 None
        """
        if not os.path.exists(root_dir) or not os.path.isdir(root_dir):
            logger.warning(f"搜索根目录不存在或不是目录：{root_dir}")
            return None
            
        from collections import deque
        
        # 规范化目标文件名以处理 Unicode 和特殊字符
        target_filename = self._normalize_filename(target_filename)
        
        # 准备搜索队列，每个元素是 (路径，当前深度)
        queue = deque([(root_dir, 0)])
        visited = set()
        
        target_lower = target_filename.lower()
        logger.info(f"开始在 {root_dir} 中搜索文件：{target_filename}")
        
        # 获取文件名和扩展名
        target_base, target_ext = os.path.splitext(target_lower)
        
        # 创建简单的匹配模式，避免复杂的正则表达式
        # 使用单词边界和不区分大小写的匹配
        try:
            # 替换常见的特殊字符为通配符
            simple_base = target_base.replace(' ', '.{0,3}')  # 允许 0-3 个任意字符替代空格
            simple_base = re.sub(r'[,\.\-_]', '.{0,1}', simple_base)  # 允许 0-1 个任意字符替代分隔符
            
            # 创建安全的正则表达式模式
            pattern = re.compile(f".*{re.escape(simple_base)}.*{re.escape(target_ext)}$", re.IGNORECASE)
        except Exception as e:
            logger.warning(f"创建搜索模式时出错：{e}")
            # 如果正则表达式创建失败，使用简单的子字符串匹配
            pattern = None
        
        while queue:
            current_dir, depth = queue.popleft()
            
            if current_dir in visited or depth > max_depth:
                continue
                
            visited.add(current_dir)
            
            try:
                for item in os.listdir(current_dir):
                    full_path = os.path.join(current_dir, item)
                    
                    # 检查是否匹配目标文件（多种匹配策略）
                    if os.path.isfile(full_path):
                        normalized_item = self._normalize_filename(item)
                        item_lower = normalized_item.lower()
                        
                        # 策略 1: 精确匹配（不区分大小写）
                        if item_lower == target_lower:
                            logger.info(f"找到精确匹配文件：{full_path}")
                            return full_path
                        
                        # 策略 2: 扩展名匹配 + 基础名包含
                        item_base, item_ext = os.path.splitext(item_lower)
                        if item_ext.lower() == target_ext.lower() and target_base in item_base:
                            logger.info(f"找到基础名包含匹配文件：{full_path}")
                            return full_path
                        
                        # 策略 3: 模式匹配（如果正则表达式可用）
                        if pattern and pattern.match(item_lower):
                            logger.info(f"找到模式匹配文件：{full_path}")
                            return full_path
                    
                    # 将子目录添加到队列
                    if os.path.isdir(full_path) and depth < max_depth:
                        queue.append((full_path, depth + 1))
            except PermissionError:
                logger.warning(f"无权访问目录：{current_dir}")
            except Exception as e:
                logger.warning(f"搜索目录 {current_dir} 时出错：{e}")
        
        logger.info(f"未找到文件：{target_filename}")
        return None
    
    def _normalize_filename(self, filename: str) -> str:
        """
        规范化文件名，处理 Unicode 字符和各种空格形式
        
        参数：
            filename: 原始文件名
            
        返回：
            str: 规范化后的文件名
        """
        if not filename:
            return ""
        
        # 解码 URL 编码的文件名
        if '%' in filename:
            try:
                filename = unquote(filename)
            except:
                pass
                
        # Unicode 规范化
        filename = unicodedata.normalize('NFC', filename)
        
        # 替换连续空格为单个空格
        filename = re.sub(r'\s+', ' ', filename)
        
        # 清理文件名两端的空白
        filename = filename.strip()
        
        return filename
    
    def _get_from_direct_local_path(self, filename: str, output_path: str) -> bool:
        """
        从本地 Zotero 存储目录直接获取指定名称的 PDF 文件，
        增强处理特殊字符和空格的能力
        
        参数：
            filename: PDF 文件名
            output_path: 输出文件路径
            
        返回：
            bool: 如果成功则返回 True，否则返回 False
        """
        try:
            if not filename:
                logger.warning("没有提供文件名，无法从本地路径获取文件")
                return False
                
            # 规范化文件名
            normalized_filename = self._normalize_filename(filename)
            
            # 构建可能的文件路径
            potential_paths = []
                
            # 首先尝试从 ZOTERO_LOCAL_PATH 获取
            if self.zotero_local_path:
                # 直接路径
                potential_paths.append(os.path.join(self.zotero_local_path, normalized_filename))
                potential_paths.append(os.path.join(self.zotero_local_path, filename))  # 原始文件名
                
                # 常见子目录
                for subdir in self.common_subdirs:
                    potential_paths.append(os.path.join(self.zotero_local_path, subdir, normalized_filename))
                    potential_paths.append(os.path.join(self.zotero_local_path, subdir, filename))
                    
            # 然后尝试从 zotero_storage_path 获取
            if self.zotero_storage_path:
                # 直接路径
                potential_paths.append(os.path.join(self.zotero_storage_path, normalized_filename))
                potential_paths.append(os.path.join(self.zotero_storage_path, filename))
                
                # 常见子目录
                for subdir in self.common_subdirs:
                    potential_paths.append(os.path.join(self.zotero_storage_path, subdir, normalized_filename))
                    potential_paths.append(os.path.join(self.zotero_storage_path, subdir, filename))
            
            # 尝试所有可能的路径
            for path in set(potential_paths):  # 使用 set 去重
                logger.info(f"尝试从路径获取文件：{path}")
                if os.path.exists(path) and os.path.isfile(path):
                    # 复制文件到输出路径
                    with open(path, 'rb') as src, open(output_path, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"成功从路径获取 PDF 文件：{path}")
                    return True
            
            # 如果直接路径都失败了，尝试进行文件搜索
            for base_path in [self.zotero_local_path, self.zotero_storage_path]:
                if base_path:
                    found_path = self._find_file_bfs(base_path, filename)
                    if found_path:
                        with open(found_path, 'rb') as src, open(output_path, 'wb') as dst:
                            dst.write(src.read())
                        logger.info(f"通过搜索找到并复制 PDF 文件：{found_path}")
                        return True
            
            logger.info(f"在本地路径中未找到文件：{filename}")
            return False
        except Exception as e:
            logger.warning(f"从直接路径获取 PDF 失败：{e}")
            return False
    
    def _download_via_api(self, attachment, pdf_filename):
        """通过 API 下载 PDF"""
        try:
            pdf_content = self.zot.file(attachment['key'])
            if pdf_content:
                with open(pdf_filename, 'wb') as f:
                    f.write(pdf_content)
                logger.info(f"成功通过 API 下载 PDF 到：{pdf_filename}")
                return True
        except Exception as e:
            logger.warning(f"通过 API 下载 PDF 失败：{e}")
        return False
    
    def _download_via_link(self, attachment, pdf_filename):
        """通过附件链接下载 PDF"""
        try:
            links = attachment.get('links', {})
            if links and 'enclosure' in links:
                download_url = links['enclosure']['href']
                
                # 添加 API 密钥到 URL
                parsed_url = urlparse(download_url)
                if not parsed_url.query:
                    download_url += f"?key={self.zot.api_key}"
                else:
                    download_url += f"&key={self.zot.api_key}"
                
                return self._download_from_url(download_url, pdf_filename)
        except Exception as e:
            logger.warning(f"通过下载链接获取 PDF 失败：{e}")
        return False
    
    def _copy_from_local_path(self, attachment, pdf_filename):
        """从本地路径复制 PDF"""
        try:
            # 首先尝试使用附件中提供的路径
            path = attachment['data'].get('path', '')
            if path:
                # 本地文件路径可能是 URI 格式，需要解码
                if path.startswith('file:///'):
                    path = unquote(path.replace('file://', ''))
                
                if os.path.exists(path) and os.path.isfile(path):
                    with open(path, 'rb') as src, open(pdf_filename, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"成功从本地路径复制 PDF 到：{pdf_filename}")
                    return True
            
            # 如果上述方法失败，尝试使用 Zotero 存储路径
            local_path = self._find_pdf_in_zotero_storage(attachment)
            if local_path and os.path.exists(local_path) and os.path.isfile(local_path):
                with open(local_path, 'rb') as src, open(pdf_filename, 'wb') as dst:
                    dst.write(src.read())
                logger.info(f"成功从 Zotero 存储路径复制 PDF 到：{pdf_filename}")
                return True
                
        except Exception as e:
            logger.warning(f"从本地路径获取 PDF 失败：{e}")
        return False
    
    def _find_pdf_in_zotero_storage(self, attachment):
        """
        在 Zotero 本地存储中查找 PDF 文件
        
        参数：
            attachment: Zotero 附件信息
            
        返回：
            str: PDF 文件的本地路径，如果找不到则返回 None
        """
        try:
            # 获取附件的 key 和文件名
            attachment_key = attachment['key']
            filename = attachment['data'].get('filename', '')
            
            # 尝试从 key 构建存储路径
            # Zotero 通常使用 {key} 或 {key}/{filename} 的路径格式
            potential_paths = [
                os.path.join(self.zotero_storage_path, attachment_key + '.pdf'),
                os.path.join(self.zotero_storage_path, attachment_key, filename),
                os.path.join(self.zotero_storage_path, attachment_key),
            ]
            
            # 如果文件名不是以.pdf 结尾，添加一个带.pdf 后缀的路径
            if filename and not filename.lower().endswith('.pdf'):
                potential_paths.append(os.path.join(self.zotero_storage_path, attachment_key, filename + '.pdf'))
            
            # 尝试直接使用文件名
            if filename:
                potential_paths.append(os.path.join(self.zotero_storage_path, filename))
            
            # 检查每个可能的路径
            for path in potential_paths:
                if os.path.exists(path) and os.path.isfile(path):
                    return path
            
            # 如果上述方法都失败，尝试在目录中查找匹配的文件
            if os.path.exists(os.path.join(self.zotero_storage_path, attachment_key)) and \
               os.path.isdir(os.path.join(self.zotero_storage_path, attachment_key)):
                directory = os.path.join(self.zotero_storage_path, attachment_key)
                files = os.listdir(directory)
                pdf_files = [f for f in files if f.lower().endswith('.pdf')]
                if pdf_files:
                    return os.path.join(directory, pdf_files[0])
            
            logger.warning(f"在 Zotero 存储中找不到附件 {attachment_key} 的 PDF 文件")
            return None
            
        except Exception as e:
            logger.warning(f"在 Zotero 存储中查找 PDF 文件失败：{e}")
            return None
    
    def _download_from_original_url(self, attachment, pdf_filename):
        """从原始 URL 下载 PDF"""
        try:
            url = attachment['data'].get('url')
            if url and (url.lower().endswith('.pdf') or 'pdf' in url.lower()):
                return self._download_from_url(url, pdf_filename)
        except Exception as e:
            logger.warning(f"从原始 URL 下载 PDF 失败：{e}")
        return False
    
    def _download_from_url(self, url, pdf_filename):
        """从 URL 下载文件到指定路径"""
        try:
            logger.debug(f"尝试从 URL 下载文件：{url[:60]}...")
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(pdf_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"成功从 URL 下载文件到：{pdf_filename}")
                return True
            logger.warning(f"从 URL 下载文件失败，状态码：{response.status_code}")
        except Exception as e:
            logger.warning(f"从 URL 下载文件失败：{e}")
        return False
    
    def sync_items_to_notion(self, items: List[Dict]) -> Tuple[int, int, List[str]]:
        """
        将 Zotero 条目同步到 Notion，增加了通过 ZoteroID 匹配的功能
        
        参数：
            items: Zotero 条目列表
            
        返回：
            Tuple[int, int, List[str]]: 
                - 成功同步的条目数
                - 跳过的条目数（已存在）
                - 错误信息列表
        """
        success_count = 0
        skip_count = 0
        errors = []
        
        # 从 Notion 获取已存在的 DOI 和 Zotero ID 列表，避免重复添加
        existing_dois = set()
        existing_zotero_ids = set()
        
        try:
            # 获取已存在的 DOI
            existing_dois = notion_service.get_existing_dois()
            
            # 获取已存在的 Zotero ID
            existing_zotero_ids = notion_service.get_existing_zotero_ids()
            
            logger.info(f"已从 Notion 获取现有记录：{len(existing_dois)} 个 DOI，{len(existing_zotero_ids)} 个 Zotero ID")
        except Exception as e:
            logger.warning(f"获取已存在的条目信息失败：{e}")
        
        for item in items:
            try:
                # 提取元数据
                metadata = self.extract_metadata(item)
                zotero_key = item['key']
                
                # 首先检查 DOI 是否已存在
                if metadata['doi'] and metadata['doi'].lower() in existing_dois:
                    logger.info(f"论文 DOI 已存在于 Notion，跳过：{metadata['title']} (DOI: {metadata['doi']})")
                    skip_count += 1
                    continue
                
                # 然后检查 Zotero ID 是否已存在
                if zotero_key in existing_zotero_ids:
                    logger.info(f"论文 Zotero ID 已存在于 Notion，跳过：{metadata['title']} (ID: {zotero_key})")
                    skip_count += 1
                    continue
                
                # 尝试获取 PDF
                pdf_path = None
                try:
                    pdf_path = self.get_pdf_attachment(item['key'])
                except Exception as e:
                    logger.warning(f"获取 PDF 失败：{e}")
                
                # 使用 Gemini 分析论文（如果有 PDF）
                gemini_analysis = {}
                if pdf_path:
                    try:
                        gemini_analysis = gemini_service.analyze_pdf_content(pdf_path)
                    except Exception as e:
                        logger.warning(f"Gemini 分析失败：{e}")
                        gemini_analysis = {
                            'brief_summary': '无法分析论文',
                            'keywords': [],
                            'insight': '分析失败',
                            'details': '解析 PDF 失败'
                        }
                    
                    # 删除临时 PDF 文件
                    try:
                        os.remove(pdf_path)
                    except:
                        pass
                
                # 合并元数据和 Gemini 分析结果
                page_data = {**metadata}
                if gemini_analysis:
                    page_data.update({
                        'summary': gemini_analysis.get('brief_summary', ''),
                        'keywords': gemini_analysis.get('keywords', []),
                        'insights': gemini_analysis.get('insight', '')
                    })
                
                # 创建 Notion 页面
                page_id = notion_service.add_to_papers_database(
                    title=metadata['title'],
                    analysis=gemini_analysis,
                    created_at=datetime.now(),
                    metadata=metadata,
                    zotero_id=item['key']
                )
                
                logger.info(f"成功将论文同步到 Notion: {metadata['title']}")
                success_count += 1
                
                # 更新 DOI 和 Zotero ID 集合
                if metadata['doi']:
                    existing_dois.add(metadata['doi'].lower())
                existing_zotero_ids.add(zotero_key)
                
                # 避免过于频繁的 API 请求
                time.sleep(1)
                
            except Exception as e:
                error_msg = f"同步论文时出错 ({item.get('data', {}).get('title', '未知标题')}): {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return success_count, skip_count, errors

def get_zotero_service() -> ZoteroService:
    """
    获取 ZoteroService 的单例实例
    
    返回：
        ZoteroService: 服务实例
    """
    global _zotero_service_instance
    if (_zotero_service_instance is None):
        _zotero_service_instance = ZoteroService()
    return _zotero_service_instance

def format_sync_result(success_count: int, skip_count: int, total_count: int, errors: List[str]) -> str:
    """
    格式化同步结果消息
    
    参数：
        success_count: 成功同步的条目数
        skip_count: 跳过的条目数（已存在）
        total_count: 总共处理的条目数
        errors: 错误信息列表
        
    返回：
        str: 格式化的结果消息
    """
    result = f"✅ 同步完成！\n\n"
    result += f"• 成功同步：{success_count} 篇\n"
    result += f"• 已存在跳过：{skip_count} 篇\n"
    result += f"• 总计论文：{total_count} 篇\n"
    
    if errors:
        result += f"\n⚠️ 同步过程中遇到 {len(errors)} 个错误:\n"
        for i, error in enumerate(errors[:5], 1):  # 最多显示 5 个错误
            result += f"{i}. {error}\n"
        if len(errors) > 5:
            result += f"... 以及其他 {len(errors) - 5} 个错误"
    
    return result

def sync_papers_to_notion(collection_id: Optional[str] = None, 
                           filter_type: str = "count", value: int = 5) -> str:
    """
    将 Zotero 论文同步到 Notion
    
    参数：
        collection_id: 收藏集 ID，如果为 None 则获取所有收藏集
        filter_type: 筛选类型，'count'表示按数量，'days'表示按天数
        value: 数量或天数值
        
    返回：
        str: 结果消息
    """
    zotero_service = get_zotero_service()
    
    # 获取论文
    papers = zotero_service.get_recent_items(collection_id, filter_type, value)
    
    if not papers:
        return "未找到符合条件的论文"
    
    # 同步到 Notion
    success_count, skip_count, errors = zotero_service.sync_items_to_notion(papers)
    
    # 返回格式化的结果
    return format_sync_result(success_count, skip_count, len(papers), errors)

def sync_recent_papers_by_count(collection_id: Optional[str] = None, count: int = 5) -> str:
    """按数量同步最近的论文（兼容旧 API）"""
    return sync_papers_to_notion(collection_id, "count", count)

def sync_recent_papers_by_days(collection_id: Optional[str] = None, days: int = 7) -> str:
    """按天数同步最近的论文（兼容旧 API）"""
    return sync_papers_to_notion(collection_id, "days", days)

def validate_collection_id(collection_id: str) -> bool:
    """
    验证收藏集 ID 是否有效
    
    参数：
        collection_id: 要验证的收藏集 ID
        
    返回：
        bool: 如果收藏集 ID 有效则返回 True，否则返回 False
    """
    try:
        zotero_service = get_zotero_service()
        # 尝试获取收藏集信息
        collection = zotero_service.zot.collection(collection_id)
        return True
    except Exception:
        return False
