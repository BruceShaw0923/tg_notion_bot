# 可以尝试不同的基础镜像版本，如果一个不可用，可以尝试另一个

# 选项1: 使用Python 3.10 slim版本
FROM python:3.10-slim

WORKDIR /app

# 复制Docker专用依赖文件
COPY docker-requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r docker-requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 设置时区
RUN apt-get update && apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 运行应用
CMD ["python", "main.py"]
