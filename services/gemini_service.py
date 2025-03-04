import google.generativeai as genai
import logging
import json
import re
import os
from config import GEMINI_API_KEY, PREDEFINED_TAG_CATEGORIES
from utils.helpers import extract_tags_from_categories
from config.prompts import (
    CONTENT_ANALYSIS_PROMPT,
    PDF_ANALYSIS_PROMPT,
    PDF_TEXT_ANALYSIS_PROMPT,
    WEEKLY_SUMMARY_PROMPT
)

logger = logging.getLogger(__name__)

# 配置 Google Gemini API
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    vision_model = genai.GenerativeModel('gemini-pro-vision')
    GEMINI_AVAILABLE = bool(GEMINI_API_KEY)
except Exception as e:
    logger.error(f"配置 Gemini API 时出错：{e}")
    GEMINI_AVAILABLE = False

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

def analyze_pdf_content(pdf_path, url=None):
    """
    分析 PDF 文件内容，特别是学术论文
    
    参数：
    pdf_path (str): PDF 文件路径
    url (str, optional): PDF 原始 URL
    
    返回：
    dict: 包含论文分析的字典
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini API 未配置或不可用，无法解析 PDF")
        return None

    try:
        # 检查文件大小 - Gemini 有输入限制
        file_size = os.path.getsize(pdf_path)
        if (file_size > 20 * 1024 * 1024):  # 20MB
            logger.warning(f"PDF 文件过大 ({file_size / (1024*1024):.2f}MB)，超过 Gemini 处理限制")
            return None
            
        # 尝试用 Gemini Vision API 处理 PDF
        try:
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()

            # 创建上下文提示
            url_context = f"该 PDF 文件来源：{url}" if url else "请分析以下 PDF 文件"
            prompt = PDF_ANALYSIS_PROMPT.format(url_context=url_context)
            
            # 创建包含 PDF 的请求
            image_parts = [
                {
                    "mime_type": "application/pdf",
                    "data": pdf_data
                }
            ]
            
            # 发送请求到 Gemini
            logger.info("正在发送 PDF 到 Gemini 进行分析...")
            response = vision_model.generate_content([prompt, image_parts])
            
            # 处理响应文本，尝试提取 JSON
            response_text = response.text
            logger.info("收到 Gemini 响应，正在处理...")
            logger.debug(f"原始响应：{response_text[:500]}...")  # 记录响应的前 500 个字符用于调试
            
            # 清理格式
            response_text = response_text.replace('\\n', '\n').replace('\\', '')
            
            # 尝试提取 JSON 格式的内容
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    result = json.loads(json_str)
                except Exception as json_err:
                    logger.warning(f"JSON 块解析失败：{json_err}")
                    result = safe_extract_fields(response_text)
            else:
                # 尝试直接解析整个文本为 JSON
                try:
                    # 寻找可能的 JSON 部分
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        result = json.loads(json_str)
                    else:
                        # 如果找不到完整的 JSON，使用正则表达式提取字段
                        result = safe_extract_fields(response_text)
                except json.JSONDecodeError:
                    # 使用字段提取方法
                    result = safe_extract_fields(response_text)
            
            # 确保有必要的字段
            required_fields = ["title", "brief_summary", "details", "insight"]
            for field in required_fields:
                if field not in result:
                    result[field] = ""
            
            return result
            
        except Exception as e:
            logger.error(f"使用 Gemini Vision API 分析 PDF {pdf_path} 时出错：{str(e)}")
            logger.debug(f"异常类型：{type(e).__name__}")
            logger.debug(f"异常详情：{e}")
            
            # 如果 Vision API 失败，尝试基于文本的方法
            return extract_and_analyze_pdf_text(pdf_path)
    
    except Exception as e:
        logger.error(f"分析 PDF {pdf_path} 内容时出错：{str(e)}")
        return {
            "title": "PDF 分析失败",
            "brief_summary": "无法解析 PDF 内容",
            "details": f"处理过程中出错：{str(e)}",
            "insight": "处理失败"
        }

def safe_extract_fields(text):
    """
    从文本中安全提取字段，处理非 JSON 格式的响应
    
    参数：
    text (str): 响应文本
    
    返回：
    dict: 提取的字段
    """
    result = {}
    
    # 使用更健壮的正则表达式提取字段
    title_pattern = r'(?:标题|title)[：:]\s*(.*?)(?:\n|$)'
    summary_pattern = r'(?:简要摘要|摘要|brief_?summary)[：:]\s*(.*?)(?:\n\n|\n(?=[A-Z#])|$)'
    insight_pattern = r'(?:见解|评价|洞察|insight)[：:]\s*(.*?)(?:\n\n|\n(?=[A-Z#])|$)'
    details_pattern = r'(?:详细分析|详情|details)[：:]\s*(.*?)(?:\n\n(?=[A-Z#])|$)'
    
    # 尝试匹配
    title_match = re.search(title_pattern, text, re.IGNORECASE | re.DOTALL)
    if title_match:
        result["title"] = title_match.group(1).strip()
    
    summary_match = re.search(summary_pattern, text, re.IGNORECASE | re.DOTALL)
    if summary_match:
        result["brief_summary"] = summary_match.group(1).strip()
    
    insight_match = re.search(insight_pattern, text, re.IGNORECASE | re.DOTALL)
    if insight_match:
        result["insight"] = insight_match.group(1).strip()
    
    details_match = re.search(details_pattern, text, re.IGNORECASE | re.DOTALL)
    if details_match:
        result["details"] = details_match.group(1).strip()
    
    # 如果没有找到详情字段，使用整个响应
    if "details" not in result or not result["details"]:
        result["details"] = text
    
    # 如果没有找到标题，使用默认标题
    if "title" not in result or not result["title"]:
        result["title"] = "PDF 分析结果"
    
    # 如果没有找到摘要，尝试使用前几行作为摘要
    if "brief_summary" not in result or not result["brief_summary"]:
        first_lines = " ".join(text.split("\n")[:3])
        result["brief_summary"] = first_lines[:300]
    
    # 如果没有找到洞察，提供默认值
    if "insight" not in result or not result["insight"]:
        result["insight"] = "无法提取关键洞察"
    
    return result

def extract_and_analyze_pdf_text(pdf_path):
    """
    提取 PDF 文本并使用文本模型进行分析
    
    参数：
    pdf_path (str): PDF 文件路径
    
    返回：
    dict: 包含论文分析的字典
    """
    try:
        # 提取 PDF 文本内容
        from pypdf import PdfReader
        
        reader = PdfReader(pdf_path)
        text = ""
        
        # 限制提取的页数，避免过长
        max_pages = min(20, len(reader.pages))
        
        for i in range(max_pages):
            page_text = reader.pages[i].extract_text() 
            if page_text:  # 确保页面包含文本
                text += page_text + "\n\n"
        
        if not text.strip():
            logger.warning("PDF 未提取到文本，可能是扫描版或加密文件")
            return {
                "title": os.path.basename(pdf_path),
                "brief_summary": "无法提取文本内容，可能是扫描版 PDF 或加密文件",
                "details": "此 PDF 没有可提取的文本层",
                "insight": "无法分析"
            }
        
        # 限制文本长度
        text = text[:15000] + ("..." if len(text) > 15000 else "")
        
        # 使用文本模型生成分析
        prompt = PDF_TEXT_ANALYSIS_PROMPT.format(text=text)
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        try:
            # 尝试解析为 JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                # 如果找不到 JSON，使用安全提取方法
                result = safe_extract_fields(response_text)
                
            # 确保有所有必要字段
            required_fields = ["title", "brief_summary", "details", "insight"]
            for field in required_fields:
                if field not in result:
                    result[field] = ""
                    
            return result
        except Exception as json_err:
            logger.error(f"解析模型响应时出错：{json_err}")
            return safe_extract_fields(response_text)
            
    except Exception as e:
        # 更详细的错误日志，包括异常类型
        logger.error(f"提取和分析 PDF 文本时出错：{str(e)}")
        logger.debug(f"异常类型：{type(e).__name__}")
        
        # 尝试获取文件名作为标题
        try:
            filename = os.path.basename(pdf_path)
            title = os.path.splitext(filename)[0]
        except:
            title = "PDF 文档"
            
        return {
            "title": title,
            "brief_summary": "无法提取或解析 PDF 文本",
            "details": f"在处理此 PDF 时发生错误：{type(e).__name__} - {str(e)}",
            "insight": "处理失败"
        }

def generate_weekly_summary(entries):
    """
    使用 Gemini 生成周报总结，并为内容添加引用标记
    
    参数：
    entries (list): Notion 页面条目列表
    
    返回：
    str: 生成的周报总结，包含 Notion 内链引用
    """
    try:
        # 提取条目中的关键信息
        entries_data = []
        for entry in entries:
            # 跳过周报本身
            if "Tags" in entry["properties"] and any(tag.get("name") == "周报" 
                                                for tag in entry["properties"]["Tags"].get("multi_select", [])):
                continue
                
            entry_data = {
                "id": entry["id"],
                "title": extract_property_text(entry, "Name", "title"),
                "summary": extract_property_text(entry, "Summary", "rich_text"),
                "tags": extract_multi_select(entry, "Tags"),
                "created": extract_date(entry, "Created"),
                "url": extract_url(entry, "URL"),
                # 添加原始内容的前 300 个字符，帮助 AI 理解内容
                "content_preview": get_content_preview(entry["id"])
            }
            entries_data.append(entry_data)
            
        # 无内容时返回提示
        if not entries_data:
            return "本周没有添加任何内容。"
            
        # 将条目转换为 JSON 格式
        entries_json = json.dumps(entries_data, ensure_ascii=False, indent=2)
        
        # 使用 Gemini 模型生成分析
        prompt = WEEKLY_SUMMARY_PROMPT.format(entries_json=entries_json)
        
        # 记录生成请求
        logger.info(f"发送周报总结生成请求，包含 {len(entries_data)} 个条目")
        
        response = model.generate_content(prompt)
        
        if response.text:
            # 检查生成的内容是否包含引用标记
            if "[" in response.text and "ref:" in response.text:
                logger.info("周报生成成功，包含引用标记")
            else:
                logger.warning("周报生成成功，但未包含引用标记")
                
            return response.text
        else:
            return "无法生成周报总结，请稍后再试。"
    
    except Exception as e:
        logger.error(f"生成周报总结时出错：{e}")
        return f"生成周报时遇到错误：{str(e)}"

def get_content_preview(page_id, max_length=300):
    """
    获取页面内容的预览
    
    参数：
    page_id (str): Notion 页面 ID
    max_length (int): 预览最大长度
    
    返回：
    str: 页面内容预览
    """
    try:
        from services.notion_service import notion, extract_notion_block_content
        
        # 获取页面内容块
        blocks = notion.blocks.children.list(block_id=page_id).get("results", [])
        
        # 提取文本内容
        content = extract_notion_block_content(blocks)
        
        # 限制长度
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content
    except Exception as e:
        logger.warning(f"获取页面内容预览时出错：{e}")
        return ""

def extract_property_text(entry, property_name, field_type):
    """从 Notion 条目中提取文本属性"""
    if property_name not in entry["properties"]:
        return ""
        
    prop = entry["properties"][property_name]
    
    if field_type == "title" and prop.get("title"):
        text_objects = prop["title"]
        if text_objects and "plain_text" in text_objects[0]:
            return text_objects[0]["plain_text"]
        elif text_objects and "text" in text_objects[0] and "content" in text_objects[0]["text"]:
            return text_objects[0]["text"]["content"]
            
    elif field_type == "rich_text" and prop.get("rich_text"):
        text_objects = prop["rich_text"]
        if text_objects and "plain_text" in text_objects[0]:
            return text_objects[0]["plain_text"]
        elif text_objects and "text" in text_objects[0] and "content" in text_objects[0]["text"]:
            return text_objects[0]["text"]["content"]
            
    return ""

def extract_multi_select(entry, property_name):
    """从 Notion 条目中提取多选项属性"""
    if property_name not in entry["properties"]:
        return []
        
    prop = entry["properties"][property_name]
    
    if prop.get("multi_select"):
        return [item.get("name", "") for item in prop["multi_select"] if "name" in item]
        
    return []

def extract_date(entry, property_name):
    """从 Notion 条目中提取日期属性"""
    if property_name not in entry["properties"]:
        return ""
        
    prop = entry["properties"][property_name]
    
    if prop.get("date") and prop["date"].get("start"):
        return prop["date"]["start"]
        
    return ""

def extract_url(entry, property_name):
    """从 Notion 条目中提取 URL 属性"""
    if property_name not in entry["properties"]:
        return ""
        
    prop = entry["properties"][property_name]
    
    if prop.get("url"):
        return prop["url"]
        
    return ""

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
    if metadata.get('abstract') and not result.get('brief_summary'):
        result['brief_summary'] = metadata['abstract']
    
    # 添加 Zotero 标签
    if metadata.get('tags'):
        result['zotero_tags'] = metadata['tags']
    
    # 添加 Zotero 键值
    if metadata.get('zotero_key'):
        result['zotero_key'] = metadata['zotero_key']
    
    return result

# 确保函数被正确导出
__all__ = [
    'analyze_content', 'analyze_pdf_content',
    'safe_extract_fields', 'extract_and_analyze_pdf_text',
    'generate_weekly_summary', 'enrich_analysis_with_metadata'
]
