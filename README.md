# TG-Notion 机器人

这是一个Telegram与Notion集成的自动化机器人，可以帮助你快速保存信息、链接和文件到Notion数据库。

## 功能特点

- 发送消息自动保存到Notion
- 发送URL自动提取网页内容
- 发送PDF文件自动解析为论文
- 使用#todo标签添加任务到待办事项
- AI自动分析内容并生成摘要和标签
- 支持Zotero论文同步
- 自动生成周报总结

## 项目结构

# TG-Notion Bot

TG-Notion Bot 是一个 Telegram 机器人，集成了 Notion、Zotero 和 Google Gemini 等多种服务，帮助用户高效管理知识和工作流。

## 功能特点

### 基本功能

- 将 Telegram 消息自动保存到 Notion
- 自动提取链接内容并分析
- 使用 #todo 标签快速创建待办事项
- 通过 Google Gemini 自动分析内容并生成摘要

### 论文管理功能

- 从 Zotero 同步论文到 Notion
- 使用 Google Gemini 自动分析论文内容
- 提取论文摘要、关键词和主要观点
- 支持按最新添加或时间范围同步

### 周报功能

- 自动生成周报摘要
- 汇总一周内处理的内容

## 命令列表

### 基本命令

- `/start` - 显示欢迎信息
- `/help` - 显示帮助信息
- `/weekly` - 手动触发生成本周周报

### Zotero 相关命令

- `/collections` - 列出所有 Zotero 收藏集
- `/sync_papers [收藏集ID] [数量]` - 同步最近添加的论文

  - 例如: `/sync_papers ABC12345 10` - 同步指定收藏集的10篇最新论文
  - 例如: `/sync_papers 5` - 同步所有收藏集的5篇最新论文
- `/sync_days [收藏集ID] [天数]` - 同步指定天数内添加的论文

  - 例如: `/sync_days ABC12345 14` - 同步指定收藏集14天内的论文
  - 例如: `/sync_days 3` - 同步所有收藏集3天内的论文

## 使用流程示例

1. **保存笔记**

   - 直接向机器人发送文本消息
   - 机器人会自动分析内容并保存到 Notion
2. **创建待办事项**

   - 发送带有 #todo 标签的消息
   - 例如: "准备明天的会议材料 #todo"
3. **分析网页内容**

   - 发送网页链接
   - 机器人会提取内容并分析保存
4. **同步论文**

   - 使用 `/collections` 查看可用收藏集
   - 使用 `/sync_papers` 或 `/sync_days` 命令同步论文
   - 机器人会自动下载并分析论文内容
5. **生成周报**

   - 周报会自动生成
   - 也可以使用 `/weekly` 手动触发

## 配置要求

使用此机器人需要配置以下环境变量:

- Telegram Bot Token
- Notion API 密钥和数据库 ID
- Zotero API 密钥和用户 ID
- Google Gemini API 密钥

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

# zotero配置
ZOTERO_API_KEY=your_zotero_api_key
ZOTERO_USER_ID=your_zotero_user_id
ZOTERO_FOLDER_ID=your_zotero_folder_id
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
│   ├── gemini_service.py  # AI内容分析服务
│   ├── notion_service.py  # Notion集成服务
│   ├── telegram/          # Telegram机器人服务
│   │   ├── __init__.py    # 导出主要功能
│   │   ├── bot.py         # 机器人初始化和配置
│   │   ├── handlers/      # 消息处理模块
│   │   └── utils.py       # Telegram特有工具函数
│   ├── telegram_service.py # 兼容层
│   ├── url_service.py     # URL内容提取服务
│   └── weekly_report.py   # 周报生成服务
├── utils/             # 通用工具
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

## 项目进度追踪

### 优化

- [X] 周报prompt的优化
- [X] 带有多个链接的文本解析优化
- [X] 多级列表的生成和解析为notion block

新增

- [ ] 图片插入
- [ ] 标签识别，并放入Tags属性
- [ ] epub/书籍通过标签建立图书馆
- [X] 周报建立notion内链
- [X] 把各种prompt放到配置文件里
- [ ] 把微信消息推送至bot
- [X] 把zotero的文件直接推送到bot
- [ ] 部署到Azure

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。

## 联系方式

如有问题或建议，请通过 Telegram 联系机器人管理员。

Happy messaging! 🚀
