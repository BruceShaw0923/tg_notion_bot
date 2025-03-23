import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_url_content(url):
    """
    从 URL 中提取网页内容

    参数：
    url (str): 需要提取内容的 URL

    返回：
    str: 提取的网页内容
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

        # 提取正文内容
        # 首先尝试提取 article 标签
        article = soup.find("article")
        if article:
            content = article.get_text(separator="\n", strip=True)
        else:
            # 如果没有 article 标签，尝试提取主要内容区域
            main_content = (
                soup.find("main")
                or soup.find(id="content")
                or soup.find(class_="content")
            )
            if main_content:
                content = main_content.get_text(separator="\n", strip=True)
            else:
                # 最后尝试提取 body 所有文本，但过滤掉脚本和样式
                for script in soup(["script", "style"]):
                    script.extract()
                content = (
                    soup.body.get_text(separator="\n", strip=True) if soup.body else ""
                )

        # 格式化内容
        formatted_content = f"# {title}\n\n{content}"

        # 如果内容太长，进行截断
        if len(formatted_content) > 10000:
            formatted_content = (
                formatted_content[:10000] + "...\n\n[内容已截断，原始内容过长]"
            )

        return formatted_content

    except Exception as e:
        logger.error(f"提取 URL 内容时出错：{e}")
        return f"无法提取 URL 内容：{url}. 错误：{str(e)}"
