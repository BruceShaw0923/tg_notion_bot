import logging
import os
import tempfile
import fitz  # PyMuPDF
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    从 PDF 文件中提取文本
    
    参数：
    pdf_path (str): PDF 文件的路径
    
    返回：
    str: 提取的文本内容
    """
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        logger.error(f"提取 PDF 文本时出错：{e}")
        return ""

def extract_metadata_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    从 PDF 文件中提取元数据（如标题、作者等）
    
    参数：
    pdf_path (str): PDF 文件的路径
    
    返回：
    Dict[str, Any]: PDF 元数据
    """
    try:
        metadata = {}
        with fitz.open(pdf_path) as doc:
            meta = doc.metadata
            if meta:
                metadata["title"] = meta.get("title", "")
                metadata["author"] = meta.get("author", "")
                metadata["subject"] = meta.get("subject", "")
                metadata["keywords"] = meta.get("keywords", "")
                metadata["creator"] = meta.get("creator", "")
                metadata["producer"] = meta.get("producer", "")
            
            # 尝试从第一页提取更多信息
            if doc.page_count > 0:
                first_page_text = doc[0].get_text()
                # 通常论文的摘要在第一页
                metadata["first_page"] = first_page_text
        
        return metadata
    except Exception as e:
        logger.error(f"提取 PDF 元数据时出错：{e}")
        return {}

def analyze_academic_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    分析学术 PDF 文件，提取关键信息
    
    参数：
    pdf_path (str): PDF 文件的路径
    
    返回：
    Dict[str, Any]: 包含分析结果的字典
    """
    analysis = {
        "title": "",
        "authors": "",
        "abstract": "",
        "keywords": [],
        "brief_summary": "",
        "details": ""
    }
    
    try:
        # 提取元数据
        metadata = extract_metadata_from_pdf(pdf_path)
        
        # 如果元数据中有标题，则使用它
        if metadata.get("title"):
            analysis["title"] = metadata["title"]
        
        # 提取全文
        full_text = extract_text_from_pdf(pdf_path)
        
        # 尝试从文本中识别摘要部分
        abstract = extract_abstract(full_text)
        if abstract:
            analysis["abstract"] = abstract
            analysis["brief_summary"] = abstract[:500] + "..." if len(abstract) > 500 else abstract
        
        # 准备详细分析文本
        details = f"文档标题：{metadata.get('title', '未知')}\n\n"
        details += f"作者：{metadata.get('author', '未知')}\n\n"
        
        if abstract:
            details += f"摘要:\n{abstract}\n\n"
        
        details += f"关键词：{metadata.get('keywords', '未提供')}\n\n"
        details += "建议进一步阅读全文并添加您的分析。"
        
        analysis["details"] = details
        
        return analysis
    except Exception as e:
        logger.error(f"分析学术 PDF 时出错：{e}")
        analysis["details"] = f"PDF 分析过程中出错：{str(e)}"
        return analysis

def extract_abstract(text: str) -> Optional[str]:
    """
    从文本中提取摘要部分
    
    参数：
    text (str): 完整文本内容
    
    返回：
    Optional[str]: 提取的摘要，如果未找到则为 None
    """
    import re
    
    # 查找常见的摘要标记
    abstract_patterns = [
        r'(?i)abstract[\s\n]*[-:]*([\s\S]*?)(?:\n\n|\n[A-Z][a-z]*\s*\n|Introduction|Keywords)',
        r'(?i)摘要[\s\n]*[:：]*([\s\S]*?)(?:\n\n|关键词|引言|INTRODUCTION)',
    ]
    
    for pattern in abstract_patterns:
        match = re.search(pattern, text)
        if match:
            abstract = match.group(1).strip()
            return abstract
    
    # 如果没有找到明确的摘要，取文档开头的一部分作为近似摘要
    first_paragraphs = " ".join(text.split("\n\n")[:2])
    if len(first_paragraphs) > 50:
        return first_paragraphs[:1000]  # 限制长度
    
    return None
