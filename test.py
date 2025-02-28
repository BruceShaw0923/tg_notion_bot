#!/usr/bin/env python3
"""
TG-Notion 自动化机器人测试脚本
用于测试各个组件的功能
"""

import sys
import logging
from datetime import datetime
from config import NOTION_TOKEN, NOTION_DATABASE_ID, GEMINI_API_KEY

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_config():
    """测试配置是否加载成功"""
    logger.info("测试配置...")
    
    if not NOTION_TOKEN:
        logger.error("错误：未设置 NOTION_TOKEN")
        return False
    
    if not NOTION_DATABASE_ID:
        logger.error("错误：未设置 NOTION_DATABASE_ID")
        return False
    
    if not GEMINI_API_KEY:
        logger.error("错误：未设置 GEMINI_API_KEY")
        return False
    
    logger.info("配置测试通过！")
    return True

def test_gemini_api():
    """测试 Google Gemini API 连接"""
    logger.info("测试 Google Gemini API...")
    
    try:
        from services.gemini_service import analyze_content
        result = analyze_content("这是一个测试文本，用于测试 Gemini API 是否工作正常。")
        
        if "summary" in result and "tags" in result:
            logger.info(f"Gemini API 测试成功！摘要：{result['summary'][:30]}...")
            logger.info(f"标签：{result['tags']}")
            return True
        else:
            logger.error(f"Gemini API 返回格式错误：{result}")
            return False
    
    except Exception as e:
        logger.error(f"Gemini API 测试失败：{e}")
        return False

def test_notion_api():
    """测试 Notion API 连接"""
    logger.info("测试 Notion API...")
    
    try:
        from services.notion_service import add_to_notion
        
        # 创建测试页面
        page_id = add_to_notion(
            content="这是一个测试条目，用于验证 Notion API 连接。",
            summary="测试摘要",
            tags=["测试", "API 验证"],
            url="",
            created_at=datetime.now()
        )
        
        if page_id:
            logger.info(f"Notion API 测试成功！页面 ID: {page_id}")
            return True
        else:
            logger.error("Notion API 测试失败：未返回页面 ID")
            return False
    
    except Exception as e:
        logger.error(f"Notion API 测试失败：{e}")
        return False

def main():
    """运行所有测试"""
    logger.info("开始测试 TG-Notion 自动化机器人组件...")
    
    tests = [
        ("配置测试", test_config),
        ("Google Gemini API 测试", test_gemini_api),
        ("Notion API 测试", test_notion_api)
    ]
    
    success = 0
    failed = 0
    
    for name, test_func in tests:
        logger.info(f"运行 {name}...")
        try:
            if test_func():
                success += 1
                logger.info(f"{name}: ✅ 通过")
            else:
                failed += 1
                logger.error(f"{name}: ❌ 失败")
        except Exception as e:
            failed += 1
            logger.error(f"{name}: ❌ 失败 (异常：{e})")
    
    logger.info(f"测试完成：{success} 通过，{failed} 失败")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
