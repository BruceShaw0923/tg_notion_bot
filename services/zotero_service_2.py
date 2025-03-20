"""
Zotero 服务：提供 Zotero API 相关功能，包括获取收藏集、同步论文到 Notion 等
1. 从环境变量中获取 Zotero API 配置
2. 初始化 Zotero API 客户端
3. 获取所有收藏集 def get_all_collections(self) -> List[Dict]:
4. 格式化收藏集列表，供 Telegram 显示 format_collection_list_for_telegram(self) -> str:
5. 获取最近的论文项目，支持按数量或天数筛选 get_recent_items(self, collection_id: Optional[str] = None, filter_type: str = "count", value: int = 5) -> List[Dict]:
6. 从 Zotero 条目中提取元数据 extract_metadata(self, item: Dict) -> Dict:
7. 获取论文的 PDF 附件 get_pdf_attachment(self, item_key: str) -> Optional[str]:
    通过在 API 中获取附件的名称如"Spear 等 - 2019 - Understanding TCR affinity, antigen specificity, and cross-reactivity to improve TCR gene-modified T.pdf"，然后在本地目录下"/Users/wangruochen/Zotero/storage/pdfs/"找到对应的 PDF 附件"/Users/wangruochen/Zotero/storage/pdfs/Spear 等 - 2019 - Understanding TCR affinity, antigen specificity, and cross-reactivity to improve TCR gene-modified T.pdf"，然后复制到/tmp 目录下等待下一步处理
8. 将 Zotero 条目同步到 Notion，通过 ZoteroID 和 DOI 匹配的功能，确保不重复同步 sync_items_to_notion(self, items: List[Dict]) -> Tuple[int, int, List[str]]:
9. 获取 ZoteroService 的单例实例
    1. 格式化同步结果消息 format_sync_result(success_count: int, skip_count: int, total_count: int, errors: List[str]) -> str:
    2. 将 Zotero 论文同步到 Notion sync_papers_to_notion(collection_id: Optional[str] = None, filter_type: str = "count", value: int = 5) -> str:
    3. 按数量同步最近的论文（兼容旧 API）sync_recent_papers_by_count(collection_id: Optional[str] = None, count: int = 5) -> str:
    4. 按天数同步最近的论文（兼容旧 API）sync_recent_papers_by_days(collection_id: Optional[str] = None, days: int = 7) -> str:
    5. 验证收藏集 ID 是否有效 validate_collection_id(collection_id: str) -> bool:
"""

