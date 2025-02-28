#!/usr/bin/env python3
"""
初始化 Notion 数据库结构
确保所有必要的数据库和属性都已创建
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_papers_database():
    """设置论文数据库结构"""
    from services.notion_service import ensure_papers_database_properties
    
    logger.info("正在设置论文数据库结构...")
    ensure_papers_database_properties()
    logger.info("论文数据库设置完成")

def main():
    """主函数"""
    logger.info("开始初始化 Notion 数据库结构...")
    
    try:
        setup_papers_database()
        logger.info("所有数据库初始化完成")
        return 0
    
    except Exception as e:
        logger.error(f"初始化数据库时出错：{e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
