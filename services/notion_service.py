from notion_client import Client
from datetime import datetime, timedelta
import logging
from config import NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_TODO_DATABASE_ID, NOTION_PAPERS_DATABASE_ID
from utils.helpers import truncate_text
from services.gemini_service import analyze_content
import re
import os
import requests
import tempfile

logger = logging.getLogger(__name__)

# 初始化 Notion 客户端
notion = Client(auth=NOTION_TOKEN)

# 添加这个函数，返回已初始化的 notion 客户端
def get_notion_client():
    """
    获取已初始化的 Notion 客户端
    
    返回：
        Client: Notion 客户端实例
    """
    global notion
    return notion

# 导入 Gemini 服务
try:
    from services.gemini_service import analyze_pdf_content
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("无法导入 Gemini 服务，将使用备用方法解析 PDF")
    GEMINI_AVAILABLE = False

def add_to_notion(content, summary, tags, url="", created_at=None):
    """
    将内容添加到 Notion 数据库
    
    参数：
    content (str): 消息内容
    summary (str): AI 生成的摘要
    tags (list): AI 生成的标签列表
    url (str): 可选的 URL
    created_at (datetime): 创建时间
    
    返回：
    str: 创建的页面 ID
    """
    if not created_at:
        created_at = datetime.now()
    
    # 注释掉这部分，因为我们已经在 telegram_service.py 中处理了 PDF URL
    # 检查 URL 是否是 PDF 文件
    # if url and is_pdf_url(url):
    #     logger.info(f"检测到 PDF URL: {url}，将按照学术论文解析")
    #     try:
    #         # 下载 PDF 文件用于解析
    #         pdf_path, _ = download_pdf(url)
    #         if pdf_path:
    #             ... 原有 PDF 处理逻辑 ...
    
    # 确定页面标题
    title = determine_title(content, url, summary)
    
    # 准备标签格式
    tag_objects = []
    for tag in tags:
        tag_objects.append({"name": tag})
    
    # 将内容转换为 Notion 块格式
    content_blocks = convert_to_notion_blocks(content)
    
    # 限制块数量，确保不超过 Notion API 限制
    content_blocks = limit_blocks(content_blocks)
    # 截断摘要，确保不超过 2000 个字符
    truncated_summary = summary[:2000] if summary else ""
    
    # 创建 Notion 页面
    try:
        new_page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Summary": {
                    "rich_text": [
                        {
                            "text": {
                                "content": truncated_summary
                            }
                        }
                    ]
                },
                "Tags": {
                    "multi_select": tag_objects
                },
                "URL": {
                    "url": url if url else None
                },
                "Created": {
                    "date": {
                        "start": created_at.isoformat()
                    }
                }
            },
            children=content_blocks
        )
        logger.info(f"成功创建 Notion 页面：{new_page['id']}")
        return new_page['id']
    
    except Exception as e:
        logger.error(f"创建 Notion 页面时出错：{e}")
        raise

