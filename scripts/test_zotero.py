#!/usr/bin/env python3
"""
测试 Zotero API 连接和功能
用于调试和验证 Zotero 相关功能是否正常工作
"""

import os
import sys
import logging
import argparse
import json
from pathlib import Path
from datetime import datetime
import tempfile
import time

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 导入 Zotero 服务模块
from config import ZOTERO_API_KEY, ZOTERO_USER_ID, ZOTERO_FOLDER_ID
from services.zotero_service import (
    get_headers, 
    get_collections, 
    get_recent_items_by_date_range,
    get_collection_items_by_date_range,
    get_pdf_attachments,
    collection_exists,
    download_attachment_file,
    get_item_metadata
)

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_zotero_connection():
    """测试 Zotero API 连接是否正常"""
    logger.info("测试 Zotero API 连接...")
    
    if not ZOTERO_API_KEY or not ZOTERO_USER_ID:
        logger.error("❌ 错误：未配置 Zotero API 密钥或用户 ID")
        return False
    
    headers = get_headers()
    logger.info(f"使用 API 头信息：{headers}")
    
    try:
        # 尝试获取顶级条目
        from services.zotero_service import API_BASE_URL
        import requests
        
        url = f"{API_BASE_URL}/users/{ZOTERO_USER_ID}/items/top?limit=1"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"✅ Zotero API 连接成功！状态码：{response.status_code}")
            logger.info(f"响应头：{response.headers}")
            return True
        else:
            logger.error(f"❌ Zotero API 连接失败！状态码：{response.status_code}")
            logger.error(f"响应内容：{response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试 Zotero 连接时出错：{e}")
        return False

def test_get_collections():
    """测试获取 Zotero 集合列表"""
    logger.info("获取 Zotero 集合列表...")
    
    collections = get_collections()
    
    if not collections:
        logger.warning("⚠️ 未找到 Zotero 集合")
        return False
    
    logger.info(f"✅ 成功获取 {len(collections)} 个 Zotero 集合：")
    
    for i, collection in enumerate(collections, 1):
        collection_data = collection.get('data', {})
        collection_id = collection_data.get('key', '')
        collection_name = collection_data.get('name', f'Unnamed Collection {i}')
        parent_key = collection_data.get('parentCollection', '')
        
        logger.info(f"    {i}. {collection_name} (ID: {collection_id})" + 
                   (f", 父集合：{parent_key}" if parent_key else ""))
    
    return True

def test_get_recent_items(days=3):
    """测试获取最近添加的条目"""
    logger.info(f"获取最近 {days} 天添加的条目...")
    
    items = get_recent_items_by_date_range(days)
    
    if not items:
        logger.warning(f"⚠️ 最近 {days} 天内未找到条目")
        return False
    
    logger.info(f"✅ 成功获取 {len(items)} 个最近添加的条目：")
    
    # 显示前 5 个条目的简要信息
    for i, item in enumerate(items[:5], 1):
        item_data = item.get('data', {})
        item_key = item_data.get('key', '')
        item_title = item_data.get('title', f'无标题条目 {i}')
        item_type = item_data.get('itemType', '未知类型')
        date_added = item_data.get('dateAdded', '未知日期')
        
        logger.info(f"    {i}. {item_title} ({item_type}, 添加于 {date_added}, ID: {item_key})")
    
    if len(items) > 5:
        logger.info(f"    ... 以及另外 {len(items) - 5} 个条目")
    
    return True

