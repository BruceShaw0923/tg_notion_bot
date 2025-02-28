# 部署TG-Notion机器人到Azure云

## 前提条件

- Azure账号
- 已安装Azure CLI
- Docker已安装（用于构建镜像）
- 配置好的.env文件（不要提交到代码库）

## 方案1: 部署到Azure容器实例(ACI)

### 步骤1: 登录Azure

```bash
az login
```

### 步骤2: 创建资源组（如果需要）

```bash
az group create --name tg-notion-bot-rg --location eastasia
```

### 步骤3: 创建Azure容器注册表(ACR)

```bash
az acr create --resource-group tg-notion-bot-rg --name tgnotionbotacr --sku Basic
az acr login --name tgnotionbotacr
```

### 步骤4: 构建并推送Docker镜像

```bash
docker build -t tgnotionbotacr.azurecr.io/tg-notion-bot:latest .
docker push tgnotionbotacr.azurecr.io/tg-notion-bot:latest
```

### 步骤5: 启用管理员账户（用于ACI部署）

```bash
az acr update --name tgnotionbotacr --admin-enabled true
az acr credential show --name tgnotionbotacr
```

### 步骤6: 使用环境变量部署ACI容器

```bash
az container create \
  --resource-group tg-notion-bot-rg \
  --name tg-notion-bot \
  --image tgnotionbotacr.azurecr.io/tg-notion-bot:latest \
  --registry-login-server tgnotionbotacr.azurecr.io \
  --registry-username tgnotionbotacr \
  --registry-password <acr-password> \
  --environment-variables \
    TELEGRAM_BOT_TOKEN=<your-token> \
    NOTION_API_KEY=<your-key> \
    ALLOWED_USER_IDS=<user-ids> \
    GEMINI_API_KEY=<gemini-key>
```

## 方案2: 部署到Azure App Service

### 步骤1: 创建App Service计划

```bash
az appservice plan create --name tg-notion-bot-plan --resource-group tg-notion-bot-rg --sku B1 --is-linux
```

### 步骤2: 创建Web应用

```bash
az webapp create \
  --resource-group tg-notion-bot-rg \
  --plan tg-notion-bot-plan \
  --name tg-notion-bot-app \
  --deployment-container-image-name tgnotionbotacr.azurecr.io/tg-notion-bot:latest
```

### 步骤3: 配置容器注册表信息

```bash
az webapp config container set \
  --name tg-notion-bot-app \
  --resource-group tg-notion-bot-rg \
  --docker-custom-image-name tgnotionbotacr.azurecr.io/tg-notion-bot:latest \
  --docker-registry-server-url https://tgnotionbotacr.azurecr.io \
  --docker-registry-server-user tgnotionbotacr \
  --docker-registry-server-password <acr-password>
```

### 步骤4: 设置环境变量

```bash
az webapp config appsettings set \
  --resource-group tg-notion-bot-rg \
  --name tg-notion-bot-app \
  --settings \
    TELEGRAM_BOT_TOKEN=<your-token> \
    NOTION_API_KEY=<your-key> \
    ALLOWED_USER_IDS=<user-ids> \
    GEMINI_API_KEY=<gemini-key>
```

### 步骤5: 配置持续部署

```bash
az webapp deployment container config --enable-cd true \
  --name tg-notion-bot-app \
  --resource-group tg-notion-bot-rg
```

## 监控和维护

### 查看日志

```bash
# 容器实例
az container logs --resource-group tg-notion-bot-rg --name tg-notion-bot

# App Service
az webapp log tail --name tg-notion-bot-app --resource-group tg-notion-bot-rg
```

### 重启服务

```bash
# 容器实例
az container restart --name tg-notion-bot --resource-group tg-notion-bot-rg

# App Service
az webapp restart --name tg-notion-bot-app --resource-group tg-notion-bot-rg
```

## 安全注意事项

- 不要在代码中硬编码敏感信息
- 使用Azure Key Vault存储机密
- 考虑设置网络安全规则
- 定期更新依赖和Docker镜像
