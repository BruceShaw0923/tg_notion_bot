from datetime import datetime
import json
from utils.helpers import truncate_text

class Message:
    """消息模型类"""
    
    def __init__(self, content, url="", created_at=None):
        self.content = content
        self.url = url
        self.created_at = created_at or datetime.now()
        self.summary = ""
        self.tags = []
    
    def set_analysis(self, summary, tags):
        """设置 AI 分析结果"""
        self.summary = summary
        self.tags = tags
    
    def to_dict(self):
        """转换为字典表示"""
        return {
            "content": self.content,
            "url": self.url,
            "created_at": self.created_at.isoformat(),
            "summary": self.summary,
            "tags": self.tags
        }
    
    def to_json(self):
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建消息对象"""
        msg = cls(
            content=data.get("content", ""),
            url=data.get("url", ""),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else None
        )
        msg.summary = data.get("summary", "")
        msg.tags = data.get("tags", [])
        return msg
    
    @classmethod
    def from_json(cls, json_str):
        """从 JSON 字符串创建消息对象"""
        return cls.from_dict(json.loads(json_str))
    
    def get_title(self, max_length=100):
        """获取消息标题"""
        if not self.content:
            return "无标题"
            
        # 如果有摘要，优先使用摘要的第一句作为标题
        if self.summary:
            first_sentence = self.summary.split(".")[0]
            if first_sentence and len(first_sentence) < max_length:
                return truncate_text(first_sentence, max_length)
        
        # 使用内容的第一行作为标题
        first_line = self.content.split("\n")[0]
        return truncate_text(first_line, max_length)