def test_collection_items(collection_id=None, days=3):
    """测试获取特定集合中的条目"""
    # 如果未提供集合 ID，使用默认集合或获取第一个可用集合
    if not collection_id:
        if ZOTERO_FOLDER_ID:
            collection_id = ZOTERO_FOLDER_ID
            logger.info(f"使用默认集合 ID: {collection_id}")
        else:
            collections = get_collections()
            if collections:
                collection_id = collections[0].get('data', {}).get('key', '')
                logger.info(f"使用第一个可用集合 ID: {collection_id}")
            else:
                logger.error("❌ 未提供集合 ID 且无法获取可用集合")
                return False
    
    logger.info(f"测试集合 {collection_id} 中最近 {days} 天添加的条目...")
    
    if not collection_exists(collection_id):
        logger.error(f"❌ 集合 {collection_id} 不存在或无法访问")
        return False
    
    items = get_collection_items_by_date_range(collection_id, days)
    
    if not items:
        logger.warning(f"⚠️ 集合 {collection_id} 最近 {days} 天内未找到条目")
        return False
    
    logger.info(f"✅ 成功获取集合 {collection_id} 中 {len(items)} 个条目：")
    
    # 显示前 5 个条目的简要信息
    for i, item in enumerate(items[:5], 1):
        item_data = item.get('data', {})
        item_key = item_data.get('key', '')
        item_title = item_data.get('title', f'无标题条目 {i}')
        item_type = item_data.get('itemType', '未知类型')
        date_added = item_data.get('dateAdded', '未知日期')
        
        logger.info(f"    {i}. {item_title} ({item_type}, 添加于 {date_added}, ID: {item_key})")
    
    if len(items) > 5:
        logger.info(f"    ... 以及另外 {len(items) - 5} 个条目")
    
    return True

def test_pdf_attachments(days=3):
    """测试获取和下载 PDF 附件"""
    logger.info(f"测试获取最近 {days} 天添加的 PDF 附件...")
    
    attachments = get_pdf_attachments(days)
    
    if not attachments:
        logger.warning(f"⚠️ 最近 {days} 天内未找到 PDF 附件")
        return False
    
    logger.info(f"✅ 找到 {len(attachments)} 个 PDF 附件：")
    
    # 显示 PDF 附件信息
    for i, attachment in enumerate(attachments[:5], 1):
        attachment_data = attachment.get('data', {})
        key = attachment_data.get('key', '')
        filename = attachment_data.get('filename', f'unnamed_file_{i}.pdf')
        link_mode = attachment_data.get('linkMode', '未知')
        parent_item = attachment.get('parentItem', {})
        parent_title = parent_item.get('data', {}).get('title', '未知父条目')
        
        logger.info(f"    {i}. {filename} (linkMode: {link_mode}, ID: {key})")
        logger.info(f"       父条目：{parent_title}")
    
    if len(attachments) > 5:
        logger.info(f"    ... 以及另外 {len(attachments) - 5} 个附件")
    
    # 尝试下载第一个附件
    if attachments:
        logger.info(f"尝试下载第一个附件...")
        attachment = attachments[0]
        attachment_data = attachment.get('data', {})
        filename = attachment_data.get('filename', 'unnamed_file.pdf')
        
        start_time = time.time()
        pdf_path, file_name, metadata = download_attachment_file(attachment)
        end_time = time.time()
        
        if pdf_path:
            file_size_kb = os.path.getsize(pdf_path) / 1024
            logger.info(f"✅ 成功下载文件 '{file_name}' 到 {pdf_path}")
            logger.info(f"   大小：{file_size_kb:.2f} KB, 耗时：{end_time - start_time:.2f} 秒")
            
            # 显示元数据摘要
            logger.info(f"   元数据摘要：")
            logger.info(f"     标题：{metadata.get('title', '无标题')}")
            logger.info(f"     作者数量：{len(metadata.get('creators', []))}")
            if metadata.get('DOI'):
                logger.info(f"     DOI: {metadata.get('DOI')}")
                
            # 清理临时文件
            try:
                os.unlink(pdf_path)
                logger.info(f"   已清理临时文件")
            except:
                logger.warning(f"   无法清理临时文件：{pdf_path}")
            
            return True
        else:
            logger.error(f"❌ 无法下载附件 '{filename}'")
            logger.info(f"   元数据：{json.dumps(metadata, indent=2, ensure_ascii=False)[:500]}...")
            return False
    
    return True

