"""
Zotero 条目模块 - 处理 Zotero 条目和元数据
"""

import logging
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .client import get_zotero_service

# 配置日志
logger = logging.getLogger(__name__)


def get_recent_items(
    collection_id: Optional[str] = None,
    filter_type: str = "count",
    value: int = 5,
) -> List[Dict]:
    """
    获取最近的条目，支持按数量或天数筛选

    参数：
        collection_id: 可选的 Zotero 收藏集 ID
        filter_type: 过滤类型，可以是"count"或"days"
        value: 对应过滤类型的值（篇数或天数）

    返回：
        最近的条目列表
    """
    service = get_zotero_service()
    try:
        if filter_type == "count":
            if collection_id:
                items = service.zot.collection_items(collection_id, limit=value)
            else:
                items = service.zot.items(limit=value)
        else:  # filter_type == "days"
            cutoff_date = datetime.now() - timedelta(days=value)
            if collection_id:
                items = service.zot.collection_items(collection_id)
            else:
                items = service.zot.items()
            items = [
                item
                for item in items
                if datetime.fromisoformat(
                    item["data"]["dateAdded"].replace("Z", "+00:00")
                )
                >= cutoff_date
            ]
        return items
    except Exception as e:
        logger.error(f"Error getting recent items: {str(e)}")
        return []


def extract_metadata(item: Dict) -> Dict:
    """
    从 Zotero 条目中提取元数据

    参数：
        item: Zotero 条目对象

    返回：
        提取的元数据字典
    """
    # 确保函数定义没有 self 参数，与模块级函数一致
    data = item["data"]

    # 提取基本元数据
    metadata = {
        "title": data.get("title", "未知标题"),
        "abstract": data.get("abstractNote", ""),
        "doi": data.get("DOI", ""),
        "url": data.get("url", ""),
        "date_added": data.get("dateAdded", ""),
        "item_type": data.get("itemType", ""),
        "authors": [],
        "publication": data.get("publicationTitle", ""),
        "date": data.get("date", "")[:4] if data.get("date") else "",
        "tags": [tag["tag"] for tag in data.get("tags", [])],
        "zotero_id": item["key"],
        "collections": data.get("collections", []),
        # 文件名信息将在后续处理中添加
        "attachment_info": [],
    }

    # 提取作者
    creators = data.get("creators", [])
    for creator in creators:
        if creator.get("creatorType") == "author":
            name = []
            if creator.get("firstName"):
                name.append(creator.get("firstName", ""))
            if creator.get("lastName"):
                name.append(creator.get("lastName", ""))
            full_name = " ".join(name).strip()
            if full_name:
                metadata["authors"].append(full_name)

    # 转换作者列表为字符串
    metadata["authors_text"] = ", ".join(metadata["authors"])

    return metadata


