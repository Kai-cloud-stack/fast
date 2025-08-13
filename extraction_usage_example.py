#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解压缩功能使用示例
Extraction Feature Usage Example

展示如何在项目中使用新集成的解压缩功能。
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.services.package_manager import PackageManager
from test_framework.utils.logging_system import get_logger


def example_1_basic_extraction():
    """
    示例1: 基本解压缩功能
    """
    logger = get_logger(__name__)
    logger.info("=== 示例1: 基本解压缩功能 ===")
    
    # 配置解压缩功能
    config = {
        "download_path": "./downloads",
        "extraction": {
            "enabled": True,
            "auto_extract": False,  # 手动控制解压
            "extract_path": "./extracted",
            "supported_formats": [".zip", ".tar", ".tar.gz", ".gz"],
            "overwrite_existing": True,
            "preserve_structure": True,
            "cleanup_archives": False  # 保留原始压缩文件
        }
    }
    
    # 创建包管理器实例
    package_manager = PackageManager(config)
    
    # 检查支持的压缩格式
    supported_formats = package_manager.get_supported_archive_formats()
    logger.info(f"支持的压缩格式: {', '.join(supported_formats)}")
    
    # 手动解压指定目录中的所有压缩文件
    if Path("./downloads").exists():
        extraction_summary = package_manager.extract_package_archives(
            "./downloads",
            "./extracted"
        )
        
        logger.info(f"解压完成:")
        logger.info(f"  - 处理的压缩文件: {extraction_summary.processed_archives}")
        logger.info(f"  - 解压的文件数: {extraction_summary.extracted_files}")
        logger.info(f"  - 失败的压缩文件: {extraction_summary.failed_archives}")
        logger.info(f"  - 处理时间: {extraction_summary.processing_time:.2f}秒")
    else:
        logger.info("下载目录不存在，跳过解压示例")


def example_2_auto_extraction():
    """
    示例2: 自动解压缩功能
    """
    logger = get_logger(__name__)
    logger.info("=== 示例2: 自动解压缩功能 ===")
    
    # 配置自动解压缩
    config = {
        "download_path": "./downloads",
        "extraction": {
            "enabled": True,
            "auto_extract": True,  # 启用自动解压
            "extract_path": "./auto_extracted",
            "supported_formats": [".zip", ".tar", ".tar.gz", ".gz"],
            "overwrite_existing": True,
            "preserve_structure": True,
            "cleanup_archives": True,  # 解压后删除原始压缩文件
            "max_extract_size": 100 * 1024 * 1024  # 100MB 限制
        },
        "windows_share": {
            "enabled": True,
            "sync_packages": [
                {
                    "name": "firmware",
                    "share_path": "//server/shared/firmware",
                    "local_path": "./downloads/firmware",
                    "extensions": [".zip", ".tar.gz"]
                }
            ]
        }
    }
    
    # 创建包管理器实例
    package_manager = PackageManager(config)
    
    logger.info("配置了自动解压缩功能:")
    logger.info(f"  - 自动解压: {'是' if package_manager.extraction_config.auto_extract else '否'}")
    logger.info(f"  - 解压路径: {package_manager.extraction_config.extract_path}")
    logger.info(f"  - 清理压缩文件: {'是' if package_manager.extraction_config.cleanup_archives else '否'}")
    logger.info(f"  - 最大解压大小: {package_manager.extraction_config.max_extract_size / (1024*1024):.0f}MB")
    
    # 注意: 在实际使用中，当从Windows共享下载文件时，
    # 如果启用了auto_extract，文件会自动解压
    logger.info("提示: 当从Windows共享下载文件时，压缩文件将自动解压")


