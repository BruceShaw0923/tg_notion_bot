import google.generativeai as genai
import logging
import json
import re
import os
from config import GEMINI_API_KEY, PREDEFINED_TAG_CATEGORIES
from utils.helpers import extract_tags_from_categories

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
        # 添加预定义标签类别指导
        prompt = f"""
        分析以下内容，并提供：
        1. 标题 (title)：提取或总结内容的标题（30 字以内）
        1. 简短摘要 (不超过 150 字)
        2. 最多 5 个相关标签
        
        标签要求：
        - 必须从以下预定义类别中选择 1-3 个：{", ".join(PREDEFINED_TAG_CATEGORIES)}
        - 然后添加 2-3 个更具体的相关标签
        
        内容：
        {content[:4000]}
        
        请以 JSON 格式返回：
        {{
            "title": "标题内容",
            "summary": "摘要内容",
            "tags": ["标签 1", "标签 2", "标签 3", "标签 4", "标签 5"]
        }}
        """
        
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
        if file_size > 20 * 1024 * 1024:  # 20MB
            logger.warning(f"PDF 文件过大 ({file_size / (1024*1024):.2f}MB)，超过 Gemini 处理限制")
            return None
            
        # 尝试用 Gemini Vision API 处理 PDF
        try:
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()

            # 创建上下文提示
            url_context = f"该 PDF 文件来源：{url}" if url else "请分析以下 PDF 文件"
            prompt = f"""
            {url_context}
            请分析这个 PDF 文件，我需要以下信息：
            1. 标题 (title)：提取或总结论文的标题
            2. 简要摘要 (brief_summary)：用简短的几句话概述文档的核心内容 (不超过 200 字)
            3. 详细分析 (details)：提供更深入的文档内容分析，包括：
                # 1.核心问题
                [待填充] 用一句话概括研究目标
                ## 现有方法不足： 
                    - [列出 3 点]

                # 2.方法论
                创新点流程图图解：（▢→▢→▢）
                ## 关键技术： 
                    - [分点说明]
                ## 理论支撑： 
                    - [定理名称]+[核心公式]

                # 3.实验验证
                ## 数据集特征： 
                    - [数据量，领域差异]
                ## 指标对比： 
                    - [表格形式呈现 FPR@95 等]
                ## 消融实验： 
                    - [关键参数影响曲线]

                # 4.启示与局限
                ## 可复现性： 
                    - [代码/数据开放情况]
                ## 应用价值： 
                    - [实际部署可能性]
                ## 改进方向： 
                    - [作者讨论的未来工作]
                ## 创新点
                    - [客观评价作者最具创新的工作，以及向外拓展的启发]
            4. 有关这篇文章，高屋建瓴的见解和评价
            
            请使用 Markdown 格式，确保正确使用以下语法：
                - 使用 # 表示一级标题，## 表示二级标题 ### 表示三级标题
                - 使用 **文本** 表示加粗文本
                - 使用 *文本* 表示斜体文本
                - 使用 - 表示列表项
                - 使用 > 表示引用
                - 使用 [文本](链接) 表示超链接
            以结构化 JSON 格式回复，包含四个字段：title, brief_summary, details, insight
            """
            
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
            
            # 尝试提取 JSON 格式的内容
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # 尝试直接解析整个文本为 JSON
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    # 使用文本处理方式
                    title_match = re.search(r'(?:标题|title)[：:]\s*(.*?)(?:\n|$)', response_text, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else ""
                    
                    summary_match = re.search(r'(?:简要摘要|brief_summary)[：:]\s*(.*?)(?:\n\n|\n(?=\d\.)|$)', response_text, re.DOTALL | re.IGNORECASE)
                    brief_summary = summary_match.group(1).strip() if summary_match else ""
                    insight_match = re.search(r'(?:见解与评价|insight)[：:]\s*(.*?)(?:\n\n\d\.|\Z)', response_text, re.DOTALL | re.IGNORECASE)
                    
                    details_match = re.search(r'(?:详细分析|details)[：:]\s*(.*?)(?:\n\n\d\.|\Z)', response_text, re.DOTALL | re.IGNORECASE)
                    details = details_match.group(1).strip() if details_match else response_text
                    
                    result = {
                        "title": title,
                        "brief_summary": brief_summary,
                        "details": details,
                        "insight": insight 
                    }
            
            # 确保有必要的字段
            required_fields = ["title", "brief_summary", "details", "insight"]
            for field in required_fields:
                if field not in result:
                    result[field] = ""
            
            return result
            
        except Exception as e:
            logger.error(f"使用 Gemini Vision API 分析 PDF 时出错：{e}")
            
            # 如果 Vision API 失败，尝试基于文本的方法
            return extract_and_analyze_pdf_text(pdf_path)
    
    except Exception as e:
        logger.error(f"分析 PDF 内容时出错：{e}")
        return {
            "title": "PDF 分析失败",
            "brief_summary": "无法解析 PDF 内容",
            "details": f"处理过程中出错：{str(e)}"
        }

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
            text += reader.pages[i].extract_text() + "\n"
        
        # 限制文本长度
        text = text[:15000] + ("..." if len(text) > 15000 else "")
        
        # 使用文本模型生成分析
        prompt = f"""
        1. 标题 (title)：提取或总结论文的标题
        2. 简要摘要 (brief_summary)：用简短的几句话概述文档的核心内容 (不超过 200 字)，这个摘要会显示在数据库条目的 Abstract 字段中，应该是清晰简洁的概述。
        3. 详细分析 (details)：提供更深入的文档内容分析，包括：
                # 1.核心问题
                [待填充] 用一句话概括研究目标
                ## 现有方法不足： 
                    - [列出 3 点]

                # 2.方法论
                创新点流程图图解：（▢→▢→▢）
                ## 关键技术： 
                    - [分点说明]
                ## 理论支撑： 
                    - [定理名称]+[核心公式]

                # 3.实验验证
                ## 数据集特征： 
                    - [数据量，领域差异]
                ## 指标对比： 
                    - [表格形式呈现 FPR@95 等]
                ## 消融实验： 
                    - [关键参数影响曲线]

                # 4.启示与局限
                ## 可复现性： 
                    - [代码/数据开放情况]
                ## 应用价值： 
                    - [实际部署可能性]
                ## 改进方向： 
                    - [作者讨论的未来工作]
                ## 创新点
                    - [客观评价作者最具创新的工作，以及向外拓展的启发]
        4. 有关这篇文章，高屋建瓴的见解和评价
        论文内容：
        {text}
        
        JSON 格式返回：
        {{
          "title": "论文标题",
          "brief_summary": "简要摘要...",
          "details": "# 1.核心问题\\n...(Markdown 格式详细内容)",
          "insight": "高屋建瓴的见解..."

        }}
        
        请使用 Markdown 格式，确保正确使用以下语法，不要将 markdown 代码放入代码块中：
        - 使用 # 表示一级标题，## 表示二级标题 ### 表示三级标题
        - 使用 **文本** 表示加粗文本
        - 使用 *文本* 表示斜体文本
        - 使用 - 表示列表项
        - 使用 > 表示引用
        - 使用 [文本](链接) 表示超链接
        """
        
        response = model.generate_content(prompt)
        
        # 解析 JSON 响应
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(0))
                return result
            except json.JSONDecodeError:
                pass
        
        # 如果 JSON 解析失败，返回简单格式
        return {
            "title": "PDF 文本解析",
            "brief_summary": response.text[:200] + "...",
            "details": response.text,
            "insight": "见解"
        }
    except Exception as e:
        logger.error(f"提取和分析 PDF 文本时出错：{e}")
        return {
            "title": "PDF 文本提取失败",
            "brief_summary": "无法提取或解析 PDF 文本",
            "details": f"出错：{str(e)}"
        }

