# TG-Notion Bot

TG-Notion Bot 是一个自动化工具，可以将 Telegram 消息无缝保存到 Notion 数据库，并使用 Google Gemini AI 进行内容分析。

## 主要功能

* 🤖  **自动保存消息** : 将 Telegram 消息直接保存到 Notion
* 🧠  **AI 内容分析** : 使用 Google Gemini AI 自动生成摘要和标签
* 📄  **PDF 解析** : 解析学术论文 PDF 并提取关键信息
* 🌐  **URL 内容提取** : 自动解析和保存 URL 内容
* ✅  **待办事项管理** : 快速添加任务到 Notion 待办数据库
* 📊  **自动周报生成** : 自动汇总你的每周内容并生成报告
* 🐳  **Docker 支持** : 支持 Docker 容器化部署

## 系统要求

* Python 3.10+
* Telegram Bot API 令牌
* Notion API 令牌和数据库 ID
* Google Gemini API 密钥
* Docker (可选，用于容器部署)

## 快速开始

### 环境变量配置

1. 复制示例环境配置文件:

```
cp .env.example .env
```

2. 编辑 [.env](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-sandbox/workbench/workbench.html) 文件，填入你的 API 密钥和其他配置:

```
# Telegram配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_USER_IDS=your_user_id

# Notion配置
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id
NOTION_TODO_DATABASE_ID=your_todo_database_id
NOTION_PAPERS_DATABASE_ID=your_papers_database_id

# Google Gemini API 配置
GEMINI_API_KEY=your_gemini_api_key

# 周报配置
WEEKLY_REPORT_DAY=Sunday
WEEKLY_REPORT_HOUR=20
```

### 使用 Docker 部署 (推荐)

1. 使用提供的 Docker Compose 启动脚本:

```
chmod +x docker-compose-run.sh./docker-compose-run.sh
```


或手动使用 Docker Compose:

```
docker-compose up -d
```

### 直接部署

1. 安装依赖:

```
pip install -r requirements.txt
```

2. 启动机器人:

```
python main.py
```

## 使用指南

### 基本功能

* 发送任何文本消息到机器人，它会自动保存到 Notion 并生成摘要和标签
* 发送 PDF 文件将解析为学术论文并保存到专用数据库
* 发送纯 URL 会自动提取网页内容
* 使用 `#todo` 标签可以快速添加任务到待办事项数据库

### Telegram 命令列表

* `/start` - 显示欢迎信息和使用说明
* `/help` - 显示帮助信息
* `/weekly` - 手动触发生成本周周报

## 项目目录结构

```
.
├── config.py          # 配置文件
├── main.py            # 主程序
├── models/            # 数据模型
├── services/          # 服务模块
├── utils/             # 工具函数
├── handlers/          # 消息处理程序
├── docs/              # 文档
├── docker-compose.yml # Docker 配置
└── Dockerfile         # Docker 构建文件
```

## 高级部署

详细的部署指南请参考:

* Docker 启动指南
* Docker 命令使用指南
* Azure 云部署指南

## 清理缓存

清理项目中的 Python 缓存文件:

```
python clean_cache.py
```

## 测试

运行自动化测试:

```
python test.py
```

## 常见问题

### 机器人没有响应消息

* 确认你的 [TELEGRAM_BOT_TOKEN](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-sandbox/workbench/workbench.html) 是否正确
* 确认你的用户 ID 已添加到 [ALLOWED_USER_IDS](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-sandbox/workbench/workbench.html) 中
* 检查日志文件 [bot.log](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-sandbox/workbench/workbench.html) 查看详细错误信息

### Notion API 错误

* 确认 [NOTION_TOKEN](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-sandbox/workbench/workbench.html) 和 [NOTION_DATABASE_ID](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-sandbox/workbench/workbench.html) 是否正确
* 验证你的 Notion 集成是否具有数据库访问权限

## 贡献指南

欢迎贡献代码或提交 issue！请确保遵循以下步骤:

1. Fork 仓库
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。

## 联系方式

如有问题或建议，请通过 Telegram 联系机器人管理员。

Happy messaging! 🚀