def example_3_dynamic_config_update():
    """
    示例3: 动态配置更新
    """
    logger = get_logger(__name__)
    logger.info("=== 示例3: 动态配置更新 ===")
    
    # 初始配置
    config = {
        "extraction": {
            "enabled": True,
            "auto_extract": False,
            "cleanup_archives": False
        }
    }
    
    package_manager = PackageManager(config)
    
    logger.info("初始配置:")
    logger.info(f"  - 自动解压: {package_manager.extraction_config.auto_extract}")
    logger.info(f"  - 清理压缩文件: {package_manager.extraction_config.cleanup_archives}")
    
    # 动态更新配置
    config_updates = {
        "auto_extract": True,
        "cleanup_archives": True,
        "overwrite_existing": True,
        "max_extract_size": 200 * 1024 * 1024  # 200MB
    }
    
    package_manager.update_extraction_config(config_updates)
    
    logger.info("更新后配置:")
    logger.info(f"  - 自动解压: {package_manager.extraction_config.auto_extract}")
    logger.info(f"  - 清理压缩文件: {package_manager.extraction_config.cleanup_archives}")
    logger.info(f"  - 覆盖现有文件: {package_manager.extraction_config.overwrite_existing}")
    logger.info(f"  - 最大解压大小: {package_manager.extraction_config.max_extract_size / (1024*1024):.0f}MB")


def example_4_main_config_integration():
    """
    示例4: 主配置文件集成
    """
    logger = get_logger(__name__)
    logger.info("=== 示例4: 主配置文件集成 ===")
    
    # 读取主配置文件
    config_path = project_root / "test_framework" / "config" / "main_config.json"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            main_config = json.load(f)
        
        package_config = main_config.get("package_manager", {})
        
        if package_config:
            # 使用主配置文件创建包管理器
            package_manager = PackageManager(package_config)
            
            logger.info("从主配置文件加载的解压缩配置:")
            logger.info(f"  - 解压功能: {'已启用' if package_manager.extraction_config.enabled else '已禁用'}")
            logger.info(f"  - 自动解压: {'是' if package_manager.extraction_config.auto_extract else '否'}")
            logger.info(f"  - 解压路径: {package_manager.extraction_config.extract_path}")
            logger.info(f"  - 支持格式: {', '.join(package_manager.extraction_config.supported_formats)}")
            logger.info(f"  - 覆盖现有文件: {'是' if package_manager.extraction_config.overwrite_existing else '否'}")
            logger.info(f"  - 保持目录结构: {'是' if package_manager.extraction_config.preserve_structure else '否'}")
            logger.info(f"  - 清理压缩文件: {'是' if package_manager.extraction_config.cleanup_archives else '否'}")
            
            # 显示Windows共享配置
            windows_share_config = package_config.get("windows_share", {})
            if windows_share_config.get("enabled"):
                sync_packages = windows_share_config.get("sync_packages", [])
                logger.info(f"  - 配置的同步包数量: {len(sync_packages)}")
                for pkg in sync_packages:
                    logger.info(f"    * {pkg.get('name', 'Unknown')}: {pkg.get('share_path', 'N/A')}")
        else:
            logger.warning("主配置文件中没有package_manager配置")
    else:
        logger.warning("主配置文件不存在")


def main():
    """
    主函数 - 运行所有示例
    """
    logger = get_logger(__name__)
    logger.info("开始解压缩功能使用示例演示")
    
    print("\n" + "="*60)
    print("解压缩功能使用示例")
    print("="*60)
    
    try:
        example_1_basic_extraction()
        print()
        
        example_2_auto_extraction()
        print()
        
        example_3_dynamic_config_update()
        print()
        
        example_4_main_config_integration()
        
        print("\n" + "="*60)
        print("所有示例演示完成")
        print("="*60)
        
        print("\n使用提示:")
        print("1. 基本解压: 手动调用 extract_package_archives() 方法")
        print("2. 自动解压: 设置 auto_extract=True，下载时自动解压")
        print("3. 配置更新: 使用 update_extraction_config() 动态修改配置")
        print("4. 格式支持: 支持 .zip, .tar, .tar.gz, .tgz, .tar.bz2, .gz 等格式")
        print("5. 安全检查: 自动检查路径安全性，防止目录遍历攻击")
        print("6. 大小限制: 可设置 max_extract_size 限制解压文件大小")
        
    except Exception as e:
        logger.error(f"示例演示过程中发生错误: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)