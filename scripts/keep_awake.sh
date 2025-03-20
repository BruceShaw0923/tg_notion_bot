#!/bin/bash

# 确保脚本具有执行权限
# 使用前请运行: chmod +x keep_awake.sh

# 配置系统允许网络唤醒
echo "配置系统允许网络唤醒..."
sudo pmset -a tcpkeepalive 1
sudo pmset -a womp 1

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "Docker未运行，正在启动Docker..."
    open -a Docker
    
    # 等待Docker启动
    while ! docker info > /dev/null 2>&1; do
        echo "等待Docker启动..."
        sleep 5
    done
    echo "Docker已启动"
fi

# 添加当前机器到可唤醒设备列表
echo "将当前机器添加到可唤醒设备列表..."
INTERFACE=$(networksetup -listallhardwareports | grep -A 1 "Wi-Fi\|Ethernet" | grep -o "en[0-9]" | head -n 1)
if [ -n "$INTERFACE" ]; then
    MAC_ADDRESS=$(networksetup -getmacaddress $INTERFACE | awk '{print $3}')
    echo "网络接口: $INTERFACE, MAC地址: $MAC_ADDRESS"
    sudo pmset -a wakeonlan 1
else
    echo "未找到网络接口"
fi

echo "已完成网络唤醒配置"
echo "请确保在系统偏好设置->节能中勾选'唤醒以供网络访问'"
echo "脚本执行完毕，系统现在应该能通过网络请求唤醒"
