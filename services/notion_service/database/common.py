import logging
import time
from datetime import datetime, timedelta

import pytz

from config import NOTION_DATABASE_ID
from services.gemini_service import analyze_content
from utils.helpers import truncate_text

from ..client import get_notion_client
from ..content_converter import convert_to_notion_blocks

logger = logging.getLogger(__name__)
notion = get_notion_client()


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
        # 修复时区问题
        created_at = created_at.astimezone(pytz.timezone("Asia/Shanghai"))

    # 确定页面标题
    title = determine_title(content, url, summary)

    # 准备标签格式
    tag_objects = []
    for tag in tags:
        tag_objects.append({"name": tag})

    # 将内容转换为 Notion 块格式
    content_blocks = convert_to_notion_blocks(content)

    # 截断摘要，确保不超过 2000 个字符
    truncated_summary = summary[:2000] if summary else ""

    # 创建 Notion 页面
    try:
        # 块的数量
        blocks_count = len(content_blocks)

        # 如果块数量超过 API 限制 (100)，我们需要分批添加
        if blocks_count > 100:
            logger.info(f"内容包含 {blocks_count} 个块，超过 API 限制，将分批添加")

            # 先创建没有子块的页面
            new_page = notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Summary": {
                        "rich_text": [{"text": {"content": truncated_summary}}]
                    },
                    "Tags": {"multi_select": tag_objects},
                    "URL": {"url": url if url else None},
                    "Created": {"date": {"start": created_at.isoformat()}},
                },
            )

            # 获取新创建页面的 ID
            page_id = new_page["id"]

            # 然后分批添加子块
            append_blocks_in_batches(page_id, content_blocks)

            logger.info(
                f"成功创建 Notion 页面并分批添加 {blocks_count} 个块：{page_id}"
            )
            return page_id
        else:
            # 如果块数量不超过限制，直接创建带有子块的页面
            new_page = notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Summary": {
                        "rich_text": [{"text": {"content": truncated_summary}}]
                    },
                    "Tags": {"multi_select": tag_objects},
                    "URL": {"url": url if url else None},
                    "Created": {"date": {"start": created_at.isoformat()}},
                },
                children=content_blocks,
            )

            logger.info(
                f"成功创建 Notion 页面：{new_page['id']}，包含 {len(content_blocks)} 个块"
            )
            return new_page["id"]

    except Exception as e:
        logger.error(f"创建 Notion 页面时出错：{e}")
        raise


def append_blocks_in_batches(page_id, blocks, batch_size=100):
    """
    分批将块添加到 Notion 页面

    参数：
    page_id (str): Notion 页面 ID
    blocks (list): 要添加的块列表
    batch_size (int): 每批最大块数，默认 100 (Notion API 限制)

    返回：
    bool: 是否成功添加所有块
    """
    total_blocks = len(blocks)
    batches_count = (total_blocks + batch_size - 1) // batch_size  # 向上取整

    logger.info(f"开始分批添加 {total_blocks} 个块，分为 {batches_count} 批")

    for i in range(0, total_blocks, batch_size):
        batch = blocks[i : i + batch_size]
        batch_num = i // batch_size + 1

        try:
            # 添加一批块
            notion.blocks.children.append(block_id=page_id, children=batch)

            logger.info(
                f"成功添加第 {batch_num}/{batches_count} 批，包含 {len(batch)} 个块"
            )

            # 添加短暂延迟避免请求过于频繁
            if batch_num < batches_count:
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"添加第 {batch_num}/{batches_count} 批块时出错：{e}")

            # 尝试细分批次重试
            if len(batch) > 10:
                logger.info("尝试将批次细分后重试...")
                smaller_batch_size = len(batch) // 2
                success = append_blocks_in_batches(page_id, batch, smaller_batch_size)
                if not success:
                    return False
            else:
                # 如果批次已经很小仍然失败，则跳过该批次
                logger.warning(f"跳过添加失败的 {len(batch)} 个块")

    return True


