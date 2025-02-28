# Docker 启动指南

本指南介绍如何启动 Docker 服务和容器，适用于项目 `tg_notion_bot`。

## 1. 启动 Docker 服务

### macOS

1. 打开 Docker Desktop 应用

   - 在访达(Finder)中，打开"应用程序"文件夹
   - 双击 Docker.app 启动
   - 等待状态栏中的 Docker 图标显示 "Docker Desktop is running"
2. 命令行确认 Docker 是否运行：

   ```bash
   docker info
   ```

### Windows

1. 打开 Docker Desktop 应用

   - 从开始菜单搜索并启动 Docker Desktop
   - 等待系统托盘中的 Docker 图标停止动画
2. 命令行确认 Docker 是否运行：

   ```bash
   docker info
   ```

### Linux

1. 启动 Docker 服务：

   ```bash
   sudo systemctl start docker
   # 或者在较旧的系统上
   sudo service docker start
   ```
2. 确认 Docker 是否运行：

   ```bash
   sudo systemctl status docker
   # 或者
   docker info
   ```

## 2. 启动现有的 tg_notion_bot 容器

如果已经创建了容器但当前停止状态：

```bash
# 查看所有容器（包括已停止的）
docker ps -a

# 启动已存在的容器
docker start tg_notion_bot

# 查看容器日志
docker logs -f tg_notion_bot
```

## 3. 首次创建并启动 tg_notion_bot 容器

如果是首次部署：

### 使用脚本启动（推荐）

项目提供了自动化脚本，可以一键构建镜像和启动容器：

```bash
# 进入项目目录
cd /Users/wangruochen/1-Tools/tg_notion_bot

# 赋予脚本执行权限
chmod +x update.sh

# 运行脚本
./update.sh
```

### 手动启动

```bash
# 进入项目目录
cd /Users/wangruochen/1-Tools/tg_notion_bot

# 构建镜像
docker build -t tg_notion_bot:latest .

# 创建并启动容器
docker run -d --name tg_notion_bot \
  -v "$(pwd)/config":/app/config \
  -v "$(pwd)/logs":/app/logs \
  --restart unless-stopped \
  tg_notion_bot:latest
```

### 使用 Docker Compose 启动

```bash
# 进入项目目录
cd /Users/wangruochen/1-Tools/tg_notion_bot

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 4. 检查容器运行状态

```bash
# 列出运行中的容器
docker ps

# 查看容器详细信息
docker inspect tg_notion_bot

# 查看容器日志
docker logs tg_notion_bot

# 持续查看日志
docker logs -f tg_notion_bot
```

## 5. 容器管理常用命令

```bash
# 停止容器
docker stop tg_notion_bot

# 重启容器
docker restart tg_notion_bot

# 删除容器
docker rm tg_notion_bot

# 强制删除运行中的容器
docker rm -f tg_notion_bot
```

## 6. 常见问题

### Docker 服务无法启动

- **macOS/Windows**:

  - 重启 Docker Desktop
  - 检查系统资源是否充足
- **Linux**:

  ```bash
  # 查看详细错误
  journalctl -xu docker.service
  ```

### 容器启动失败

- 查看错误日志：

  ```bash
  docker logs tg_notion_bot
  ```
- 检查配置文件是否正确
- 检查挂载目录是否存在
- 检查权限是否正确

### 挂载卷错误

如果出现 "Mounts denied" 错误，参考 [troubleshooting.md](./troubleshooting.md) 文档中的解决方案。

## 7. 重要提醒

- 确保在启动容器前已经准备好必要的配置文件
- macOS 和 Windows 用户需要在 Docker Desktop 的设置中配置足够的资源
- 首次启动可能需要较长时间来拉取镜像
