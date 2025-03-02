"""
Zotero 调试工具：用于分析和检查 Zotero API 返回的数据结构
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

# 导入 Zotero 服务
from services.zotero_service import get_zotero_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

def analyze_attachment_structure(item_key: str, output_file: Optional[str] = None) -> Dict:
    """
    分析指定 Zotero 条目的附件结构
    
    参数：
        item_key: Zotero 条目的 key
        output_file: 可选，输出 JSON 文件的路径
        
    返回：
        Dict: 附件分析结果
    """
    zotero_service = get_zotero_service()
    
    # 获取附件
    attachments = zotero_service.zot.children(item_key)
    
    if not attachments:
        logger.info(f"条目 {item_key} 没有附件")
        return {"error": "没有附件"}
    
    logger.info(f"条目 {item_key} 共找到 {len(attachments)} 个附件")
    
    # 分析所有附件
    analysis = {
        "item_key": item_key,
        "attachment_count": len(attachments),
        "attachments": []
    }
    
    for idx, attachment in enumerate(attachments, 1):
        att_data = {
            "index": idx,
            "key": attachment.get('key', 'unknown'),
            "data": attachment.get('data', {}),
            "links": attachment.get('links', {})
        }
        
        # 单独提取关键属性便于查看
        data = attachment.get('data', {})
        att_data["key_properties"] = {
            "contentType": data.get('contentType', 'unknown'),
            "filename": data.get('filename', 'unknown'),
            "title": data.get('title', 'unknown'),
            "linkMode": data.get('linkMode', 'unknown'),
            "url": data.get('url', 'unknown'),
            "path": data.get('path', 'unknown')
        }
        
        analysis["attachments"].append(att_data)
    
    # 输出到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        logger.info(f"附件分析已保存至：{output_file}")
    
    return analysis

def find_pdf_items(limit: int = 10) -> List[str]:
    """
    查找最近的包含 PDF 附件的条目
    
    参数：
        limit: 要检查的最近条目数量
        
    返回：
        List[str]: 包含 PDF 附件的条目 key 列表
    """
    zotero_service = get_zotero_service()
    
    # 获取最近的条目
    recent_items = zotero_service.get_recent_items(filter_type='count', value=limit)
    
    pdf_items = []
    for item in recent_items:
        item_key = item['key']
        attachments = zotero_service.zot.children(item_key)
        
        # 检查是否有 PDF 附件
        has_pdf = any(att['data'].get('contentType') == 'application/pdf' for att in attachments if 'data' in att)
        if has_pdf:
            title = item['data'].get('title', 'Unknown Title')
            pdf_items.append((item_key, title))
    
    # 输出结果
    logger.info(f"在最近 {limit} 条目中找到 {len(pdf_items)} 篇带有 PDF 附件的论文")
    for idx, (key, title) in enumerate(pdf_items, 1):
        logger.info(f"{idx}. {title} (Key: {key})")
    
    return [key for key, _ in pdf_items]

if __name__ == "__main__":
    # 示例用法
    logger.info("查找带有 PDF 附件的条目...")
    pdf_items = find_pdf_items(20)
    
    if pdf_items:
        # 分析第一个条目的附件
        first_item = pdf_items[0]
        logger.info(f"分析条目 {first_item} 的附件...")
        
        # 输出到当前目录下的 JSON 文件
        output_file = os.path.join(os.getcwd(), f"zotero_attachment_{first_item}.json")
        analyze_attachment_structure(first_item, output_file)
