#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : test_logging_fix.py
@date     : 2024-12-19
@author   : <kai.ren@freetech.com>
@describe : 测试日志系统修复，验证所有模块的日志都能保存到文件
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 直接导入日志系统模块，避免导入依赖Windows的模块
sys.path.insert(0, str(project_root / 'test_framework' / 'utils'))
from logging_system import (
    setup_project_logging, 
    get_logger, 
    get_project_log_file,
    get_project_log_level
)

def test_logging_system():
    """
    测试日志系统功能
    """
    print("=" * 60)
    print("测试日志系统修复")
    print("=" * 60)
    
    # 1. 设置项目级别的日志
    print("\n1. 初始化项目日志系统...")
    project_logger = setup_project_logging(
        project_name='LoggingTest',
        log_dir='logs',
        log_level='INFO'
    )
    
    # 2. 获取项目日志信息
    log_file = get_project_log_file()
    log_level = get_project_log_level()
    print(f"项目日志文件: {log_file}")
    print(f"项目日志级别: {log_level}")
    
    # 3. 测试不同模块的日志记录器
    print("\n2. 测试不同模块的日志记录器...")
    
    # 模拟不同模块的日志记录器
    module_loggers = {
        'environment_checker': get_logger('test_framework.checkers.environment_checker'),
        'task_executor': get_logger('test_framework.executors.task_executor'),
        'canoe_interface': get_logger('test_framework.interfaces.canoe_interface'),
        'main_controller': get_logger('test_framework.core.main_controller'),
        'notification_service': get_logger('test_framework.services.notification_service')
    }
    
    # 4. 记录测试日志
    print("\n3. 记录测试日志...")
    for module_name, logger in module_loggers.items():
        logger.info(f"这是来自 {module_name} 模块的信息日志")
        logger.warning(f"这是来自 {module_name} 模块的警告日志")
        logger.error(f"这是来自 {module_name} 模块的错误日志")
        print(f"✓ {module_name} 模块日志已记录")
    
    # 5. 验证日志文件
    print("\n4. 验证日志文件...")
    if log_file and os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            line_count = len(content.splitlines())
            print(f"✓ 日志文件存在: {log_file}")
            print(f"✓ 日志文件行数: {line_count}")
            
            # 检查是否包含各模块的日志
            modules_found = []
            for module_name in module_loggers.keys():
                if module_name in content:
                    modules_found.append(module_name)
            
            print(f"✓ 找到以下模块的日志: {', '.join(modules_found)}")
            
            if len(modules_found) == len(module_loggers):
                print("✅ 所有模块的日志都已成功保存到文件！")
            else:
                print("❌ 部分模块的日志未保存到文件")
                
            # 显示日志文件的前几行内容
            print("\n📄 日志文件内容预览:")
            lines = content.splitlines()
            for i, line in enumerate(lines[:10], 1):
                print(f"{i:2d}: {line}")
            if len(lines) > 10:
                print(f"... 还有 {len(lines) - 10} 行")
                
    else:
        print("❌ 日志文件不存在或路径错误")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    return log_file

if __name__ == '__main__':
    try:
        log_file = test_logging_system()
        if log_file:
            print(f"\n📁 日志文件位置: {log_file}")
            print("💡 您可以打开此文件查看所有模块的日志记录")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()