def get_pdf_attachment(item_key: str) -> Optional[str]:
    """
    获取论文的 PDF 附件路径

    参数：
        item_key: Zotero 条目的键值

    返回：
        PDF 文件的路径，如果不存在则返回 None
    """
    # 确保函数定义没有 self 参数，与模块级函数一致
    service = get_zotero_service()
    pdf_attachment_key = None
    pdf_filename = None

    try:
        # 1. Find the PDF attachment key and filename
        children = service.zot.children(item_key)
        for child in children:
            child_data = child.get("data", {})
            if (
                child_data.get("itemType") == "attachment"
                and child_data.get("contentType") == "application/pdf"
            ):
                pdf_attachment_key = child.get("key")
                pdf_filename = child_data.get("filename") or child_data.get(
                    "title", f"{pdf_attachment_key}.pdf"
                )
                if not pdf_filename.lower().endswith(".pdf"):
                    pdf_filename += ".pdf"
                logger.info(
                    f"Found PDF attachment info for item {item_key}: Key={pdf_attachment_key}, Filename={pdf_filename}"
                )
                break

        if not pdf_attachment_key:
            logger.warning(f"No PDF attachment metadata found for item {item_key}")
            return None

        # --- Primary Method: Try API Download ---
        try:
            logger.info(
                f"Attempting to download PDF via API (Key: {pdf_attachment_key})"
            )
            pdf_content = service.zot.file(pdf_attachment_key)

            if pdf_content:
                logger.info(
                    f"API download successful (Size: {len(pdf_content)} bytes). Saving to temp file."
                )
                # Save API content to temp file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf", prefix=f"{item_key}_api_"
                ) as temp_pdf:
                    temp_pdf.write(pdf_content)
                    temp_file_path = temp_pdf.name
                    logger.info(
                        f"PDF content saved to temporary file via API: {temp_file_path}"
                    )
                    return temp_file_path  # <<< SUCCESS via API
            else:
                logger.warning(
                    f"API download for {pdf_attachment_key} returned empty content. Attempting local fallback."
                )
                # Proceed to fallback

        except Exception as api_e:
            logger.warning(
                f"API download failed for {pdf_attachment_key}: {api_e}. Attempting local fallback."
            )
            # Proceed to fallback

        # --- Fallback Method: Try Local Storage ---
        if (
            pdf_filename
            and service.pdf_storage_path
            and os.path.isdir(service.pdf_storage_path)
        ):
            # Construct the potential path in the *actual* Zotero storage structure
            # Zotero stores files in subdirectories named by the attachment key
            potential_dir = os.path.join(service.pdf_storage_path, pdf_attachment_key)
            source_path = os.path.join(potential_dir, pdf_filename)

            logger.info(f"Attempting local fallback at: {source_path}")

            if os.path.exists(source_path):
                logger.info(
                    f"Found PDF locally at: {source_path}. Copying to temporary location."
                )
                try:
                    # Copy local file to a new temp file
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf", prefix=f"{item_key}_local_"
                    ) as temp_pdf:
                        shutil.copy2(
                            source_path, temp_pdf.name
                        )  # Copy *into* the temp file's path
                        temp_file_path = temp_pdf.name
                        logger.info(
                            f"Successfully copied local file to temp: {temp_file_path}"
                        )
                        return temp_file_path  # <<< SUCCESS via Local Fallback
                except Exception as copy_e:
                    logger.error(
                        f"Failed to copy local file {source_path} to temporary location: {copy_e}"
                    )
                    # Proceed to return None at the end
            else:
                # Sometimes the filename in Zotero metadata doesn't match exactly or the structure is different.
                # Add a simple check directly in the pdf_storage_path as a last resort (less reliable)
                alt_source_path = os.path.join(service.pdf_storage_path, pdf_filename)
                logger.warning(
                    f"Local file not found in key directory: {source_path}. Checking root storage path: {alt_source_path}"
                )
                if os.path.exists(alt_source_path):
                    logger.info(
                        f"Found PDF locally in root storage: {alt_source_path}. Copying to temporary location."
                    )
                    try:
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=".pdf",
                            prefix=f"{item_key}_local_root_",
                        ) as temp_pdf:
                            shutil.copy2(alt_source_path, temp_pdf.name)
                            temp_file_path = temp_pdf.name
                            logger.info(
                                f"Successfully copied local file (from root) to temp: {temp_file_path}"
                            )
                            return (
                                temp_file_path  # <<< SUCCESS via Local Fallback (Root)
                            )
                    except Exception as copy_e:
                        logger.error(
                            f"Failed to copy local file {alt_source_path} to temporary location: {copy_e}"
                        )
                else:
                    logger.warning(
                        "Local fallback failed: File not found in key directory or root storage path."
                    )
                    # Proceed to return None at the end
        elif not pdf_filename:
            logger.warning(
                "Local fallback skipped: PDF filename could not be determined from metadata."
            )
        elif not service.pdf_storage_path:
            logger.warning(
                "Local fallback skipped: ZOTERO_PDF_PATH environment variable not set."
            )
        elif not os.path.isdir(service.pdf_storage_path):
            logger.warning(
                f"Local fallback skipped: Configured PDF storage path is not a valid directory: {service.pdf_storage_path}"
            )
            # Proceed to return None at the end

    except Exception as outer_e:
        # Catch errors in finding children etc.
        logger.error(f"Error processing attachments for item {item_key}: {outer_e}")

    # If neither API nor local worked, or an outer error occurred
    logger.error(f"Could not obtain PDF for item {item_key} via API or local fallback.")
    return None
