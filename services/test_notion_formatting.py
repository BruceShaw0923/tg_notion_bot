import logging
import json
import sys
import os

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 创建一个临时的 mock config 用于测试
class MockConfig:
    NOTION_TOKEN = "test_token"
    NOTION_DATABASE_ID = "test_database_id"
    NOTION_TODO_DATABASE_ID = "test_todo_database_id"
    NOTION_PAPERS_DATABASE_ID = "test_papers_database_id"

# 创建 mock 模块
import types
sys.modules['config'] = types.ModuleType('config')
sys.modules['config'].NOTION_TOKEN = MockConfig.NOTION_TOKEN
sys.modules['config'].NOTION_DATABASE_ID = MockConfig.NOTION_DATABASE_ID
sys.modules['config'].NOTION_TODO_DATABASE_ID = MockConfig.NOTION_TODO_DATABASE_ID
sys.modules['config'].NOTION_PAPERS_DATABASE_ID = MockConfig.NOTION_PAPERS_DATABASE_ID

from notion_service import parse_markdown_formatting, convert_to_notion_blocks

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_markdown_parsing():
    """测试 Markdown 解析功能"""
    test_texts = [
        "普通文本没有格式",
        "这是**加粗的文本**和*斜体的文本*",
        "这里有`代码片段`和~~删除线~~",
        "这是 [一个链接](https://example.com)",
        "混合格式：**加粗文本**中的*斜体*和`代码`以及 [链接](https://example.com)"
    ]
    
    for text in test_texts:
        logger.info(f"原始文本：{text}")
        rich_text = parse_markdown_formatting(text)
        logger.info(f"解析后：{json.dumps(rich_text, indent=2, ensure_ascii=False)}")
        logger.info("---")

def test_block_conversion():
    """测试块转换功能"""
    test_content = """# 这是一级标题
    
## 这是**加粗的**二级标题

这是一个普通段落，包含*斜体*和**加粗**以及`代码`。

- 这是列表项 1
- 这是**加粗的**列表项 2
- 这是带有 [链接](https://example.com) 的列表项

1. 第一项
2. 第二项，*斜体*
3. 第三项，**加粗**

> 这是一个引用块，可以包含**加粗**和*斜体*

```python
# 这是代码块
def hello():
    print("Hello World")
```

最后一段普通文本。
"""
    
    blocks = convert_to_notion_blocks(test_content)
    logger.info(f"转换后的块结构：{json.dumps(blocks, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    logger.info("开始测试 Markdown 解析...")
    test_markdown_parsing()
    
    logger.info("\n开始测试块转换...")
    test_block_conversion()