import logging
import os
import re
import time
import unicodedata
import tempfile  # 添加缺少的模块导入
import shutil    # 添加缺少的模块导入
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
    def __init__(self):
        """Initialize ZoteroService with API credentials"""
        self.api_key = ZOTERO_API_KEY
        self.user_id = ZOTERO_USER_ID
        self.zot = zotero.Zotero(self.user_id, 'user', self.api_key)
        
        # 从环境变量获取 PDF 存储路径，如果没有则使用默认值
        self.pdf_storage_path = os.environ.get('ZOTERO_PDF_PATH', "/Users/wangruochen/Zotero/storage/pdfs")
        # 记录 PDF 存储路径，方便调试
        logger.info(f"Using PDF storage path: {self.pdf_storage_path}")
        # 检查路径是否存在
        if not os.path.exists(self.pdf_storage_path):
            logger.warning(f"PDF storage path does not exist: {self.pdf_storage_path}")

    def get_all_collections(self) -> List[Dict]:
        """Get all Zotero collections"""
        try:
            collections = self.zot.collections()
            return collections
        except Exception as e:
            logger.error(f"Error getting collections: {str(e)}")
            return []

    def format_collection_list_for_telegram(self) -> str:
        """Format collections list for Telegram display"""
        collections = self.get_all_collections()
        if not collections:
            return "No collections found."
        
        formatted_list = "Available collections:\n\n"
        for coll in collections:
            formatted_list += f"📚 {coll['data']['name']}\n"
            formatted_list += f"ID: {coll['key']}\n\n"
        return formatted_list

    def get_recent_items(self, collection_id: Optional[str] = None, 
                        filter_type: str = "count", value: int = 5) -> List[Dict]:
        """Get recent items based on count or days"""
        try:
            if (filter_type == "count"):
                if collection_id:
                    items = self.zot.collection_items(collection_id, limit=value)
                else:
                    items = self.zot.items(limit=value)
            else:  # filter_type == "days"
                cutoff_date = datetime.now() - timedelta(days=value)
                if collection_id:
                    items = self.zot.collection_items(collection_id)
                else:
                    items = self.zot.items()
                items = [item for item in items 
                        if datetime.fromisoformat(item['data']['dateAdded'].replace('Z', '+00:00')) 
                        >= cutoff_date]
            return items
        except Exception as e:
            logger.error(f"Error getting recent items: {str(e)}")
            return []

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

    def get_pdf_attachment(self, item_key: str) -> Optional[str]:
        """
        获取条目的 PDF 附件
        
        参数：
            item_key: Zotero 条目的唯一键（注意：这是论文条目的 ID，不是附件的 ID）
            
        返回：
            Optional[str]: 本地临时 PDF 文件路径，如果找不到则返回 None
        """
        try:
            # 获取条目（使用条目的 Zotero ID）
            item = self.zot.item(item_key)
            logger.info(f"Using item key to get metadata: {item_key}")
            metadata = self.extract_metadata(item)
            
            # 获取条目的所有子条目 (附件)
            children = self.zot.children(item_key)
            
            pdf_attachments = []
            for child in children:
                child_data = child.get('data', {})
                if child_data.get('contentType') == 'application/pdf' or child_data.get('filename', '').lower().endswith('.pdf'):
                    pdf_attachments.append(child)
            
            if pdf_attachments:
                # 使用找到的第一个 PDF 附件
                attachment = pdf_attachments[0]
                filename = attachment['data'].get('filename', metadata['title'])
            else:
                # 如果没有找到 PDF 附件，使用论文标题作为文件名
                filename = metadata['title']
            
            # 确保文件名有.pdf 后缀
            if not filename.lower().endswith('.pdf'):
                filename = f"{filename}.pdf"
            
            # 尝试在本地存储路径中查找文件
            source_path = os.path.join(self.pdf_storage_path, filename)
            logger.info(f"Looking for file at: {source_path}")
            if (os.path.exists(source_path)):
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
                
                # 如果本地文件不存在，并且找到了附件，尝试通过 Zotero API 获取
                if pdf_attachments:
                    try:
                        attachment = pdf_attachments[0]
                        logger.info(f"尝试通过 Zotero API 获取附件 {attachment['key']}")
                        # 注意：这里使用附件的 key，而不是条目的 key
                        attachment_item = self.zot.item(attachment['key'])
                        if 'links' in attachment_item and 'enclosure' in attachment_item['links']:
                            download_url = attachment_item['links']['enclosure']['href']
                            logger.info(f"获取到下载链接：{download_url}")
                            
                            # 下载 PDF 到临时目录
                            temp_dir = tempfile.mkdtemp()
                            target_path = os.path.join(temp_dir, os.path.basename(filename))
                            
                            # 使用带有鉴权的请求下载文件
                            headers = {"Authorization": f"Bearer {self.api_key}"}
                            response = requests.get(download_url, headers=headers, stream=True)
                            if response.status_code == 200:
                                with open(target_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                logger.info(f"成功下载 PDF 文件到：{target_path}")
                                return target_path
                            else:
                                logger.error(f"下载 PDF 失败，状态码：{response.status_code}")
                    except Exception as e:
                        logger.error(f"通过 API 获取 PDF 失败：{str(e)}")
        except Exception as e:
            logger.error(f"获取 PDF 附件时出错：{str(e)}")
        
        return None


    def sync_items_to_notion(self, items: List[Dict]) -> Tuple[int, int, List[str]]:
        """Sync items to Notion"""
        success_count = 0
        skip_count = 0
        errors = []

        for item in items:
            try:
                # 提取完整元数据
                metadata = self.extract_metadata(item)
                
                # 记录更详细的元数据信息
                logger.info(f"Processing paper: {metadata['title']}")
                logger.info(f"Authors: {', '.join(metadata['authors']) if metadata['authors'] else 'Not available'}")
                logger.info(f"DOI: {metadata['doi'] or 'Not available'}")
                logger.info(f"Publication: {metadata['publication'] or 'Not available'}")
                logger.info(f"Date: {metadata['date'] or 'Not available'}")
                logger.info(f"Tags count: {len(metadata['tags'])}")
                
                # Check if already exists in Notion
                if notion_service.check_paper_exists_in_notion(doi=metadata.get('doi'), zotero_id=metadata.get('zotero_id')):
                    logger.info(f"Paper already exists in Notion: {metadata['title']}")
                    skip_count += 1
                    continue

                # Get PDF attachment
                pdf_path = self.get_pdf_attachment(item['key'])
                
                # 使用 Gemini 分析 PDF 内容（如果有 PDF）
                analysis_result = {}
                if pdf_path:
                    logger.info(f"Analyzing PDF with Gemini: {pdf_path}")
                    analysis_result = gemini_service.analyze_pdf_content(pdf_path)
                    if not analysis_result:
                        logger.warning(f"Failed to analyze PDF: {pdf_path}")
                        analysis_result = {
                            "title": metadata['title'],
                            "brief_summary": metadata.get('abstract', ''),
                            "details": f"Failed to analyze PDF. Original abstract: {metadata.get('abstract', '')}",
                            "insight": "PDF analysis failed"
                        }
                else:
                    # 如果没有 PDF，使用元数据创建基本分析结果
                    logger.info(f"No PDF found, using metadata only: {metadata['title']}")
                    analysis_result = {
                        "title": metadata['title'],
                        "brief_summary": metadata.get('abstract', ''),
                        "details": f"No PDF available. Original abstract: {metadata.get('abstract', '')}",
                        "insight": "Based on metadata only"
                    }
                
                # 使用已定义的函数合并 Gemini 分析结果与 Zotero 元数据
                enriched_analysis = gemini_service.enrich_analysis_with_metadata(analysis_result, metadata)
                
                # 使用已定义的函数准备 Notion 元数据
                notion_metadata = notion_service.prepare_metadata_for_notion(metadata)
                
                # 使用 add_to_papers_database 将论文添加到 Notion
                created_at = datetime.fromisoformat(item['data']['dateAdded'].replace('Z', '+00:00'))
                page_id = notion_service.add_to_papers_database(
                    title=enriched_analysis.get('title', metadata['title']),
                    analysis=enriched_analysis,
                    created_at=created_at,
                    pdf_url=metadata.get('url', ''),
                    metadata=notion_metadata,
                    zotero_id=metadata['zotero_id']
                )
                
                if page_id:
                    success_count += 1
                    logger.info(f"Successfully synced to Notion: {metadata['title']}")
                else:
                    errors.append(f"Failed to sync: {metadata['title']}")

            except Exception as e:
                logger.error(f"Error processing item: {str(e)}")
                errors.append(f"Error processing {item.get('data', {}).get('title', 'Unknown')}: {str(e)}")

        return success_count, skip_count, errors

    @staticmethod
    def format_sync_result(success_count: int, skip_count: int, total_count: int, 
                          errors: List[str]) -> str:
        """Format sync result message"""
        message = f"Sync completed:\n"
        message += f"✅ Successfully synced: {success_count}\n"
        message += f"⏭️ Skipped (already exists): {skip_count}\n"
        message += f"📊 Total processed: {total_count}\n"
        
        if errors:
            message += "\n❌ Errors:\n"
            message += "\n".join(errors)
        
        return message

    def sync_papers_to_notion(self, collection_id: Optional[str] = None, 
                            filter_type: str = "count", value: int = 5) -> str:
        """Sync papers to Notion with filtering options"""
        items = self.get_recent_items(collection_id, filter_type, value)
        success_count, skip_count, errors = self.sync_items_to_notion(items)
        return self.format_sync_result(success_count, skip_count, len(items), errors)

    def sync_recent_papers_by_count(self, collection_id: Optional[str] = None, 
                                  count: int = 5) -> str:
        """Sync recent papers by count (legacy API)"""
        return self.sync_papers_to_notion(collection_id, "count", count)

    def sync_recent_papers_by_days(self, collection_id: Optional[str] = None, 
                                 days: int = 7) -> str:
        """Sync recent papers by days (legacy API)"""
        return self.sync_papers_to_notion(collection_id, "days", days)

    def validate_collection_id(self, collection_id: str) -> bool:
        """Validate if collection ID exists"""
        try:
            self.zot.collection(collection_id)
            return True
        except Exception:
            return False

def get_zotero_service() -> ZoteroService:
    """Get singleton instance of ZoteroService"""
    global _zotero_service_instance
    if _zotero_service_instance is None:
        _zotero_service_instance = ZoteroService()
    return _zotero_service_instance

# 添加模块级函数，这样就可以直接从模块导入
def sync_papers_to_notion(collection_id=None, filter_type="count", value=5):
    """
    将 Zotero 论文同步到 Notion
    
    参数：
        collection_id: 可选的 Zotero 收藏集 ID
        filter_type: 过滤类型，可以是 "count" 或 "days"
        value: 对应过滤类型的值（篇数或天数）
        
    返回：
        格式化的同步结果消息
    """
    return get_zotero_service().sync_papers_to_notion(collection_id, filter_type, value)

def validate_collection_id(collection_id):
    """
    验证收藏集 ID 是否有效
    
    参数：
        collection_id: Zotero 收藏集 ID
        
    返回：
        布尔值，表示 ID 是否有效
    """
    return get_zotero_service().validate_collection_id(collection_id)