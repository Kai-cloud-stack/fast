#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解压缩功能集成测试脚本
Extraction Integration Test Script

测试包管理器中解压缩功能的集成和配置读取。
"""

import os
import sys
import json
import tempfile
import zipfile
import tarfile
import gzip
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.services.package_manager import PackageManager
from test_framework.utils.logging_system import get_logger


def create_test_archives(test_dir: Path):
    """
    创建测试用的压缩文件
    
    Args:
        test_dir: 测试目录
    """
    logger = get_logger(__name__)
    
    # 创建测试文件
    test_file1 = test_dir / "test1.txt"
    test_file2 = test_dir / "test2.txt"
    test_file1.write_text("这是测试文件1的内容")
    test_file2.write_text("这是测试文件2的内容")
    
    # 创建ZIP文件
    zip_path = test_dir / "test.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(test_file1, "test1.txt")
        zf.write(test_file2, "test2.txt")
    
    # 创建TAR文件
    tar_path = test_dir / "test.tar"
    with tarfile.open(tar_path, 'w') as tf:
        tf.add(test_file1, "test1.txt")
        tf.add(test_file2, "test2.txt")
    
    # 创建TAR.GZ文件
    tar_gz_path = test_dir / "test.tar.gz"
    with tarfile.open(tar_gz_path, 'w:gz') as tf:
        tf.add(test_file1, "test1.txt")
        tf.add(test_file2, "test2.txt")
    
    # 创建GZ文件
    gz_path = test_dir / "test.txt.gz"
    with open(test_file1, 'rb') as f_in:
        with gzip.open(gz_path, 'wb') as f_out:
            f_out.write(f_in.read())
    
    # 删除原始测试文件
    test_file1.unlink()
    test_file2.unlink()
    
    logger.info(f"创建了测试压缩文件: {[f.name for f in test_dir.glob('*') if f.is_file()]}")
    return [zip_path, tar_path, tar_gz_path, gz_path]


def test_extraction_config_loading():
    """
    测试解压缩配置的加载
    """
    logger = get_logger(__name__)
    logger.info("开始测试解压缩配置加载")
    
    # 创建测试配置
    test_config = {
        "download_path": "./test_downloads",
        "extraction": {
            "enabled": True,
            "auto_extract": True,
            "extract_path": "extracted",
            "supported_formats": [".zip", ".tar", ".tar.gz", ".gz"],
            "overwrite_existing": True,
            "preserve_structure": True,
            "cleanup_archives": False,
            "max_extract_size": 500 * 1024 * 1024,  # 500MB
            "password_protected": False
        }
    }
    
    try:
        # 创建包管理器实例
        package_manager = PackageManager(test_config)
        
        # 验证配置加载
        assert package_manager.extraction_config.enabled == True
        assert package_manager.extraction_config.auto_extract == True
        assert package_manager.extraction_config.extract_path == "extracted"
        assert package_manager.extraction_config.overwrite_existing == True
        assert package_manager.extraction_config.max_extract_size == 500 * 1024 * 1024
        
        # 验证支持的格式
        supported_formats = package_manager.get_supported_archive_formats()
        assert ".zip" in supported_formats
        assert ".tar" in supported_formats
        assert ".tar.gz" in supported_formats
        
        logger.info("✓ 解压缩配置加载测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 解压缩配置加载测试失败: {str(e)}")
        return False


def test_manual_extraction():
    """
    测试手动解压功能
    """
    logger = get_logger(__name__)
    logger.info("开始测试手动解压功能")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # 创建测试压缩文件
            archive_files = create_test_archives(temp_path)
            
            # 创建包管理器实例
            test_config = {
                "extraction": {
                    "enabled": True,
                    "auto_extract": False,
                    "extract_path": "manual_extracted",
                    "supported_formats": [".zip", ".tar", ".tar.gz", ".gz"],
                    "overwrite_existing": True,
                    "preserve_structure": True
                }
            }
            package_manager = PackageManager(test_config)
            
            # 执行手动解压
            extraction_summary = package_manager.extract_package_archives(
                str(temp_path), 
                str(temp_path / "extracted")
            )
            
            # 验证解压结果
            assert extraction_summary.processed_archives > 0
            assert extraction_summary.failed_archives == 0
            
            # 检查解压的文件是否存在
            extracted_dir = temp_path / "extracted"
            assert extracted_dir.exists()
            
            # 检查是否有解压出的文件
            extracted_files = list(extracted_dir.rglob("*.txt"))
            assert len(extracted_files) > 0
            
            logger.info(f"✓ 手动解压测试通过: 处理了 {extraction_summary.processed_archives} 个压缩文件")
            logger.info(f"  解压出 {extraction_summary.extracted_files} 个文件")
            logger.info(f"  处理时间: {extraction_summary.processing_time:.2f}秒")
            return True
            
        except Exception as e:
            logger.error(f"✗ 手动解压测试失败: {str(e)}")
            return False


def test_config_update():
    """
    测试配置更新功能
    """
    logger = get_logger(__name__)
    logger.info("开始测试配置更新功能")
    
    try:
        # 创建包管理器实例
        test_config = {
            "extraction": {
                "enabled": True,
                "auto_extract": False,
                "cleanup_archives": False
            }
        }
        package_manager = PackageManager(test_config)
        
        # 验证初始配置
        assert package_manager.extraction_config.auto_extract == False
        assert package_manager.extraction_config.cleanup_archives == False
        
        # 更新配置
        config_updates = {
            "auto_extract": True,
            "cleanup_archives": True,
            "overwrite_existing": True
        }
        package_manager.update_extraction_config(config_updates)
        
        # 验证配置更新
        assert package_manager.extraction_config.auto_extract == True
        assert package_manager.extraction_config.cleanup_archives == True
        assert package_manager.extraction_config.overwrite_existing == True
        
        logger.info("✓ 配置更新测试通过")
        return True
        
    except Exception as e:
        logger.error(f"✗ 配置更新测试失败: {str(e)}")
        return False


def test_main_config_integration():
    """
    测试与主配置文件的集成
    """
    logger = get_logger(__name__)
    logger.info("开始测试主配置文件集成")
    
    try:
        # 读取主配置文件
        config_path = project_root / "test_framework" / "config" / "main_config.json"
        
        if not config_path.exists():
            logger.warning("主配置文件不存在，跳过集成测试")
            return True
        
        with open(config_path, 'r', encoding='utf-8') as f:
            main_config = json.load(f)
        
        package_config = main_config.get("package_manager", {})
        if not package_config:
            logger.warning("主配置文件中没有package_manager配置，跳过集成测试")
            return True
        
        # 创建包管理器实例
        package_manager = PackageManager(package_config)
        
        # 验证解压缩配置是否正确加载
        extraction_config = package_config.get("extraction", {})
        if extraction_config:
            assert package_manager.extraction_config.enabled == extraction_config.get("enabled", True)
            assert package_manager.extraction_config.auto_extract == extraction_config.get("auto_extract", True)
            
            logger.info("✓ 主配置文件集成测试通过")
            logger.info(f"  解压功能: {'已启用' if package_manager.extraction_config.enabled else '已禁用'}")
            logger.info(f"  自动解压: {'是' if package_manager.extraction_config.auto_extract else '否'}")
            logger.info(f"  支持格式: {', '.join(package_manager.extraction_config.supported_formats)}")
        else:
            logger.info("✓ 主配置文件集成测试通过（使用默认配置）")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 主配置文件集成测试失败: {str(e)}")
        return False


def main():
    """
    主测试函数
    """
    logger = get_logger(__name__)
    logger.info("开始解压缩功能集成测试")
    
    test_results = {
        "配置加载测试": test_extraction_config_loading(),
        "手动解压测试": test_manual_extraction(),
        "配置更新测试": test_config_update(),
        "主配置集成测试": test_main_config_integration()
    }
    
    # 输出测试结果
    print("\n" + "="*60)
    print("解压缩功能集成测试结果")
    print("="*60)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name.ljust(20)}: {status}")
        if not result:
            all_passed = False
    
    print("="*60)
    overall_status = "所有测试通过" if all_passed else "部分测试失败"
    print(f"总体结果: {overall_status}")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)