# 使用官方Python镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app/

# 安装依赖 - 使用docker特定的requirements
RUN pip install --no-cache-dir -r docker-requirements.txt && \
    # 明确安装SOCKS支持
    pip install --no-cache-dir PySocks requests[socks] && \
    # 禁用Python警告
    pip install --no-cache-dir --upgrade urllib3==1.26.15 && \
    # 确保pyzotero已安装（使用引号避免shell解析版本号）
    pip install --no-cache-dir "pyzotero>=1.5.5" && \
    # 验证安装
    python -c "import socks; import pyzotero; print('PySocks and pyzotero installed successfully')"

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"

# 创建日志目录
RUN mkdir -p /app/logs

# 添加可执行权限到启动脚本
RUN chmod +x /app/start.sh

# 运行应用
CMD ["/app/start.sh"]
