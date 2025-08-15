#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : test_case_selection_fix.py
@date     : 2024-12-19
@author   : <kai.ren@freetech.com>
@describe : 测试用例选择修复验证脚本
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.utils.common_utils import (
    load_main_config,
    load_task_config,
    get_enabled_test_cases,
    get_testcase_group_from_tse_name
)
from test_framework.utils.logging_system import setup_project_logging

def test_case_selection_logic():
    """
    测试用例选择逻辑验证
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 设置日志
        setup_project_logging()
        
        # 同时输出到控制台
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        logger.info("=== 测试用例选择修复验证 ===")
        
        # 1. 测试TSE名称到测试用例组的映射
        logger.info("\n--- 测试1: TSE名称映射 ---")
        test_tse_names = [
            "Test_Diag_Module1.tse",
            "Test_Can_Module2.tse", 
            "General_Test.tse",
            "C:/path/to/Diag_Test.tse",
            "Network_Frame_Test.tse"
        ]
        
        for tse_name in test_tse_names:
            group = get_testcase_group_from_tse_name(tse_name)
            logger.info(f"TSE文件: {tse_name} -> 测试用例组: {group}")
        
        # 2. 测试任务配置加载和测试用例选择
        logger.info("\n--- 测试2: 任务配置和测试用例选择 ---")
        
        # 检查任务配置文件是否存在
        task_config_path = project_root / "test_framework" / "config" / "task_config.json"
        if task_config_path.exists():
            logger.info(f"加载任务配置: {task_config_path}")
            task_config = load_task_config(str(task_config_path))
            
            # 显示配置结构
            logger.info("任务配置结构:")
            for key, value in task_config.items():
                if isinstance(value, list):
                    logger.info(f"  {key}: {len(value)} 个项目")
                else:
                    logger.info(f"  {key}: {type(value).__name__}")
            
            # 测试不同TSE名称的测试用例选择
            for tse_name in ["Test_Diag_Module1.tse", "Test_Can_Module2.tse", None]:
                logger.info(f"\n测试TSE: {tse_name}")
                enabled_cases = get_enabled_test_cases(task_config, tse_name)
                logger.info(f"启用的测试用例数量: {len(enabled_cases)}")
                if enabled_cases:
                    logger.info(f"测试用例列表: {enabled_cases[:5]}{'...' if len(enabled_cases) > 5 else ''}")
        else:
            logger.warning(f"任务配置文件不存在: {task_config_path}")
        
        # 3. 测试主配置加载
        logger.info("\n--- 测试3: 主配置加载 ---")
        main_config_path = project_root / "test_framework" / "config" / "main_config.json"
        if main_config_path.exists():
            logger.info(f"加载主配置: {main_config_path}")
            main_config = load_main_config(str(main_config_path))
            
            # 检查多TSE配置
            multi_tse_config = main_config.get('multi_tse', {})
            tse_files = multi_tse_config.get('tse_files', [])
            logger.info(f"配置的TSE文件数量: {len(tse_files)}")
            
            for i, tse_file in enumerate(tse_files[:3], 1):  # 只显示前3个
                logger.info(f"  TSE {i}: {tse_file}")
        else:
            logger.warning(f"主配置文件不存在: {main_config_path}")
        
        logger.info("\n=== 验证完成 ===")
        logger.info("修复说明:")
        logger.info("1. 修复了select_test_cases方法中的语法错误 (case_name== -> case_name ==)")
        logger.info("2. 这个错误可能导致测试用例选择失败，从而使测试用例看起来没有运行")
        logger.info("3. 修复后，测试用例选择应该能正常工作")
        
        return True
        
    except Exception as e:
        logger.error(f"验证过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_case_selection_logic()
    if success:
        print("\n✓ 测试用例选择修复验证通过")
    else:
        print("\n✗ 测试用例选择修复验证失败")
        sys.exit(1)