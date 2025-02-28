# Docker Compose 使用指南

本文档提供了使用 Docker Compose 管理 TG-Notion Bot 的完整指南。

## 基本命令

### 1. 启动服务

```bash
# 首次启动或重建镜像
docker-compose up --build

# 后台运行
docker-compose up -d

# 仅启动已存在的容器
docker-compose start
```

### 2. 停止服务

```bash
# 停止并移除容器
docker-compose down

# 仅停止容器不移除
docker-compose stop
```

### 3. 查看日志

```bash
# 查看实时日志
docker-compose logs -f

# 仅查看最近50行
docker-compose logs --tail=50
```

### 4. 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart tg-notion-bot
```

### 5. 查看容器状态

```bash
docker-compose ps
```

### 6. 一键更新，并启动新镜像

```
# 全流程更新命令（推荐）
docker compose pull && docker compose up -d --build
```

## 环境配置

### 创建 .env 文件

在项目根目录创建 `.env` 文件，内容如下：

```
# Telegram 配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_USER_IDS=12345678,98765432

# Notion 配置
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
NOTION_TODO_DATABASE_ID=your_todo_database_id
NOTION_PAPERS_DATABASE_ID=your_papers_database_id

# Gemini API 配置
GEMINI_API_KEY=your_gemini_api_key

# 周报配置
WEEKLY_REPORT_DAY=Friday
WEEKLY_REPORT_HOUR=18
```

## 多环境配置

可以为不同环境创建不同的配置文件：

### 开发环境

创建 `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  tg-notion-bot:
    build: 
      context: .
      dockerfile: Dockerfile
    env_file:
      - .env.dev
    volumes:
      - .:/app
      - ./logs:/app/logs
    restart: "no"
```

启动开发环境:

```bash
docker-compose -f docker-compose.dev.yml up
```

### 生产环境

创建 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  tg-notion-bot:
    image: tgnotionbotacr.azurecr.io/tg-notion-bot:latest
    env_file:
      - .env.prod
    volumes:
      - ./logs:/app/logs
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "20m"
        max-file: "10"
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

启动生产环境:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 使用 Alpine 版本解决构建问题

如果默认 Dockerfile 构建遇到问题，可以使用 Alpine 版本：

```bash
# 使用 Alpine 版本构建
docker-compose -f docker-compose.yml -f docker-compose.alpine.yml up -d
```

创建 `docker-compose.alpine.yml`:

```yaml
version: '3.8'

services:
  tg-notion-bot:
    build:
      context: .
      dockerfile: Dockerfile.alpine
```

## 持久化和备份

### 自动备份日志

创建备份脚本 `backup-logs.sh`:

```bash
#!/bin/bash
TODAY=$(date +%Y-%m-%d)
mkdir -p backups
tar -czf backups/logs-$TODAY.tar.gz logs/
```

设置定时执行：

```bash
# 添加到 crontab
0 0 * * * /path/to/backup-logs.sh
```

## 常见问题排查

### 1. 容器无法启动

检查日志：

```bash
docker-compose logs
```

### 2. 网络问题

检查网络设置：

```bash
docker network ls
docker network inspect bot-network
```

### 3. 使用 Docker Compose V2

如果您使用的是 Docker Compose V2，命令格式略有不同：

```bash
docker compose up -d  # 注意没有连字符
```

### 4. 重建容器和镜像

完全重建时使用：

```bash
docker-compose down --rmi all --volumes
docker-compose up --build -d
```

## 最佳实践

1. **安全管理**: 永远不要将 `.env` 文件提交到版本控制系统
2. **资源限制**: 使用 `deploy` 配置限制容器资源使用
3. **日志轮转**: 配置日志驱动以避免磁盘空间耗尽
4. **健康检查**: 添加健康检查以监控服务状态
5. **备份策略**: 定期备份关键数据