def generate_weekly_summary(entries):
    """
    生成本周内容的格式化摘要，支持 Notion 中的标题、加粗等 Markdown 格式
    
    参数：
    entries (list): 本周的 Notion 条目
    
    返回：
    str: 格式化的周报内容（Markdown 格式）
    """
    if not entries:
        return "本周没有记录任何内容。"
    
    try:
        # 提取每个条目的标题、摘要和标签
        entries_data = []
        for entry in entries:
            title = ""
            summary = ""
            tags = []
            url = ""
            
            props = entry.get("properties", {})
            
            # 提取标题
            if "Name" in props and props["Name"].get("title"):
                title = "".join([text.get("plain_text", "") for text in props["Name"]["title"]])
            
            # 提取摘要
            if "Summary" in props and props["Summary"].get("rich_text"):
                summary = "".join([text.get("plain_text", "") for text in props["Summary"]["rich_text"]])
            
            # 提取标签
            if "Tags" in props and props["Tags"].get("multi_select"):
                tags = [tag.get("name", "") for tag in props["Tags"]["multi_select"]]
            
            # 提取 URL
            if "URL" in props and props["URL"].get("url"):
                url = props["URL"]["url"]
            
            entries_data.append({
                "title": title,
                "summary": summary,
                "tags": tags,
                "url": url
            })
        
        # 构建提示，明确指示返回 Markdown 格式
        prompt = f"""
        根据以下本周收集的内容，生成一份简洁的周报摘要。
        分析这些内容的主题和趋势，突出重要的发现和见解。
        
        本周内容：
        {json.dumps(entries_data, ensure_ascii=False)}
        
        请生成一份结构化的周报，包含：
        1. 总体主题和趋势概述
        2. 按类别分组的关键内容
        3. 值得关注的亮点
        
        请使用 Markdown 格式，确保正确使用以下语法：
        - 使用 # 表示一级标题，## 表示二级标题
        - 使用 **文本** 表示加粗文本
        - 使用 *文本* 表示斜体文本
        - 使用 - 表示列表项
        - 使用 > 表示引用
        - 使用 [文本](链接) 表示超链接
        
        示例格式：
        # 本周摘要
        
        **总体趋势**
        本周主要关注了**三个领域**：技术、商业和文化。
        
        ## 技术动态
        - **人工智能**: 最新研究表明...
        - **区块链**: 新的应用场景包括...
        
        请生成类似上述格式的 Markdown 文本，确保标题层级清晰，重点内容加粗显示。不需要将 markdown 代码放入代码块中。
        """
        
        response = model.generate_content(prompt, stream=False)
        
        # 确保返回的是纯文本格式，保留 Markdown 语法
        return response.text
    
    except Exception as e:
        logger.error(f"生成周报摘要时出错：{e}")
        return "生成摘要时出错，请查看日志了解详情。"
