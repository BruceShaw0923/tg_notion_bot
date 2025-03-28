import logging

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


def extract_url_content(url):
    """
    从 URL 中提取网页内容并转换为 Markdown 格式

    参数：
    url (str): 需要提取内容的 URL

    返回：
    str: 提取并转换为 Markdown 格式的网页内容
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # 获取网页内容
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # 提取标题
        title = soup.title.string if soup.title else ""

        # 提取正文内容 - 首先尝试找到主要内容区域
        main_content = None
        for selector in [
            "article",
            "main",
            "div#content",
            "div.content",
            "div.post",
            "div.article",
            "body",
        ]:
            if selector.startswith("div"):
                # 处理带 class 或 id 的选择器
                attrs = {}
                if "." in selector:
                    tag, cls = selector.split(".")
                    attrs["class"] = cls
                elif "#" in selector:
                    tag, id = selector.split("#")
                    attrs["id"] = id
                element = soup.find(tag, attrs)
            else:
                element = soup.find(selector)

            if element:
                main_content = element
                break

        # 如果没找到主要内容区域，使用整个 body
        if not main_content:
            main_content = soup.body if soup.body else soup

        # 从内容中移除不需要的元素
        for element in main_content.find_all(
            ["script", "style", "nav", "footer", "header"]
        ):
            element.extract()

        # 将 HTML 转换为 Markdown
        markdown_content = md(str(main_content), heading_style="ATX")

        # 格式化内容，确保标题在最前面
        formatted_content = f"# {title}\n\n{markdown_content}"

        # 移除内容截断代码 - 让 Notion Service 的分批处理机制处理长内容

        logger.info(f"成功提取并转换 URL 内容，长度：{len(formatted_content)} 字符")
        return formatted_content

    except Exception as e:
        logger.error(f"提取 URL 内容时出错：{e}")
        return f"无法提取 URL 内容：{url}. 错误：{str(e)}"
