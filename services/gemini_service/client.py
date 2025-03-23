"""
Gemini API 客户端模块

处理 Google Gemini API 的配置和初始化
"""

import logging

import google.generativeai as genai

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# 默认初始化
model = None
vision_model = None
GEMINI_AVAILABLE = False


def configure_gemini_api():
    """
    配置 Google Gemini API 并初始化模型

    返回：
        bool: 配置是否成功
    """
    global model, vision_model, GEMINI_AVAILABLE

    try:
        if not GEMINI_API_KEY:
            logger.warning("未设置 GEMINI_API_KEY，Gemini 功能将不可用")
            return False

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-pro-exp-02-05")
        vision_model = genai.GenerativeModel("gemini-2.0-pro-exp-02-05")
        GEMINI_AVAILABLE = True
        logger.info("Gemini API 配置成功")
        return True
    except Exception as e:
        logger.error(f"配置 Gemini API 时出错：{e}")
        GEMINI_AVAILABLE = False
        return False


# 自动初始化
configure_gemini_api()
