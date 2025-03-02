"""
测试 Zotero 服务对 PDF 附件的处理功能
"""

import os
import unittest
import logging
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 导入要测试的模块
from services.zotero_service import ZoteroService, get_zotero_service

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class TestZoteroService(unittest.TestCase):
    """测试 ZoteroService 类"""
    
    def setUp(self):
        """测试前的初始化"""
        self.zotero_service = get_zotero_service()
        
        # 创建临时目录用于保存测试文件
        self.temp_dir = os.path.join(os.getcwd(), 'test_temp')
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.zotero_service.temp_dir = self.temp_dir
    
    def tearDown(self):
        """测试后的清理"""
        # 删除测试过程中创建的文件
        for file in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, file))
            except Exception as e:
                logger.warning(f"删除测试文件失败：{e}")
        
        # 删除测试临时目录
        try:
            os.rmdir(self.temp_dir)
        except Exception as e:
            logger.warning(f"删除临时目录失败：{e}")
    
    def test_get_pdf_attachment_real_api(self):
        """测试通过真实 API 获取 PDF 附件
        
        注意：这个测试需要有效的 Zotero API 凭据和一个存在 PDF 附件的条目
        """
        # 检查是否配置了环境变量
        if not os.getenv('ZOTERO_USER_ID') or not os.getenv('ZOTERO_API_KEY'):
            self.skipTest("缺少 Zotero API 凭据，跳过测试")
        
        # 获取最近添加的一篇有 PDF 附件的论文
        try:
            recent_items = self.zotero_service.get_recent_items(filter_type='count', value=5)
            logger.info(f"获取到 {len(recent_items)} 篇论文")
            
            # 找到一篇有附件的论文
            test_item = None
            for item in recent_items:
                attachments = self.zotero_service.zot.children(item['key'])
                if any(att['data'].get('contentType') == 'application/pdf' for att in attachments):
                    test_item = item
                    break
            
            if not test_item:
                self.skipTest("未找到带有 PDF 附件的论文，跳过测试")
                
            # 获取 PDF 附件
            item_key = test_item['key']
            pdf_path = self.zotero_service.get_pdf_attachment(item_key)
            
            # 验证结果
            self.assertIsNotNone(pdf_path, "应该成功获取 PDF 附件")
            self.assertTrue(os.path.exists(pdf_path), "PDF 文件应该存在于指定路径")
            self.assertTrue(pdf_path.endswith('.pdf'), "文件应该是 PDF 格式")
            
            # 检查文件大小
            file_size = os.path.getsize(pdf_path)
            self.assertGreater(file_size, 0, "PDF 文件不应为空")
            
            logger.info(f"成功获取 PDF 文件：{pdf_path}, 大小：{file_size} 字节")
            
        except Exception as e:
            logger.error(f"测试过程中出错：{e}")
            raise
    
    @patch('services.zotero_service.ZoteroService._download_via_api')
    def test_get_pdf_attachment_mocked(self, mock_download):
        """使用 mock 测试 PDF 附件获取逻辑"""
        # 模拟下载成功
        mock_download.return_value = True
        
        # 创建一个模拟的附件对象
        mock_attachment = {
            'key': 'ABC123',
            'data': {
                'contentType': 'application/pdf',
                'filename': 'test_paper.pdf'
            }
        }
        
        # 使用 patch 替换 zot.children 方法
        with patch.object(self.zotero_service.zot, 'children') as mock_children:
            mock_children.return_value = [mock_attachment]
            
            # 测试获取 PDF 附件
            pdf_path = self.zotero_service.get_pdf_attachment('TEST123')
            
            # 验证结果
            self.assertIsNotNone(pdf_path)
            expected_path = f"{self.temp_dir}/TEST123.pdf"
            self.assertEqual(pdf_path, expected_path)
            
            # 验证方法调用
            mock_children.assert_called_once_with('TEST123')
            mock_download.assert_called_once()
    
    def test_local_file_attachment(self):
        """测试从本地路径获取 PDF 附件"""
        # 创建一个测试 PDF 文件
        test_pdf_path = os.path.join(self.temp_dir, 'local_test.pdf')
        with open(test_pdf_path, 'wb') as f:
            f.write(b'Test PDF content')
        
        # 创建模拟附件对象，指向本地文件
        mock_attachment = {
            'data': {
                'path': f'file:///{test_pdf_path.replace(os.sep, "/")}',
                'contentType': 'application/pdf'
            }
        }
        
        # 目标输出文件路径
        output_path = os.path.join(self.temp_dir, 'output_test.pdf')
        
        # 测试复制功能
        result = self.zotero_service._copy_from_local_path(mock_attachment, output_path)
        
        # 验证结果
        self.assertTrue(result, "应该成功从本地路径复制文件")
        self.assertTrue(os.path.exists(output_path), "目标文件应该存在")
        
        # 验证文件内容
        with open(output_path, 'rb') as f:
            content = f.read()
            self.assertEqual(content, b'Test PDF content', "文件内容应该正确复制")
    
    def test_zotero_storage_path(self):
        """测试从 Zotero 存储路径获取 PDF 文件"""
        # 创建临时 Zotero 存储目录
        test_storage_path = os.path.join(self.temp_dir, 'zotero_storage')
        os.makedirs(test_storage_path, exist_ok=True)
        
        # 暂存原始路径
        original_path = self.zotero_service.zotero_storage_path
        self.zotero_service.zotero_storage_path = test_storage_path
        
        try:
            # 创建测试文件结构
            test_key = "TESTKEY123"
            test_filename = "test_document.pdf"
            test_dir = os.path.join(test_storage_path, test_key)
            os.makedirs(test_dir, exist_ok=True)
            
            # 创建 PDF 文件
            test_pdf_path = os.path.join(test_dir, test_filename)
            with open(test_pdf_path, 'wb') as f:
                f.write(b'Zotero storage test content')
                
            # 创建模拟附件对象
            mock_attachment = {
                'key': test_key,
                'data': {
                    'filename': test_filename,
                    'contentType': 'application/pdf'
                }
            }
            
            # 输出文件路径
            output_path = os.path.join(self.temp_dir, 'zotero_output.pdf')
            
            # 测试复制功能
            result = self.zotero_service._copy_from_local_path(mock_attachment, output_path)
            
            # 验证结果
            self.assertTrue(result, "应该成功从 Zotero 存储路径复制文件")
            self.assertTrue(os.path.exists(output_path), "目标文件应该存在")
            
            # 验证文件内容
            with open(output_path, 'rb') as f:
                content = f.read()
                self.assertEqual(content, b'Zotero storage test content', "文件内容应该正确复制")
                
        finally:
            # 恢复原始路径
            self.zotero_service.zotero_storage_path = original_path
            
            # 清理临时目录
            for root, dirs, files in os.walk(test_storage_path, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(test_storage_path)

if __name__ == '__main__':
    unittest.main()
