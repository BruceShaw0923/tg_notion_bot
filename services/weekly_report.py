from datetime import datetime
from services.notion_service import get_weekly_entries, create_weekly_report
from services.gemini_service import generate_weekly_summary
import logging

logger = logging.getLogger(__name__)

def generate_weekly_report():
    """
    生成并发布每周报告
    
    返回：
    str: 创建的周报页面 URL
    """
    logger.info("开始生成每周报告")
    
    try:
        # 获取过去一周的条目
        entries = get_weekly_entries(days=7)
        logger.info(f"获取到 {len(entries)} 个条目")
        
        if not entries:
            logger.info("没有条目，跳过周报生成")
            return None
        
        # 生成周报标题
        today = datetime.now()
        report_title = f"周报：{today.strftime('%Y-%m-%d')}"
        
        # 使用 Gemini 生成摘要
        report_content = generate_weekly_summary(entries)
        logger.info("成功生成周报内容")
        
        # 创建周报页面
        report_url = create_weekly_report(report_title, report_content)
        logger.info(f"成功创建周报：{report_url}")
        
        return report_url
    
    except Exception as e:
        logger.error(f"生成周报时出错：{e}")
        raise