def convert_to_notion_blocks(content):
    """
    将文本内容转换为 Notion 块格式，支持 Markdown 语法
    
    参数：
    content (str): 要转换的文本内容
    
    返回：
    list: Notion 块对象列表
    """
    import re
    
    # Notion API 文本块长度限制
    MAX_TEXT_LENGTH = 2000
    
    # 如果内容为空，返回简单段落
    if not content or len(content.strip()) == 0:
        return [
            {
                "object": "block",
                "paragraph": {
                    "rich_text": [{"text": {"content": ""}}]
                }
            }
        ]
    
    # 将内容分成行
    lines = content.split("\n")
    blocks = []
    
    i = 0
    current_list_type = None  # 'bulleted' 或 'numbered'
    list_levels = []  # 保存当前层级的列表项信息
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 处理标题 (# 标题)
        header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if header_match:
            # 如果之前在处理列表，结束列表
            current_list_type = None
            list_levels = []
            
            level = len(header_match.group(1))
            heading_text = header_match.group(2)
            
            # 确保标题文本不超过限制
            if len(heading_text) > MAX_TEXT_LENGTH:
                heading_text = heading_text[:MAX_TEXT_LENGTH-3] + "..."
            
            heading_type = f"heading_{level}"
            blocks.append({
                "object": "block",
                heading_type: {
                    "rich_text": parse_markdown_formatting(heading_text)
                }
            })
            i += 1
            continue
        
        # 处理列表项，支持多级列表
        # 检查列表项的缩进级别
        list_match = re.match(r'^(\s*)[-*]\s+(.+)$', line)
        if list_match:
            indent = len(list_match.group(1))
            list_text = list_match.group(2)
            
            # 确定列表级别 (基于缩进)
            indent_level = indent // 2  # 假设每级缩进为 2 个空格
            
            # 更新列表级别信息
            if current_list_type != 'bulleted' or indent_level != len(list_levels):
                # 新的列表类型或新的缩进级别
                current_list_type = 'bulleted'
                
                # 调整 list_levels 以匹配当前级别
                if indent_level > len(list_levels):
                    # 增加缩进级别
                    while len(list_levels) < indent_level:
                        list_levels.append('bulleted')
                else:
                    # 减少缩进级别
                    list_levels = list_levels[:indent_level]
                list_levels.append('bulleted')
            
            # 分割长列表项
            for chunk in split_text(list_text, MAX_TEXT_LENGTH):
                # 根据缩进级别创建嵌套结构
                block = {
                    "object": "block",
                    "bulleted_list_item": {
                        "rich_text": parse_markdown_formatting(chunk)
                    }
                }
                
                # 处理子项
                if indent_level > 0:
                    # 添加缩进信息
                    block["bulleted_list_item"]["color"] = "default"
                
                blocks.append(block)
            i += 1
            continue
        
        # 处理数字列表项，支持多级列表
        num_list_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
        if num_list_match:
            indent = len(num_list_match.group(1))
            num = num_list_match.group(2)
            list_text = num_list_match.group(3)
            
            # 确定列表级别 (基于缩进)
            indent_level = indent // 2  # 假设每级缩进为 2 个空格
            
            # 更新列表级别信息
            if current_list_type != 'numbered' or indent_level != len(list_levels):
                current_list_type = 'numbered'
                
                # 调整 list_levels 以匹配当前级别
                if indent_level > len(list_levels):
                    # 增加缩进级别
                    while len(list_levels) < indent_level:
                        list_levels.append('numbered')
                else:
                    # 减少缩进级别
                    list_levels = list_levels[:indent_level]
                list_levels.append('numbered')
            
            # 分割长列表项
            for chunk in split_text(list_text, MAX_TEXT_LENGTH):
                # 创建编号列表项
                block = {
                    "object": "block",
                    "numbered_list_item": {
                        "rich_text": parse_markdown_formatting(chunk)
                    }
                }
                
                # 处理子项
                if indent_level > 0:
                    # 添加缩进信息
                    block["numbered_list_item"]["color"] = "default"
                
                blocks.append(block)
            i += 1
            continue
        
        # 如果遇到空行或其他非列表项，重置列表状态
        if not line:
            current_list_type = None
            list_levels = []
        
        # 处理引用块 (> 引用)
        quote_match = re.match(r'^>\s+(.+)$', line)
        if quote_match:
            # 结束之前的列表
            current_list_type = None
            list_levels = []
            
            quote_text = quote_match.group(1)
            
            # 分割长引用
            for chunk in split_text(quote_text, MAX_TEXT_LENGTH):
                blocks.append({
                    "object": "block",
                    "quote": {
                        "rich_text": parse_markdown_formatting(chunk)
                    }
                })
            i += 1
            continue
        
        # 处理代码块 (```language 代码 ```)
        if line.startswith("```"):
            # 结束之前的列表
            current_list_type = None
            list_levels = []
            
            code_lang = line[3:].strip()
            code_content = []
            i += 1
            
            while i < len(lines) and not lines[i].strip().endswith("```"):
                code_content.append(lines[i])
                i += 1
            
            if i < len(lines):  # 找到了结束标记
                code_text = "\n".join(code_content)
                blocks.append({
                    "object": "block",
                    "code": {
                        "language": code_lang if code_lang else "plain text",
                        "rich_text": [{"text": {"content": code_text}}]
                    }
                })
                i += 1
                continue
        
        # 处理表格行 (| 列 1 | 列 2 | 列 3 |)
        table_match = re.match(r'^\s*\|(.+)\|\s*$', line)
        if table_match:
            # 检测到表格，但 Notion API 当前有一些限制，我们先跳过它
            # 在未来的版本可以处理表格转换
            current_list_type = None
            list_levels = []
            
            # 提取表格行的内容
            cells = [cell.strip() for cell in table_match.group(1).split('|')]
            
            # 把表格行转为普通文本
            table_line = "| " + " | ".join(cells) + " |"
            blocks.append({
                "object": "block",
                "paragraph": {
                    "rich_text": [{"text": {"content": table_line}}]
                }
            })
            i += 1
            continue
        
        # 处理普通段落
        if line:
            # 结束之前的列表
            current_list_type = None
            list_levels = []
            
            # 分割长段落
            for chunk in split_text(line, MAX_TEXT_LENGTH):
                blocks.append({
                    "object": "block",
                    "paragraph": {
                        "rich_text": parse_markdown_formatting(chunk)
                    }
                })
        else:
            # 空行，添加空段落
            blocks.append({
                "object": "block",
                "paragraph": {
                    "rich_text": []
                }
            })
        
        i += 1
    
    return blocks

def limit_blocks(blocks, max_blocks=100):
    """
    限制 Notion 块的数量和内容长度，确保不超过 API 限制
    
    参数：
    blocks (list): Notion 块列表
    max_blocks (int): 最大块数量，默认为 100（Notion API 限制）
    
    返回：
    list: 限制后的块列表
    """
    if not blocks:
        return []
        
    MAX_TEXT_LENGTH = 2000  # Notion API 文本长度限制
    limited_blocks = []
    blocks_processed = 0
    
    # 留出一个位置给可能的截断提示块
    actual_max_blocks = max_blocks - 1
    
    # 处理所有块，确保每个块的内容不超过限制
    for block in blocks:
        # 如果已经处理了最大数量的块，直接退出循环
        if len(limited_blocks) >= actual_max_blocks:
            logger.warning(f"达到最大块限制 ({actual_max_blocks})，停止处理其余 {len(blocks) - blocks_processed} 个块")
            break
            
        blocks_processed += 1
        block_type = block.get("object", "block")
        
        # 处理不同类型的块
        if block_type == "block":
            # 获取块类型（paragraph, heading_x, code 等）
            content_type = list(block.keys())[0] if block else None
            if not content_type or content_type == "object":
                content_type = list(block.keys())[1] if len(block.keys()) > 1 else None
            
            if content_type:
                # 处理代码块（特别需要注意，因为它们通常包含较长文本）
                if content_type == "code" and "rich_text" in block["code"]:
                    code_content = ""
                    if block["code"]["rich_text"] and "text" in block["code"]["rich_text"][0]:
                        code_content = block["code"]["rich_text"][0]["text"].get("content", "")
                    
                    # 如果代码内容超出限制，分割成多个代码块
                    if len(code_content) > MAX_TEXT_LENGTH:
                        language = block["code"].get("language", "plain text")
                        # 分割代码内容
                        code_chunks = []
                        for i in range(0, len(code_content), MAX_TEXT_LENGTH):
                            chunk = code_content[i:i+MAX_TEXT_LENGTH]
                            code_chunks.append({
                                "object": "block",
                                "code": {
                                    "language": language,
                                    "rich_text": [{"text": {"content": chunk}}]
                                }
                            })
                        
                        # 确保添加的代码块不会超过限制
                        remaining_slots = actual_max_blocks - len(limited_blocks)
                        if len(code_chunks) > remaining_slots:
                            limited_blocks.extend(code_chunks[:remaining_slots])
                            logger.warning(f"代码块过长，只保留了前 {remaining_slots} 个代码块")
                            break  # 退出循环，添加截断提示
                        else:
                            limited_blocks.extend(code_chunks)
                    else:
                        limited_blocks.append(block)
                
                # 处理段落、标题和其他文本块
                elif content_type in ["paragraph", "heading_1", "heading_2", "heading_3", 
                                    "bulleted_list_item", "numbered_list_item", "quote", "callout"]:
                    rich_text_key = content_type
                    if rich_text_key in block and "rich_text" in block[rich_text_key]:
                        rich_texts = block[rich_text_key]["rich_text"]
                        
                        # 计算总文本长度
                        total_length = sum(len(rt.get("text", {}).get("content", "")) for rt in rich_texts if "text" in rt)
                        
                        if total_length > MAX_TEXT_LENGTH:
                            # 如果总长度超出限制，创建新的简化文本块
                            combined_text = "".join(rt.get("text", {}).get("content", "") for rt in rich_texts if "text" in rt)
                            text_chunks = []
                            
                            # 分割文本并创建多个块
                            for i in range(0, len(combined_text), MAX_TEXT_LENGTH):
                                chunk = combined_text[i:i+MAX_TEXT_LENGTH]
                                new_block = {
                                    "object": "block",
                                    content_type: {
                                        "rich_text": [{"text": {"content": chunk}}]
                                    }
                                }
                                
                                # 保留原始块的其他属性（如颜色）
                                for key, value in block[content_type].items():
                                    if key != "rich_text":
                                        new_block[content_type][key] = value
                                        
                                text_chunks.append(new_block)
                            
                            # 确保添加的文本块不会超过限制
                            remaining_slots = actual_max_blocks - len(limited_blocks)
                            if len(text_chunks) > remaining_slots:
                                limited_blocks.extend(text_chunks[:remaining_slots])
                                logger.warning(f"文本块过长，只保留了前 {remaining_slots} 个文本块")
                                break  # 退出循环，添加截断提示
                            else:
                                limited_blocks.extend(text_chunks)
                        else:
                            limited_blocks.append(block)
                else:
                    # 其他类型的块直接添加
                    limited_blocks.append(block)
            else:
                limited_blocks.append(block)
        else:
            limited_blocks.append(block)
    
    # 检查是否需要添加截断提示
    if blocks_processed < len(blocks) or len(limited_blocks) >= actual_max_blocks:
        # 确保我们始终有空间添加警告块
        if len(limited_blocks) >= max_blocks:
            # 移除一个块来腾出空间
            limited_blocks.pop()
        
        # 添加截断警告
        limited_blocks.append({
            "object": "block",
            "callout": {
                "rich_text": [{"text": {"content": f"内容过长，已截断显示 ({len(limited_blocks)} / {len(blocks)} 块)。完整内容请参考原始文档。"}}],
                "icon": {"emoji": "⚠️"},
                "color": "yellow_background"
            }
        })
        
        logger.warning(f"内容过多 ({len(blocks)} 块)，已截断至 {len(limited_blocks)} 块")
    
    # 最终确保块数量不超过限制
    if len(limited_blocks) > max_blocks:
        logger.error(f"致命错误：限制后块数量 ({len(limited_blocks)}) 仍然超过 Notion API 限制 ({max_blocks})")
        return limited_blocks[:max_blocks]
    
    return limited_blocks

def parse_markdown_formatting(text):
    """
    解析文本中的 Markdown 格式并转换为 Notion rich_text 格式
    
    支持：
    - **加粗**
    - *斜体*
    - ~~删除线~~
    - `代码`
    - [链接](URL)
    - [内容](https://notion.so/PAGE_ID) 作为 Notion 页面链接
    
    参数：
    text (str): 包含 Markdown 格式的文本
    
    返回：
    list: Notion rich_text 对象列表
    """
    import re
    
    # 如果文本为空，返回空列表
    if not text:
        return []
    
    # 创建一个结果列表
    result = []
    
    # 使用一个更精确的方法来处理格式化文本
    # 1. 首先识别所有特殊格式的位置和类型
    formats = []
    
    # 定义正则表达式模式
    patterns = [
        # Notion 页面链接 [text](https://notion.so/pageid)
        (r'\[(.+?)\]\(https://notion\.so/([a-zA-Z0-9]+)\)', 'notion_page'),
        # 普通链接 [text](url)
        (r'\[(.+?)\]\((?!https://notion\.so/)(.+?)\)', 'link'),
        # 加粗 **text**
        (r'\*\*(.+?)\*\*', 'bold'),
        # 斜体 *text*
        (r'\*(.+?)\*', 'italic'),
        # 删除线 ~~text~~
        (r'~~(.+?)~~', 'strikethrough'),
        # 代码 `text`
        (r'`(.+?)`', 'code')
    ]
    
    # 查找所有格式标记的位置
    for pattern, format_type in patterns:
        for match in re.finditer(pattern, text):
            start, end = match.span()
            content = match.group(1)  # 格式内的实际文本
            
            # 处理不同类型的链接
            if format_type == 'link':
                url = match.group(2)
                formats.append((start, end, format_type, content, url))
            elif format_type == 'notion_page':
                page_id = match.group(2)
                formats.append((start, end, format_type, content, page_id))
            else:
                formats.append((start, end, format_type, content, None))
    
    # 2. 按照起始位置排序格式标记
    formats.sort(key=lambda x: x[0])
    
    # 3. 处理文本，避免重复
    if not formats:
        # 没有格式，直接返回纯文本
        return [{"text": {"content": text}}]
    
    # 处理有格式的文本
    last_end = 0
    processed = []  # 用来跟踪已处理的文本范围
    
    for start, end, format_type, content, link_data in formats:
        # 检查这个区域是否已被处理
        if any(s <= start < e or s < end <= e for s, e in processed):
            continue
        
        # 添加格式标记前的普通文本
        if start > last_end:
            plain_text = text[last_end:start]
            if plain_text:
                result.append({"text": {"content": plain_text}})
        
        # 添加格式化文本
        if format_type == 'notion_page':
            # 创建页面引用/提及
            result.append({
                "mention": {
                    "type": "page",
                    "page": {
                        "id": link_data
                    }
                },
                "plain_text": content,
                "href": f"https://notion.so/{link_data}"
            })
        else:
            # 标准文本格式
            rich_text = {
                "text": {"content": content}
            }
            
            if format_type == 'link' and url:
                rich_text["text"]["link"] = {"url": url}
            
            # 设置文本的格式注释
            annotations = {"bold": False, "italic": False, "strikethrough": False, "code": False}
            if format_type in annotations:
                annotations[format_type] = True
            rich_text["annotations"] = annotations
            
            result.append(rich_text)
        
        # 更新已处理的范围
        processed.append((start, end))
        last_end = end
    
    # 添加最后一段普通文本
    if last_end < len(text):
        result.append({"text": {"content": text[last_end:]}})
    
    return result

def split_text(text, max_length):
    """
    将文本分割成不超过最大长度的块
    
    参数：
    text (str): 要分割的文本
    max_length (int): 每块的最大长度
    
    返回：
    list: 文本块列表
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    for i in range(0, len(text), max_length):
        # 如果不是第一块，尽量在句子或单词边界分割
        if i > 0 and i + max_length < len(text):
            # 尝试在句子结束处分割（句号、问号、感叹号后面）
            end = min(i + max_length, len(text))
            break_point = max(text.rfind('. ', i, end), 
                             text.rfind('? ', i, end),
                             text.rfind('! ', i, end))
            
            # 如果没有找到句子结束，尝试在空格处分割
            if break_point < i:
                break_point = text.rfind(' ', i, end)
            
            # 如果仍然没有找到合适的分割点，则强制在最大长度处分割
            if break_point < i:
                break_point = i + max_length - 1
            else:
                # 包含分隔符
                break_point += 1
                
            chunks.append(text[i:break_point])
            i = break_point - 1  # 减 1 是因为循环会加回来
        else:
            chunks.append(text[i:i + max_length])
    
    return chunks

def determine_title(content, url, summary):
    """基于内容、URL 和摘要确定标题"""
    # 如果内容很短，直接使用内容作为标题
    if len(content) <= 100:
        return content
    
    # 如果有 URL 和摘要，使用摘要的第一句
    # if url and summary:
    #     first_sentence = summary.split(".")[0]
    #     # 确保标题长度不超过 50 个字符
    #     if len(first_sentence) > 50:
    #         return first_sentence[:47] + "..."
    #     return first_sentence + "..."
    
    # 默认使用内容的前一部分作为标题
    return analyze_content(content)["title"]

def get_weekly_entries(days=7):
    """
    获取过去几天内添加的所有条目
    
    参数：
    days (int): 要检索的天数
    
    返回：
    list: Notion 页面对象列表
    """
    from datetime import datetime, timedelta
    
    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 查询 Notion 数据库
    try:
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "and": [
                    {
                        "property": "Created",
                        "date": {
                            "on_or_after": start_date.isoformat()
                        }
                    }
                ]
            },
            sorts=[
                {
                    "property": "Created",
                    "direction": "ascending"
                }
            ]
        )
        
        return response["results"]
    
    except Exception as e:
        logger.error(f"查询 Notion 数据库时出错：{e}")
        raise

def create_weekly_report(title, content):
    """
    创建周报页面
    
    参数：
    title (str): 周报标题
    content (str): 周报内容，可以包含 [引用文本](ref:页面 ID) 格式的引用
    
    返回：
    str: 创建的页面 URL
    """
    try:
        # 将内容中的引用格式 [标题](ref:页面 ID) 转换为 Notion 内链格式
        logger.info("处理周报中的页面引用...")
        processed_content = process_notion_references(content)
        
        # 将内容转换为 Notion block 格式，支持内链
        blocks = convert_to_notion_blocks(processed_content)
        
        # 创建页面
        new_page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Tags": {
                    "multi_select": [{"name": "周报"}]
                },
                "Created": {
                    "date": {
                        "start": datetime.now().isoformat()
                    }
                }
            },
            children=blocks
        )
        
        page_id = new_page['id']
        logger.info(f"成功创建周报页面：{page_id}")
        
        # 返回页面 URL
        return f"https://notion.so/{page_id.replace('-', '')}"
    
    except Exception as e:
        logger.error(f"创建周报页面时出错：{e}")
        raise

def process_notion_references(content):
    """
    处理文本中的 Notion 引用标记，转换为 Notion 链接格式
    支持格式：[引用文本](ref:页面 ID)
    
    参数：
    content (str): 包含 [引用文本](ref:页面 ID) 格式引用的文本
    
    返回：
    str: 转换后的文本，引用转为 Notion 可识别的内链格式
    """
    import re
    
    # 查找格式为 [引用文本](ref:页面 ID) 的引用
    pattern = r'\[(.*?)\]\(ref:([a-zA-Z0-9-]+)\)'
    
    def replace_ref(match):
        text = match.group(1)
        page_id = match.group(2)
        
        # 返回 Notion 页面链接格式 - 这会被 convert_to_notion_blocks 函数进一步处理
        # 确保 ID 格式正确（移除连字符，因为 Notion URL 中不使用）
        clean_id = page_id.replace('-', '')
        return f"[{text}](https://notion.so/{clean_id})"
    
    # 替换所有匹配项
    processed_text = re.sub(pattern, replace_ref, content)
    
    # 记录处理情况
    original_refs_count = len(re.findall(pattern, content))
    processed_refs_count = len(re.findall(r'\[(.*?)\]\(https://notion\.so/[a-zA-Z0-9]+\)', processed_text))
    
    logger.info(f"处理了 {original_refs_count} 个引用，转换了 {processed_refs_count} 个 Notion 内链")
    
    return processed_text

def generate_weekly_content(entries):
    """
    根据本周条目生成周报内容，并自动创建内链引用
    
    参数：
    entries (list): 本周 Notion 页面对象列表
    
    返回：
    str: 格式化的周报内容，包含内链引用
    """
    content = []
    content.append("# 本周内容总结\n")
    
    # 按日期分组
    entries_by_date = {}
    for entry in entries:
        # 跳过周报本身
        if "Tags" in entry["properties"] and any(tag.get("name") == "周报" 
                                               for tag in entry["properties"]["Tags"].get("multi_select", [])):
            continue
            
        # 获取条目创建日期
        created_date = None
        if "Created" in entry["properties"] and entry["properties"]["Created"].get("date"):
            date_str = entry["properties"]["Created"]["date"].get("start")
            if date_str:
                created_date = date_str.split("T")[0]  # 仅保留日期部分 YYYY-MM-DD
        
        if not created_date:
            created_date = "未知日期"
        
        if created_date not in entries_by_date:
            entries_by_date[created_date] = []
        
        entries_by_date[created_date].append(entry)
    
    # 按日期排序
    for date in sorted(entries_by_date.keys()):
        content.append(f"## {date}\n")
        
        # 添加每个条目的摘要和内链
        for entry in entries_by_date[date]:
            # 获取条目标题
            title = "无标题"
            if "Name" in entry["properties"] and entry["properties"]["Name"].get("title"):
                title_objects = entry["properties"]["Name"]["title"]
                if title_objects and "plain_text" in title_objects[0]:
                    title = title_objects[0]["plain_text"]
                elif title_objects and "text" in title_objects[0] and "content" in title_objects[0]["text"]:
                    title = title_objects[0]["text"]["content"]
            
            # 获取条目摘要
            summary = ""
            if "Summary" in entry["properties"] and entry["properties"]["Summary"].get("rich_text"):
                summary_objects = entry["properties"]["Summary"]["rich_text"]
                if summary_objects and "plain_text" in summary_objects[0]:
                    summary = summary_objects[0]["plain_text"]
                elif summary_objects and "text" in summary_objects[0] and "content" in summary_objects[0]["text"]:
                    summary = summary_objects[0]["text"]["content"]
            
            # 尝试获取内容块以提取更多详细信息
            try:
                page_content = notion.blocks.children.list(block_id=entry["id"])
                content_text = extract_notion_block_content(page_content.get("results", []))
                
                # 如果提取到内容，使用内容的前一部分作为摘要展示
                if content_text and not summary:
                    summary = truncate_text(content_text, 150)  # 限制摘要长度
            except Exception as e:
                logger.warning(f"提取页面内容时出错：{e}")
            
            # 截断摘要
            if len(summary) > 150:
                summary = summary[:147] + "..."
            
            # 生成包含内链的摘要行
            page_id = entry["id"]
            
            # 使用 ref: 格式，方便后续使用 process_notion_references 处理
            content.append(f"- [{title}](ref:{page_id}): {summary}")
        
        content.append("")  # 添加空行分隔不同日期的内容
    
    # 添加结尾，等待 AI 生成的总结
    content.append("# AI 周报总结\n")
    content.append("_以下内容由 AI 自动生成_\n")
    
    return "\n".join(content)

def extract_notion_block_content(blocks):
    """
    从 Notion 块中提取文本内容
    
    参数：
    blocks (list): Notion 块列表
    
    返回：
    str: 提取的文本内容
    """
    content = []
    
    for block in blocks:
        block_type = block.get("type")
        if not block_type:
            continue
            
        block_data = block.get(block_type)
        if not block_data:
            continue
            
        # 处理不同类型的块
        if block_type == "paragraph":
            text = extract_rich_text(block_data.get("rich_text", []))
            if text:
                content.append(text)
        elif block_type in ["heading_1", "heading_2", "heading_3"]:
            text = extract_rich_text(block_data.get("rich_text", []))
            if text:
                # 添加标题标记
                prefix = "#" * int(block_type[-1])
                content.append(f"{prefix} {text}")
        elif block_type == "bulleted_list_item":
            text = extract_rich_text(block_data.get("rich_text", []))
            if text:
                content.append(f"- {text}")
        elif block_type == "numbered_list_item":
            text = extract_rich_text(block_data.get("rich_text", []))
            if text:
                content.append(f"1. {text}")  # 简化处理，所有项目都用 1.
        elif block_type == "quote":
            text = extract_rich_text(block_data.get("rich_text", []))
            if text:
                content.append(f"> {text}")
        elif block_type == "callout":
            text = extract_rich_text(block_data.get("rich_text", []))
            if text:
                icon = ""
                if "icon" in block_data and "emoji" in block_data["icon"]:
                    icon = block_data["icon"]["emoji"] + " "
                content.append(f"> {icon}{text}")
        elif block_type == "code":
            text = extract_rich_text(block_data.get("rich_text", []))
            language = block_data.get("language", "")
            if text:
                content.append(f"```{language}\n{text}\n```")
                
    return "\n".join(content)

def extract_rich_text(rich_text):
    """
    从富文本数组中提取纯文本
    
    参数：
    rich_text (list): Notion 富文本对象列表
    
    返回：
    str: 提取的纯文本
    """
    if not rich_text:
        return ""
        
    return "".join([rt.get("plain_text", "") for rt in rich_text])

def create_auto_weekly_report():
    """
    自动创建包含本周所有条目的周报
    
    返回：
    str: 创建的周报页面 URL
    """
    # 获取本周日期范围
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    week_number = today.isocalendar()[1]
    
    # 创建周报标题
    title = f"周报 {today.year} 第{week_number}周 ({start_of_week.strftime('%m.%d')}-{end_of_week.strftime('%m.%d')})"
    
    # 获取本周条目
    entries = get_weekly_entries(days=7)
    
    # 生成周报内容
    content = generate_weekly_content(entries)
    
    # 创建周报
    report_url = create_weekly_report(title, content)
    
    logger.info(f"成功创建周报：{title} ({report_url})")
    return report_url

def add_to_todo_database(content, created_at=None):
    """
    将待办事项添加到 Notion 待办事项数据库
    
    参数：
    content (str): 待办事项内容
    created_at (datetime): 创建时间
    
    返回：
    str: 创建的页面 ID
    """
    if not NOTION_TODO_DATABASE_ID:
        logger.error("未设置待办事项数据库 ID")
        raise ValueError("未设置待办事项数据库 ID")
    
    if not created_at:
        created_at = datetime.now()
    
    # 截取标题
    title = truncate_text(content, 100)
    
    try:
        new_page = notion.pages.create(
            parent={"database_id": NOTION_TODO_DATABASE_ID},
            properties={
                "Name": {
                    "title": [{"text": {"content": title}}]
                },
                "Status": {
                    "select": {"name": "待办"}
                },
                "Priority": {
                    "select": {"name": "中"}
                },
                "Created": {
                    "date": {"start": created_at.isoformat()}
                }
            },
            children=[
                {
                    "object": "block",
                    "paragraph": {
                        "rich_text": [{"text": {"content": content}}]
                    }
                }
            ]
        )
        logger.info(f"成功创建待办事项：{new_page['id']}")
        return new_page['id']
    
    except Exception as e:
        logger.error(f"创建待办事项时出错：{e}")
        raise

def get_existing_dois():
    """
    从 Notion 论文数据库中获取所有已存在的 DOI
    
    返回：
    set: 已存在的 DOI 集合
    """
    if not NOTION_PAPERS_DATABASE_ID:
        logger.error("未设置论文数据库 ID")
        return set()
    
    try:
        # 检查数据库是否有 DOI 字段
        db_info = notion.databases.retrieve(database_id=NOTION_PAPERS_DATABASE_ID)
        if "DOI" not in db_info.get('properties', {}):
            logger.warning("论文数据库中没有 DOI 字段，无法检查重复")
            return set()
        
        # 查询所有条目
        existing_dois = set()
        start_cursor = None
        has_more = True
        
        while has_more:
            response = notion.databases.query(
                database_id=NOTION_PAPERS_DATABASE_ID,
                start_cursor=start_cursor,
                page_size=100,  # 每页最多获取 100 条
                filter={
                    "property": "DOI",
                    "rich_text": {
                        "is_not_empty": True
                    }
                }
            )
            
            # 提取 DOI
            for page in response["results"]:
                if "DOI" in page["properties"]:
                    rich_text = page["properties"]["DOI"].get("rich_text", [])
                    if rich_text and "plain_text" in rich_text[0]:
                        doi = rich_text[0]["plain_text"].strip().lower()
                        if doi:
                            existing_dois.add(doi)
            
            # 检查是否有更多数据
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
            
            if has_more:
                # 避免请求过于频繁
                time.sleep(0.5)
        
        logger.info(f"从 Notion 中获取到 {len(existing_dois)} 个已同步的 DOI")
        return existing_dois
    
    except Exception as e:
        logger.error(f"获取已存在的 DOI 时出错：{e}")
        return set()

def add_to_papers_database(title, analysis, created_at=None, pdf_url=None, metadata=None, zotero_id=None):
    """
    将论文分析添加到论文数据库
    
    参数：
    title (str): 论文标题
    analysis (dict): 论文分析结果，包含详细分析和简洁摘要
    created_at (datetime): 创建时间
    pdf_url (str): 原始 PDF URL
    metadata (dict, optional): 其他元数据，如作者、DOI、发表日期等
    zotero_id (str, optional): Zotero 条目 ID，作为备用标识符
    
    返回：
    str: 创建的页面 ID
    """
    if not NOTION_PAPERS_DATABASE_ID:
        logger.error("未设置论文数据库 ID")
        raise ValueError("未设置论文数据库 ID")
    
    if not created_at:
        created_at = datetime.now()
    
    # 准备基础属性
    properties = {
        "Name": {
            "title": [{"text": {"content": title}}]
        },
        "Created": {
            "date": {"start": created_at.isoformat()}
        }
    }
    
    # 如果有 Zotero ID，作为备用标识符添加到属性中
    if zotero_id:
        properties["ZoteroID"] = {
            "rich_text": [{"text": {"content": zotero_id}}]
        }
    
    # 如果有元数据，添加到属性中
    if metadata:
        # 处理元数据并添加到相应的字段
        properties = add_paper_metadata_to_properties(properties, metadata)
    
    # 如果有 PDF URL，添加到属性中
    if pdf_url:
        properties["URL"] = {
            "url": pdf_url
        }
    
    # 将简要摘要放入 Abstract 属性
    if analysis.get('brief_summary'):
        # 截断摘要，确保不超过 2000 个字符 (Notion API 限制)
        truncated_summary = analysis.get('brief_summary', '')[:2000]
        properties["Abstract"] = {
            "rich_text": [{"text": {"content": truncated_summary}}]
        }
    
    # 准备内容块
    children = []
    
    # 添加洞察部分
    if analysis.get('insight'):
        children.append({
            "object": "block",
            "callout": {
                "rich_text": [{"text": {"content": analysis.get('insight', '')[:150]}}],
                "icon": {"emoji": "💡"}
            }
        })
    
    # 添加详细分析块
    if analysis.get('details'):
        # 转换详细分析为 Notion 块格式
        details_blocks = convert_to_notion_blocks(analysis.get('details', ''))
        children.extend(details_blocks)
    
    try:
        # 首先确保数据库有需要的属性
        ensure_papers_database_properties()
        
        # 创建页面
        new_page = notion.pages.create(
            parent={"database_id": NOTION_PAPERS_DATABASE_ID},
            properties=properties,
            children=children
        )
        logger.info(f"成功创建论文分析：{new_page['id']}")
        return new_page['id']
    
    except Exception as e:
        logger.error(f"创建论文分析时出错：{e}")
        raise

def add_paper_metadata_to_properties(properties, metadata):
    """
    将论文元数据添加到 Notion 属性中
    
    参数：
    properties (dict): 现有属性字典
    metadata (dict): 元数据字典
    
    返回：
    dict: 更新后的属性字典
    """
    # 添加作者（多选文本）
    if metadata.get('authors'):
        authors = metadata['authors']
        if isinstance(authors, list) or authors:
            # 转为逗号分隔的字符串
            author_text = ", ".join(authors)
            properties["Authors"] = {
                "rich_text": [{"text": {"content": author_text[:2000]}}]  # Notion API 限制
            }
    
    # 添加期刊/出版物（文本）
    if metadata.get('publication'):
        properties["Publication"] = {
            "rich_text": [{"text": {"content": metadata['publication'][:2000]}}]
        }
    
    # 添加发布日期
    if metadata.get('date'):
        try:
            # 尝试解析日期字符串
            from dateutil.parser import parse
            date_obj = parse(metadata['date'])
            properties["PublishDate"] = {
                "date": {"start": date_obj.strftime('%Y-%m-%d')}
            }
        except:
            # 如果无法解析，使用原始字符串
            properties["PublishYear"] = {
                "rich_text": [{"text": {"content": metadata['date'][:100]}}]
            }
    
    # 添加 DOI
    if metadata.get('doi'):
        properties["DOI"] = {
            "rich_text": [{"text": {"content": metadata['doi'][:100]}}]
        }
    
    # 添加 Zotero 链接
    if metadata.get('zotero_link'):
        properties["ZoteroLink"] = {
            "url": metadata['zotero_link']
        }
    
    # 添加标签（多选）
    if metadata.get('tags') and isinstance(metadata['tags'], list):
        multi_select_tags = []
        for tag in metadata['tags'][:10]:  # 限制数量
            multi_select_tags.append({"name": tag[:100]})  # 限制长度
        
        if multi_select_tags:
            properties["Tags"] = {
                "multi_select": multi_select_tags
            }
    
    return properties

def ensure_papers_database_properties():
    """
    确保论文数据库拥有所需的所有属性/字段
    第一次使用时会初始化数据库结构
    """
    try:
        # 获取当前数据库结构
        db_info = notion.databases.retrieve(database_id=NOTION_PAPERS_DATABASE_ID)
        existing_properties = db_info.get('properties', {})
        
        # 检查并添加缺失的属性
        required_properties = {
            "Abstract": {"rich_text": {}},
            "Authors": {"rich_text": {}},
            "Publication": {"rich_text": {}},
            "PublishDate": {"date": {}},
            "PublishYear": {"rich_text": {}},  # 备用字段，当无法解析日期时使用
            "DOI": {"rich_text": {}},
            "Tags": {"multi_select": {}},
            "ZoteroLink": {"url": {}},
            "URL": {"url": {}}
        }
        
        missing_properties = {}
        for prop_name, prop_config in required_properties.items():
            if prop_name not in existing_properties:
                missing_properties[prop_name] = prop_config
        
        # 如果有缺失的属性，更新数据库结构
        if missing_properties:
            logger.info(f"正在添加缺失的论文数据库属性：{', '.join(missing_properties.keys())}")
            notion.databases.update(
                database_id=NOTION_PAPERS_DATABASE_ID,
                properties=missing_properties
            )
            logger.info("数据库结构已更新")
    
    except Exception as e:
        logger.warning(f"检查/更新数据库结构时出错：{e}")
        # 继续执行，因为这不是致命错误

def is_pdf_url(url):
    """
    检查 URL 是否为 PDF 文件链接
    
    参数：
    url (str): 要检查的 URL
    
    返回：
    bool: 如果 URL 指向 PDF 文件则返回 True，否则返回 False
    """
    # URL 路径以 .pdf 结尾
    if re.search(r'\.pdf(\?.*)?$', url, re.IGNORECASE):
        return True
        
    try:
        # 检查 HTTP 头中的内容类型
        head_response = requests.head(url, allow_redirects=True, timeout=5)
        content_type = head_response.headers.get('Content-Type', '')
        if 'application/pdf' in content_type.lower():
            return True
            
        # 如果 HEAD 请求没有返回内容类型，尝试 GET 请求的前几个字节
        if 'content-type' not in head_response.headers:
            response = requests.get(url, stream=True, timeout=5)
            # 读取前几个字节检查 PDF 魔数 %PDF-
            content_start = response.raw.read(5).decode('latin-1', errors='ignore')
            if content_start.startswith('%PDF-'):
                return True
            response.close()
    except Exception as e:
        logger.warning(f"检查 PDF URL 时出错：{e}")
    
    return False

def download_pdf(url):
    """
    从 URL 下载 PDF 文件到临时位置
    
    参数：
    url (str): PDF 文件的 URL
    
    返回：
    tuple: (下载的 PDF 文件路径，文件大小 (字节)), 下载失败则返回 (None, 0)
    """
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            # 获取文件大小
            file_size = int(response.headers.get('content-length', 0))
            logger.info(f"PDF 文件大小：{file_size / (1024 * 1024):.2f} MB")
            
            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)
            
            # 将内容写入临时文件
            downloaded_size = 0
            with open(temp_path, 'wb') as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)
                    downloaded_size += len(chunk)
            
            logger.info(f"PDF 文件已下载到：{temp_path}")
            return temp_path, downloaded_size or file_size
        else:
            logger.error(f"下载 PDF 失败，状态码：{response.status_code}")
            return None, 0
    except Exception as e:
        logger.error(f"下载 PDF 时出错：{e}")
        return None, 0

def check_paper_exists_in_notion(doi: str) -> bool:
    """
    检查论文是否已存在于 Notion 数据库中（通过 DOI）
    
    参数：
        doi: 论文的 DOI
        
    返回：
        bool: 如果论文已存在则返回 True，否则返回 False
    """
    if not doi:
        return False
    
    try:
        # 使用全局 notion 客户端，而不是调用函数
        # notion = get_notion_client() 这行会导致错误
        
        # 查询 Notion 数据库
        response = notion.databases.query(
            database_id=NOTION_PAPERS_DATABASE_ID,
            filter={
                "property": "DOI",
                "rich_text": {
                    "equals": doi
                }
            }
        )
        
        # 如果找到结果，则论文已存在
        return len(response.get('results', [])) > 0
    
    except Exception as e:
        logger.error(f"检查论文是否存在时出错：{e}")
        return False

def ensure_papers_database_properties():
    """确保论文数据库有所有必要的属性"""
    try:
        notion = get_notion_client()
        
        # 获取当前数据库结构
        database = notion.databases.retrieve(database_id=NOTION_PAPERS_DATABASE_ID)
        current_properties = database.get('properties', {})
        
        # 检查是否需要更新
        needs_update = False
        new_properties = {}
        
        # 检查并添加 DOI 属性
        if 'DOI' not in current_properties:
            new_properties['DOI'] = {
                "rich_text": {}
            }
            needs_update = True
        
        # 检查并添加其他必要属性（以下是示例）
        required_properties = {
            "Authors": {"rich_text": {}},
            "Publication": {"rich_text": {}},
            "Publication Date": {"date": {}},
            "URL": {"url": {}},
            "Tags": {"multi_select": {}}
        }
        
        for prop_name, prop_config in required_properties.items():
            if prop_name not in current_properties:
                new_properties[prop_name] = prop_config
                needs_update = True
        
        # 如果需要更新，执行更新操作
        if needs_update:
            logger.info(f"正在更新论文数据库属性...")
            notion.databases.update(
                database_id=NOTION_PAPERS_DATABASE_ID,
                properties=new_properties
            )
            logger.info(f"论文数据库属性已更新")
    
    except Exception as e:
        logger.error(f"确保论文数据库属性时出错：{e}")

def get_existing_zotero_ids() -> set[str]:
    """
    获取已存在于 Notion 数据库中的 ZoteroID 列表
    
    返回：
        set[str]: ZoteroID 集合
    """
    try:
        notion_service = get_notion_service()
        
        # 查询数据库中所有包含 Zotero ID 的记录
        results = []
        has_more = True
        next_cursor = None
        
        # 获取所有页面，可能需要分页
        while has_more:
            query_params = {
                "filter": {
                    "property": "ZoteroID",
                    "rich_text": {
                        "is_not_empty": True
                    }
                }
            }
            
            if next_cursor:
                query_params["start_cursor"] = next_cursor
                
            response = notion_service.client.databases.query(
                database_id=notion_service.papers_database_id,
                **query_params
            )
            
            results.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")
        
        # 提取所有 Zotero ID
        zotero_ids = set()
        for page in results:
            try:
                zotero_id_prop = page.get("properties", {}).get("ZoteroID", {})
                if zotero_id_prop and "rich_text" in zotero_id_prop:
                    rich_text = zotero_id_prop.get("rich_text", [])
                    if rich_text:
                        zotero_id = rich_text[0].get("plain_text", "").strip()
                        if zotero_id:
                            zotero_ids.add(zotero_id)
            except Exception as e:
                logger.warning(f"提取 Zotero ID 时出错：{e}")
                
        logger.info(f"从 Notion 数据库中获取到 {len(zotero_ids)} 个 Zotero ID")
        return zotero_ids
    
    except Exception as e:
        logger.error(f"获取现有 Zotero ID 列表时出错：{e}")
        return set()
