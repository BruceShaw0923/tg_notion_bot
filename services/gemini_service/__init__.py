"""
Google Gemini API 服务模块

提供内容分析、PDF 解析和周报生成等功能
"""

# 导入客户端
from .client import (
    GEMINI_API_KEY,
    GEMINI_AVAILABLE,
    configure_gemini_api,
    genai,
    model,
    vision_model,
)

# 导入内容分析功能
from .content_analyzer import analyze_content, enrich_analysis_with_metadata

# 导入 PDF 分析功能
from .pdf_analyzer import (
    analyze_pdf_content,
    extract_and_analyze_pdf_text,
    safe_extract_fields,
)

# 导入工具函数
from .utils import (
    extract_date,
    extract_multi_select,
    extract_property_text,
    extract_url,
)

# 导入周报功能
from .weekly_summary import generate_weekly_summary, get_content_preview

# 暴露所有公共函数，保持与原模块兼容
__all__ = [
    # 客户端和配置
    'genai', 'model', 'vision_model', 
    'GEMINI_API_KEY', 'GEMINI_AVAILABLE',
    'configure_gemini_api',
    
    # 内容分析
    'analyze_content',
    'enrich_analysis_with_metadata',
    
    # PDF 分析
    'analyze_pdf_content',
    'safe_extract_fields',
    'extract_and_analyze_pdf_text',
    
    # 周报功能
    'generate_weekly_summary',
    'get_content_preview',
    
    # 工具函数
    'extract_property_text',
    'extract_multi_select',
    'extract_date',
    'extract_url'
]
