#!/usr/bin/env python3
"""
测试 Zotero 获取特定集合中的条目并打印详细信息
这个脚本更简单，专注于调试 Zotero API 的数据获取功能
"""

import sys
import logging
import json
from pathlib import Path
import argparse
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fetch_and_print_collection(collection_id, days=7, max_items=10):
    """获取并打印集合中的条目"""
    from services.zotero_service import get_collection_items_by_date_range, collection_exists
    
    if not collection_exists(collection_id):
        logger.error(f"集合 {collection_id} 不存在！")
        return False
    
    logger.info(f"获取集合 {collection_id} 中最近 {days} 天的条目...")
    
    items = get_collection_items_by_date_range(collection_id, days)
    
    if not items:
        logger.warning(f"未找到符合条件的条目")
        return False
    
    logger.info(f"找到 {len(items)} 个条目")
    
    # 打印条目信息
    for i, item in enumerate(items[:max_items], 1):
        item_data = item.get('data', {})
        item_type = item_data.get('itemType')
        item_key = item_data.get('key')
        
        logger.info(f"\n条目 {i} ({item_type}, ID: {item_key}):")
        
        title = item_data.get('title', '无标题')
        date_added = item_data.get('dateAdded', '未知')
        
        logger.info(f"  标题：{title}")
        logger.info(f"  添加日期：{date_added}")
        
        # 针对附件检查链接模式
        if item_type == 'attachment':
            link_mode = item_data.get('linkMode', '未知')
            content_type = item_data.get('contentType', '未知')
            filename = item_data.get('filename', '未知')
            logger.info(f"  文件名：{filename}")
            logger.info(f"  链接模式：{link_mode}")
            logger.info(f"  内容类型：{content_type}")
            logger.info(f"  URL: {item_data.get('url', '无')}")
            
            # 检查父条目
            parent_item = item.get('parentItem')
            if parent_item:
                parent_data = parent_item.get('data', {})
                logger.info(f"  父条目：{parent_data.get('title', '未知')} (ID: {parent_data.get('key', '未知')})")
        
        # 检查作者
        creators = item_data.get('creators', [])
        if creators:
            logger.info(f"  作者：")
            for creator in creators:
                name = f"{creator.get('firstName', '')} {creator.get('lastName', '')}"
                logger.info(f"    - {name}")
    
    if len(items) > max_items:
        logger.info(f"\n... 以及另外 {len(items) - max_items} 个条目")
    
    return True

def fetch_raw_item(item_id):
    """获取并打印原始条目数据"""
    from services.zotero_service import API_BASE_URL, ZOTERO_USER_ID, get_headers
    import requests
    
    logger.info(f"获取条目 {item_id} 的原始数据...")
    
    url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/items/{item_id}"
    params = {"format": "json"}
    
    try:
        response = requests.get(url, params=params, headers=get_headers())
        response.raise_for_status()
        
        item_data = response.json()
        logger.info(f"原始 JSON 数据：")
        print(json.dumps(item_data, indent=2, ensure_ascii=False))
        return True
    
    except Exception as e:
        logger.error(f"获取条目 {item_id} 时出错：{e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试 Zotero 集合数据获取")
    parser.add_argument("--collection", "-c", help="要获取的集合 ID", required=True)
    parser.add_argument("--days", "-d", type=int, default=7, help="获取最近几天的条目 (默认：7)")
    parser.add_argument("--max", "-m", type=int, default=10, help="最大显示条目数 (默认：10)")
    parser.add_argument("--item", "-i", help="获取特定条目的原始数据")
    
    args = parser.parse_args()
    
    if args.item:
        return 0 if fetch_raw_item(args.item) else 1
    else:
        return 0 if fetch_and_print_collection(args.collection, args.days, args.max) else 1

if __name__ == "__main__":
    sys.exit(main())
