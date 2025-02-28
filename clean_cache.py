import os
import shutil

def clean_pycache():
    """清理项目中的 Python 缓存文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 清理 __pycache__ 目录
    for root, dirs, files in os.walk(base_dir):
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            print(f"删除缓存目录：{cache_dir}")
            shutil.rmtree(cache_dir)
        
        # 删除 .pyc 文件
        for file in files:
            if file.endswith('.pyc'):
                pyc_file = os.path.join(root, file)
                print(f"删除缓存文件：{pyc_file}")
                os.remove(pyc_file)

if __name__ == "__main__":
    clean_pycache()
    print("缓存清理完成！")
