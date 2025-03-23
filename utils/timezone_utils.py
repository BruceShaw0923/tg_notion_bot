"""
时区相关的工具函数
确保程序中的日期时间处理一致
"""

from datetime import datetime, timedelta, timezone


def get_utc_now():
    """
    获取当前的 UTC 时间

    返回：
    datetime: 当前 UTC 时间
    """
    return datetime.now(timezone.utc)


def get_utc_past(days=7):
    """
    获取过去指定天数的 UTC 时间

    参数：
    days (int): 过去的天数

    返回：
    datetime: UTC 时间
    """
    return get_utc_now() - timedelta(days=days)


def format_iso8601(dt):
    """
    将 datetime 对象格式化为 ISO 8601 格式字符串

    参数：
    dt (datetime): 要格式化的 datetime 对象

    返回：
    str: ISO 8601 格式字符串
    """
    # 确保 datetime 对象带有时区信息
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_date_range(date, days=7):
    """
    验证日期范围是否合理
    - 确保日期不在未来
    - 确保日期在指定范围内

    参数：
    date (datetime): 要验证的日期
    days (int): 最大允许的天数范围

    返回：
    datetime: 验证后的日期（如果有修正）
    """
    now = get_utc_now()

    # 确保日期不在未来
    if date > now:
        return now - timedelta(days=days)

    # 确保日期不会过早
    earliest_allowed = now - timedelta(days=365)  # 最早允许一年前
    if date < earliest_allowed:
        return now - timedelta(days=days)

    return date