def test_specific_item(item_key):
    """测试获取特定条目的信息"""
    logger.info(f"获取条目 {item_key} 的信息...")
    
    metadata = get_item_metadata(item_key)
    
    if not metadata:
        logger.error(f"❌ 无法获取条目 {item_key} 的元数据")
        return False
    
    logger.info(f"✅ 成功获取条目 {item_key} 的元数据：")
    logger.info(f"    标题：{metadata.get('title', '无标题')}")
    logger.info(f"    类型：{metadata.get('itemType', '未知类型')}")
    logger.info(f"    添加日期：{metadata.get('dateAdded', '未知')}")
    
    creators = metadata.get('creators', [])
    if creators:
        logger.info(f"    作者：")
        for i, creator in enumerate(creators[:3], 1):
            name = f"{creator.get('firstName', '')} {creator.get('lastName', '')}"
            logger.info(f"        {i}. {name}")
        if len(creators) > 3:
            logger.info(f"        ... 以及另外 {len(creators) - 3} 个作者")
    
    return True

def print_object_structure(obj, name="对象", max_level=2, current_level=0):
    """打印对象结构，用于调试"""
    indent = "  " * current_level
    
    if current_level >= max_level:
        logger.info(f"{indent}{name}: 已达到最大嵌套级别")
        return
    
    if isinstance(obj, dict):
        logger.info(f"{indent}{name} (dict):")
        for k, v in obj.items():
            print_object_structure(v, k, max_level, current_level + 1)
    elif isinstance(obj, list):
        if not obj:
            logger.info(f"{indent}{name} (空列表)")
        else:
            logger.info(f"{indent}{name} (list, 长度={len(obj)}):")
            if len(obj) > 3:
                for i, item in enumerate(obj[:2]):
                    print_object_structure(item, f"[{i}]", max_level, current_level + 1)
                logger.info(f"{indent}  ... 以及另外 {len(obj) - 2} 项")
            else:
                for i, item in enumerate(obj):
                    print_object_structure(item, f"[{i}]", max_level, current_level + 1)
    else:
        value = str(obj)
        if len(value) > 100:
            value = value[:100] + "..."
        logger.info(f"{indent}{name}: {value}")
    
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试 Zotero API 功能")
    parser.add_argument("--test", "-t", choices=["all", "connection", "collections", "recent", "collection", "pdfs", "item"], 
                      default="all", help="指定要运行的测试")
    parser.add_argument("--days", "-d", type=int, default=7, help="获取最近几天的条目 (默认：7)")
    parser.add_argument("--collection", "-c", help="要测试的特定集合 ID")
    parser.add_argument("--item", "-i", help="要测试的特定条目 ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Zotero 测试工具 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"配置信息：")
    logger.info(f"  用户 ID: {ZOTERO_USER_ID}")
    logger.info(f"  API 密钥：{ZOTERO_API_KEY[:5]}{'*' * (len(ZOTERO_API_KEY) - 10)}{ZOTERO_API_KEY[-5:] if ZOTERO_API_KEY else ''}")
    logger.info(f"  默认文件夹 ID: {ZOTERO_FOLDER_ID or '未设置'}")
    logger.info(f"  正在测试：{args.test}")
    
    # 运行所选测试
    results = {}
    
    if args.test in ["all", "connection"]:
        results["connection"] = test_zotero_connection()
    
    if results.get("connection", True) and args.test in ["all", "collections"]:
        results["collections"] = test_get_collections()
    
    if results.get("connection", True) and args.test in ["all", "recent"]:
        results["recent"] = test_get_recent_items(args.days)
    
    if results.get("connection", True) and args.test in ["all", "collection"]:
        results["collection"] = test_collection_items(args.collection, args.days)
    
    if results.get("connection", True) and args.test in ["all", "pdfs"]:
        results["pdfs"] = test_pdf_attachments(args.days)
    
    if results.get("connection", True) and args.test in ["item"] and args.item:
        results["item"] = test_specific_item(args.item)
    
    # 显示测试结果摘要
    logger.info("\n测试结果摘要：")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"  {test_name}: {status}")
        
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n✅ 所有测试通过！")
        return 0
    else:
        logger.info("\n⚠️ 部分测试失败，请检查上面的错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
