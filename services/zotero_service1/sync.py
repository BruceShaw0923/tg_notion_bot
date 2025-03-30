"""
Zotero 同步模块 - 处理 Zotero 到 Notion 的同步
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import services.gemini_service as gemini_service
import services.notion_service as notion_service

from .items import extract_metadata, get_pdf_attachment, get_recent_items

# 配置日志
logger = logging.getLogger(__name__)


def sync_items_to_notion(items: List[Dict]) -> Tuple[int, int, List[str]]:
    """Sync items to Notion"""
    success_count = 0
    skip_count = 0
    errors = []

    for item in items:
        try:
            # 提取完整元数据
            metadata = extract_metadata(item)

            # 记录更详细的元数据信息
            # logger.info(f"Processing paper: {metadata['file_title']}")
            logger.info(
                f"Authors: {', '.join(metadata['authors']) if metadata['authors'] else 'Not available'}"
            )
            logger.info(f"DOI: {metadata['doi'] or 'Not available'}")
            logger.info(f"Publication: {metadata['publication'] or 'Not available'}")
            logger.info(f"Date: {metadata['date'] or 'Not available'}")
            logger.info(f"Tags count: {len(metadata['tags'])}")

            # Check if already exists in Notion
            if notion_service.check_paper_exists_in_notion(
                doi=metadata.get("doi"), zotero_id=metadata.get("zotero_id")
            ):
                logger.info(f"Paper already exists in Notion: {metadata['title']}")
                skip_count += 1
                continue

            # Get PDF attachment
            pdf_path = get_pdf_attachment(item["key"])

            # 使用 Gemini 分析 PDF 内容（如果有 PDF）
            analysis_result = {}
            if pdf_path:
                logger.info(f"Analyzing PDF with Gemini: {pdf_path}")
                analysis_result = gemini_service.analyze_pdf_content(pdf_path)
                if not analysis_result:
                    logger.warning(f"Failed to analyze PDF: {pdf_path}")
                    analysis_result = {
                        "title": metadata["title"],
                        "brief_summary": metadata.get("abstract", ""),
                        "details": f"Failed to analyze PDF. Original abstract: {metadata.get('abstract', '')}",
                        "insight": "PDF analysis failed",
                    }
            else:
                # 如果没有 PDF，使用元数据创建基本分析结果
                logger.info(f"No PDF found, using metadata only: {metadata['title']}")
                analysis_result = {
                    "title": metadata["title"],
                    "brief_summary": metadata.get("abstract", ""),
                    "details": f"No PDF available. Original abstract: {metadata.get('abstract', '')}",
                    "insight": "Based on metadata only",
                }

            # 使用已定义的函数合并 Gemini 分析结果与 Zotero 元数据
            enriched_analysis = gemini_service.enrich_analysis_with_metadata(
                analysis_result, metadata
            )

            # 使用已定义的函数准备 Notion 元数据
            notion_metadata = notion_service.prepare_metadata_for_notion(metadata)

            # 使用 add_to_papers_database 将论文添加到 Notion
            created_at = datetime.fromisoformat(
                item["data"]["dateAdded"].replace("Z", "+00:00")
            )
            page_id = notion_service.add_to_papers_database(
                title=enriched_analysis.get("title", metadata["title"]),
                analysis=enriched_analysis,
                created_at=created_at,
                pdf_url=metadata.get("url", ""),
                metadata=notion_metadata,
                zotero_id=metadata["zotero_id"],
            )

            if page_id:
                success_count += 1
                logger.info(f"Successfully synced to Notion: {metadata['title']}")
            else:
                errors.append(f"Failed to sync: {metadata['title']}")

        except Exception as e:
            logger.error(f"Error processing item: {str(e)}")
            errors.append(
                f"Error processing {item.get('data', {}).get('title', 'Unknown')}: {str(e)}"
            )

    return success_count, skip_count, errors


def format_sync_result(
    success_count: int, skip_count: int, total_count: int, errors: List[str]
) -> str:
    """Format sync result message"""
    message = "Sync completed:\n"
    message += f"✅ Successfully synced: {success_count}\n"
    message += f"⏭️ Skipped (already exists): {skip_count}\n"
    message += f"📊 Total processed: {total_count}\n"

    if errors:
        message += "\n❌ Errors:\n"
        message += "\n".join(errors)

    return message


def sync_papers_to_notion(
    collection_id: Optional[str] = None,
    filter_type: str = "count",
    value: int = 5,
) -> str:
    """Sync papers to Notion with filtering options"""
    items = get_recent_items(collection_id, filter_type, value)
    success_count, skip_count, errors = sync_items_to_notion(items)
    return format_sync_result(success_count, skip_count, len(items), errors)


def sync_recent_papers_by_count(
    collection_id: Optional[str] = None, count: int = 5
) -> str:
    """Sync recent papers by count (legacy API)"""
    return sync_papers_to_notion(collection_id, "count", count)


def sync_recent_papers_by_days(
    collection_id: Optional[str] = None, days: int = 7
) -> str:
    """Sync recent papers by days (legacy API)"""
    return sync_papers_to_notion(collection_id, "days", days)
