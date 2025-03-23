"""
内容分析模块

使用 Google Gemini API 分析文本内容
"""

import logging
import json
import re
from config import PREDEFINED_TAG_CATEGORIES
from utils.helpers import extract_tags_from_categories
from config.prompts import CONTENT_ANALYSIS_PROMPT
from .client import model, GEMINI_AVAILABLE

logger = logging.getLogger(__name__)

def analyze_content(content):
    """
    使用 Google Gemini API 分析内容
    
    参数：
    content (str): 需要分析的内容
    
    返回：
    dict: 包含标题、摘要和标签的字典
    """
    if not content or len(content.strip()) == 0:
        return {"title": "", "summary": "", "tags": []}
    
    try:
        # 使用配置文件中的提示模板，注入预定义标签类别和内容
        prompt = CONTENT_ANALYSIS_PROMPT.format(
            categories=", ".join(PREDEFINED_TAG_CATEGORIES),
            content=content[:4000]  # 限制内容长度
        )
        
        response = model.generate_content(prompt)
        
        # 提取 JSON 部分
        import json
        import re
        
        # 尝试找到 JSON 部分并解析
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(0))
                # 确保 tags 是列表
                if not isinstance(result.get("tags", []), list):
                    result["tags"] = []
                # 确保有标题字段
                if "title" not in result:
                    result["title"] = ""
                return result
            except json.JSONDecodeError:
                pass
        
        # 如果上述尝试失败，则进行更简单的解析
        title = ""
        summary = ""
        tags = []
        
        lines = response.text.split('\n')
        for line in lines:
            if '"title"' in line.lower() and ':' in line:
                title = line.split(':', 1)[1].strip().strip('"',).strip(',')
            if '"summary"' in line.lower() and ':' in line:
                summary = line.split(':', 1)[1].strip().strip('"',).strip(',')
            elif '"tags"' in line.lower() and '[' in line:
                tags_part = line[line.find('['):].strip()
                # 简单解析标签列表
                tags = [tag.strip().strip('"').strip("'") for tag in tags_part.strip('[]').split(',')]
        
        # 如果自动解析失败，则从预定义类别中提取一些标签
        if not tags:
            category_tags = extract_tags_from_categories(content, PREDEFINED_TAG_CATEGORIES)
            if category_tags:
                tags = category_tags
        
        return {
            "title": title if title else "无标题",
            "summary": summary if summary else "无摘要",
            "tags": [tag for tag in tags if tag] if tags else []
        }
    
    except Exception as e:
        logger.error(f"分析内容时出错：{e}")
        return {
            "title": "无法生成标题",
            "summary": "无法生成摘要",
            "tags": []
        }

def enrich_analysis_with_metadata(analysis: dict, metadata: dict) -> dict:
    """
    将 Zotero 元数据添加到 Gemini 分析结果
    
    参数：
        analysis: Gemini 分析结果
        metadata: Zotero 元数据
        
    返回：
        enriched_analysis: 添加元数据后的分析结果
    """
    result = analysis.copy() if analysis else {}
    
    # 使用元数据中的标题（如果存在且分析中未提供）
    if metadata.get('title') and not result.get('title'):
        result['title'] = metadata['title']
    
    # 添加作者信息
    if metadata.get('authors'):
        result['authors'] = metadata['authors']
    
    # 添加 DOI
    if metadata.get('doi'):
        result['doi'] = metadata['doi']
    
    # 添加出版信息
    if metadata.get('publication'):
        result['publication'] = metadata['publication']
    
    # 添加日期
    if metadata.get('date'):
        result['date'] = metadata['date']
    
    # 添加 URL（如果元数据中有而分析中没有）
    if metadata.get('url') and not result.get('url'):
        result['url'] = metadata['url']
    
    # 添加摘要（如果元数据中有而分析中没有）
    if metadata.get('abstract') and not result['brief_summary']:
        result['brief_summary'] = metadata['abstract']
    
    # 添加 Zotero 标签
    if metadata.get('tags'):
        result['zotero_tags'] = metadata['tags']
    
    # 添加 Zotero 键值
    if metadata.get('zotero_key'):
        result['zotero_key'] = metadata['zotero_key']
    
    return result
