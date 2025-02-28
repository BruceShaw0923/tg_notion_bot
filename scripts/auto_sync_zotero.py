#!/usr/bin/env python3
"""
自动同步 Zotero 最近添加的 PDF 文件
可以通过 cron 定时执行此脚本
"""

import os
import sys
import logging
import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(root_dir, "zotero_sync.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """自动同步 Zotero PDF 文件的主函数"""
    logger.info("开始自动同步 Zotero PDF 文件")
    
    try:
        from services.zotero_service import sync_recent_pdfs
        from services.gemini_service import analyze_pdf_content
        from services.notion_service import add_to_papers_database
        from services.telegram_service import enrich_analysis_with_metadata
        
        # 默认同步最近 2 天的 PDF
        days = 2
        logger.info(f"获取最近 {days} 天添加的 PDF 文件")
        
        # 获取并处理 PDF 文件
        pdf_files = sync_recent_pdfs(days)
        
        if not pdf_files:
            logger.info("未找到最近添加的 PDF 文件")
            return 0
        
        logger.info(f"找到 {len(pdf_files)} 个 PDF 文件，开始处理")
        
        # 逐个处理 PDF 文件
        success_count = 0
        for pdf_path, filename, metadata in pdf_files:
            try:
                logger.info(f"处理：{filename}")
                
                # 使用 Gemini 分析 PDF 内容
                pdf_analysis = analyze_pdf_content(pdf_path, metadata.get('url', ''))
                
                # 标题优先使用元数据中的标题
                title = metadata.get('title', '') or filename
                
                # 添加元数据到分析结果
                enriched_analysis = enrich_analysis_with_metadata(pdf_analysis, metadata)
                
                # 添加到 Notion 数据库
                page_id = add_to_papers_database(
                    title=title,
                    analysis=enriched_analysis,
                    created_at=datetime.datetime.now(),
                    pdf_url=metadata.get('url', '')
                )
                
                success_count += 1
                logger.info(f"成功处理：{filename}")
                
                # 清理临时文件
                try:
                    os.unlink(pdf_path)
                except:
                    pass
                
            except Exception as e:
                logger.error(f"处理 PDF 文件 {filename} 时出错：{e}")
        
        logger.info(f"同步完成！成功处理 {success_count}/{len(pdf_files)} 个 PDF 文件")
        return 0
    
    except Exception as e:
        logger.error(f"自动同步 Zotero PDF 文件过程中出错：{e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
