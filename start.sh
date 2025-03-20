#!/bin/bash

# 设置环境变量
export DISABLE_TELEGRAM_SSL_VERIFY=true
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

# 启动机器人
python main.py
