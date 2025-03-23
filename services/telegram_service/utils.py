import logging
import os
import re

logger = logging.getLogger(__name__)


def extract_metadata_from_filename(filename):
    """
    尝试从文件名提取元数据，适用于常见的学术论文命名模式
    例如：Author_Year_Title.pdf 或 Title_Journal_Year.pdf

    参数：
    filename (str): PDF 文件名

    返回：
    dict: 提取的元数据
    """
    metadata = {}

    # 去除扩展名
    name_only = os.path.splitext(filename)[0]

    # 尝试分割常见分隔符
    parts = re.split(r"[_\-\s]+", name_only)

    # 尝试识别年份
    year_pattern = r"(19|20)\d{2}"
    years = []
    for part in parts:
        if re.match(year_pattern, part):
            years.append(part)

    if years:
        metadata["date"] = years[0]

    return metadata


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
    if metadata.get("title") and not result.get("title"):
        result["title"] = metadata["title"]

    # 添加作者信息
    if metadata.get("authors"):
        result["authors"] = metadata["authors"]

    # 添加 DOI
    if metadata.get("doi"):
        result["doi"] = metadata["doi"]

    # 添加出版信息
    if metadata.get("publication"):
        result["publication"] = metadata["publication"]

    # 添加日期
    if metadata.get("date"):
        result["date"] = metadata["date"]

    # 添加 URL（如果元数据中有而分析中没有）
    if metadata.get("url") and not result.get("url"):
        result["url"] = metadata["url"]

    # 添加摘要（如果元数据中有而分析中没有）
    if metadata.get("abstract") and not result.get("brief_summary"):
        result["brief_summary"] = metadata["abstract"]

    # 添加 Zotero 标签
    if metadata.get("tags"):
        result["zotero_tags"] = metadata["tags"]

    # 添加 Zotero 键值
    if metadata.get("zotero_key"):
        result["zotero_key"] = metadata["zotero_key"]

    return result


def prepare_metadata_for_notion(metadata):
    """
    从 Zotero 元数据准备 Notion 需要的元数据格式

    参数：
    metadata (dict): Zotero 元数据

    返回：
    dict: Notion 格式的元数据
    """
    notion_metadata = {}

    # 处理作者
    if metadata.get("creators"):
        authors = []
        for creator in metadata.get("creators", []):
            if creator.get("firstName") or creator.get("lastName"):
                author = f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
                authors.append(author)
        if authors:
            notion_metadata["authors"] = authors

    # 处理出版物信息
    if metadata.get("publicationTitle"):
        notion_metadata["publication"] = metadata.get("publicationTitle")

    # 处理日期
    if metadata.get("date"):
        notion_metadata["date"] = metadata.get("date")

    # 处理 DOI - 确保保存为小写以便一致性比较
    if metadata.get("DOI"):
        notion_metadata["doi"] = metadata.get("DOI", "").lower().strip()

    # 处理 Zotero 链接
    if metadata.get("zotero_key"):
        notion_metadata["zotero_link"] = (
            f"zotero://select/library/items/{metadata.get('zotero_key')}"
        )

    # 处理标签
    if metadata.get("tags"):
        tags = []
        for tag_obj in metadata.get("tags", []):
            if tag_obj.get("tag"):
                tags.append(tag_obj.get("tag"))
        if tags:
            notion_metadata["tags"] = tags

    return notion_metadata
