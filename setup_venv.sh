#!/bin/bash
# 创建和配置Python虚拟环境

echo "===== 开始设置Python虚拟环境 ====="

# 确定Python命令
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "错误：找不到Python。请确保已安装Python 3。"
    exit 1
fi

# 检查Python版本
PY_VERSION=$($PYTHON_CMD -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
echo "检测到Python版本: $PY_VERSION"

# 检查venv模块
if ! $PYTHON_CMD -c "import venv" &>/dev/null; then
    echo "错误：未找到venv模块。请安装venv后再试。"
    exit 1
fi

# 确定虚拟环境路径
VENV_PATH="venv"
if [ -d "$VENV_PATH" ]; then
    echo "发现已存在的虚拟环境。"
    read -p "是否重新创建虚拟环境？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "删除现有虚拟环境..."
        rm -rf "$VENV_PATH"
    else
        echo "将使用现有虚拟环境..."
    fi
fi

# 创建虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "创建新的虚拟环境..."
    $PYTHON_CMD -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "创建虚拟环境失败。"
        exit 1
    fi
fi

# 激活虚拟环境
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source "$VENV_PATH/Scripts/activate"
else
    # Unix/Linux/MacOS
    source "$VENV_PATH/bin/activate"
fi

# 检查激活是否成功
if [ $? -ne 0 ]; then
    echo "激活虚拟环境失败。"
    exit 1
fi

echo "已激活虚拟环境: $VIRTUAL_ENV"

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装项目依赖..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "安装依赖失败。"
    exit 1
fi

echo "===== 虚拟环境设置完成 ====="
echo "使用以下命令激活虚拟环境:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "    source venv/Scripts/activate"
else
    echo "    source venv/bin/activate"
fi
echo "使用以下命令运行应用:"
echo "    python main.py"
