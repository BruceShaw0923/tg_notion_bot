import logging
import re

logger = logging.getLogger(__name__)

def markdown_to_notion_blocks(markdown_text):
    """
    将 Markdown 文本转换为 Notion 可用的 blocks 格式
    
    参数：
    markdown_text (str): Markdown 格式的文本
    
    返回：
    list: Notion blocks 列表
    """
    blocks = []
    lines = markdown_text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 跳过空行
        if not line:
            i += 1
            continue
        
        # 处理标题
        if line.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif line.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        
        # 处理列表项
        elif line.startswith('- ') or line.startswith('* '):
            list_items = []
            while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                list_text = lines[i].strip()[2:]
                
                # 处理加粗和斜体
                rich_text = parse_markdown_formatting(list_text)
                
                list_items.append({
                    "bulleted_list_item": {
                        "rich_text": rich_text
                    }
                })
                i += 1
            
            for item in list_items:
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    **item
                })
            continue
        
        # 处理普通段落
        else:
            # 处理加粗和斜体
            rich_text = parse_markdown_formatting(line)
            
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text
                }
            })
        
        i += 1
    
    return blocks

def parse_markdown_formatting(text):
    """
    解析 Markdown 文本中的格式（加粗、斜体等）
    
    参数：
    text (str): 包含 Markdown 格式的文本
    
    返回：
    list: Notion rich_text 列表
    """
    rich_text = []
    
    # 匹配加粗、斜体和链接
    pattern = r'(\*\*.*?\*\*)|(\*.*?\*)|(\[.*?\]\(.*?\))'
    
    # 分割文本
    parts = re.split(pattern, text)
    parts = [p for p in parts if p is not None]
    
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:  # 跳过空字符串
            i += 1
            continue
            
        # 处理加粗
        if part.startswith('**') and part.endswith('**'):
            rich_text.append({
                "type": "text",
                "text": {"content": part[2:-2]},
                "annotations": {"bold": True}
            })
        
        # 处理斜体
        elif part.startswith('*') and part.endswith('*'):
            rich_text.append({
                "type": "text",
                "text": {"content": part[1:-1]},
                "annotations": {"italic": True}
            })
        
        # 处理链接
        elif part.startswith('[') and '](' in part and part.endswith(')'):
            link_text = part[1:part.index('](')]
            link_url = part[part.index('](')+2:-1]
            rich_text.append({
                "type": "text",
                "text": {"content": link_text, "link": {"url": link_url}}
            })
        
        # 处理普通文本
        else:
            rich_text.append({
                "type": "text",
                "text": {"content": part}
            })
        
        i += 1
    
    return rich_text