# TODO: 重构 determine_title
def determine_title(content, url, summary):
    """基于内容、URL  and 摘要确定标题"""
    # 如果内容很短，直接使用内容作为标题
    if len(content) <= 100:
        return content

    # 如果有 URL  and 摘要，使用摘要的第一句
    # if url  and summary:
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
                        "date": {"on_or_after": start_date.isoformat()},
                    }
                ]
            },
            sorts=[{"property": "Created", "direction": "ascending"}],
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
        blocks_count = len(blocks)

        # 如果块数量超过 API 限制，分批添加
        if blocks_count > 100:
            logger.info(f"周报包含 {blocks_count} 个块，超过 API 限制，将分批添加")

            # 先创建没有子块的页面
            new_page = notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Tags": {"multi_select": [{"name": "周报"}]},
                    "Created": {"date": {"start": datetime.now().isoformat()}},
                },
            )

            # 获取新创建页面的 ID
            page_id = new_page["id"]

            # 然后分批添加子块
            append_blocks_in_batches(page_id, blocks)

            logger.info(f"成功创建周报页面并分批添加 {blocks_count} 个块：{page_id}")
        else:
            new_page = notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Tags": {"multi_select": [{"name": "周报"}]},
                    "Created": {"date": {"start": datetime.now().isoformat()}},
                },
                children=blocks,
            )

            page_id = new_page["id"]
            logger.info(f"成功创建周报页面：{page_id}，包含 {len(blocks)} 个块")

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
    pattern = r"\[(.*?)\]\(ref:([a-zA-Z0-9-]+)\)"

    def replace_ref(match):
        text = match.group(1)
        page_id = match.group(2)

        # 返回 Notion 页面链接格式 - 这会被 convert_to_notion_blocks 函数进一步处理
        # 确保 ID 格式正确（移除连字符，因为 Notion URL 中不使用）
        clean_id = page_id.replace("-", "")
        return f"[{text}](https://notion.so/{clean_id})"

    # 替换所有匹配项
    processed_text = re.sub(pattern, replace_ref, content)

    # 记录处理情况
    original_refs_count = len(re.findall(pattern, content))
    processed_refs_count = len(
        re.findall(r"\[(.*?)\]\(https://notion\.so/[a-zA-Z0-9]+\)", processed_text)
    )

    logger.info(
        f"处理了 {original_refs_count} 个引用，转换了 {processed_refs_count} 个 Notion 内链"
    )

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
        if "Tags" in entry["properties"] and any(
            tag.get("name") == "周报"
            for tag in entry["properties"]["Tags"].get("multi_select", [])
        ):
            continue

        # 获取条目创建日期
        created_date = None
        if "Created" in entry["properties"] and entry["properties"]["Created"].get(
            "date"
        ):
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

        # 添加每个条目的摘要 and 内链
        for entry in entries_by_date[date]:
            # 获取条目标题
            title = "无标题"
            if "Name" in entry["properties"] and entry["properties"]["Name"].get(
                "title"
            ):
                title_objects = entry["properties"]["Name"]["title"]
                if title_objects and "plain_text" in title_objects[0]:
                    title = title_objects[0]["plain_text"]
                elif (
                    title_objects
                    and "text" in title_objects[0]
                    and "content" in title_objects[0]["text"]
                ):
                    title = title_objects[0]["text"]["content"]

            # 获取条目摘要
            summary = ""
            if "Summary" in entry["properties"] and entry["properties"]["Summary"].get(
                "rich_text"
            ):
                summary_objects = entry["properties"]["Summary"]["rich_text"]
                if summary_objects and "plain_text" in summary_objects[0]:
                    summary = summary_objects[0]["plain_text"]
                elif (
                    summary_objects
                    and "text" in summary_objects[0]
                    and "content" in summary_objects[0]["text"]
                ):
                    summary = summary_objects[0]["text"]["content"]

            # 尝试获取内容块以提取更多详细信息
            try:
                page_content = notion.blocks.children.list(block_id=entry["id"])
                content_text = extract_notion_block_content(
                    page_content.get("results", [])
                )

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
