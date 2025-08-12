#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软件包管理器测试脚本
Package Manager Test Script

用于测试 Windows 共享和 SVN 两种软件包下载方式。
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


def load_config():
    """
    加载配置文件
    
    Returns:
        dict: 配置信息
    """
    config_path = project_root / "test_framework" / "config" / "main_config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"配置文件未找到: {config_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")
        return None


def main():
    """
    主测试函数
    """
    logger = get_logger(__name__)
    logger.info("开始软件包管理器测试")
    
    # 加载配置
    config = load_config()
    if not config:
        logger.error("无法加载配置文件，测试终止")
        return False
    
    package_config = config.get("package_manager", {})
    if not package_config:
        logger.error("未找到 package_manager 配置，测试终止")
        return False
    
    logger.info("配置加载成功")
    logger.info(f"默认下载方式: {package_config.get('default_method', 'unknown')}")
    
    # 创建软件包管理器实例
    try:
        package_manager = PackageManager(package_config)
        logger.info("软件包管理器初始化成功")
    except Exception as e:
        logger.error(f"软件包管理器初始化失败: {str(e)}")
        return False
    
    # 运行测试
    logger.info("开始执行下载测试...")
    test_results = package_manager.run_download_tests()
    
    # 输出详细结果
    print("\n" + "="*50)
    print("软件包管理器测试结果")
    print("="*50)
    
    all_passed = True
    for method, success in test_results.items():
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{method.ljust(20)}: {status}")
        if not success:
            all_passed = False
    
    print("="*50)
    overall_status = "所有测试通过" if all_passed else "部分测试失败"
    print(f"总体结果: {overall_status}")
    print("="*50)
    
    # 输出配置信息
    print("\n当前配置信息:")
    print(f"  默认方式: {package_config.get('default_method')}")
    print(f"  下载路径: {package_config.get('download_path')}")
    print(f"  超时设置: {package_config.get('timeout')}秒")
    
    # Windows 共享配置
    ws_config = package_config.get("windows_share", {})
    if ws_config.get("enabled"):
        print(f"  Windows 共享: 已启用")
        sync_packages = ws_config.get("sync_packages", [])
        print(f"    配置包数量: {len(sync_packages)}")
        for pkg in sync_packages:
            print(f"    - {pkg.get('name')}: {pkg.get('share_path')}")
    else:
        print(f"  Windows 共享: 已禁用")
    
    # SVN 配置
    svn_config = package_config.get("svn", {})
    if svn_config.get("enabled"):
        print(f"  SVN: 已启用")
        print(f"    仓库地址: {svn_config.get('repository_url')}")
        test_packages = svn_config.get("test_packages", [])
        print(f"    测试包数量: {len(test_packages)}")
        for pkg in test_packages:
            print(f"    - {pkg.get('name')}: {pkg.get('svn_url')}")
    else:
        print(f"  SVN: 已禁用")
    
    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中发生未预期错误: {str(e)}")
        sys.exit(1)