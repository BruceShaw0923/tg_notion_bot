#!/bin/bash
# 安装所有必需的依赖项

echo "===== 安装项目依赖 ====="

# 确保 pip 是最新的
pip install --upgrade pip

# 安装核心依赖
pip install -r docker-requirements.txt

# 确保 pyzotero 已安装 (若上一步失败)
# 使用引号避免特殊字符被 shell 解析
pip install "pyzotero>=1.5.5"

echo "===== 检查 pyzotero 安装 ====="
# 使用 try/catch 结构避免执行错误
python -c "
import sys
try:
    import pyzotero
    print(f'pyzotero 版本: {pyzotero.__version__}')
    print('安装成功!')
except ImportError:
    print('pyzotero 未安装成功，请手动安装')
    sys.exit(1)
"

echo "===== 依赖安装完成 ====="
