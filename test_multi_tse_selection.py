#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : test_multi_tse_selection.py
@date     : 2024-12-19
@author   : <kai.ren@freetech.com>
@describe : 测试多TSE执行中的测试用例选择功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.utils.common_utils import load_main_config, load_task_config, get_enabled_test_cases
from test_framework.utils.logging_system import get_logger

def test_multi_tse_selection():
    """
    测试多TSE执行中的测试用例选择功能
    """
    logger = get_logger(__name__)
    logger.info("=== 测试多TSE执行中的测试用例选择功能 ===")
    
    try:
        # 1. 加载配置文件
        main_config_path = "test_framework/config/main_config.json"
        task_config_path = "test_framework/config/task_config.json"
        
        logger.info(f"\n1. 加载配置文件")
        logger.info(f"主配置文件: {main_config_path}")
        logger.info(f"任务配置文件: {task_config_path}")
        
        main_config = load_main_config(main_config_path)
        task_config = load_task_config(task_config_path)
        
        # 2. 获取TSE文件路径
        tse_paths = main_config.get('canoe', {}).get('tse_paths', [])
        logger.info(f"\n2. TSE文件路径配置:")
        for i, tse_path in enumerate(tse_paths, 1):
            logger.info(f"  {i}. {tse_path}")
        
        # 3. 模拟多TSE执行流程中的测试用例选择
        logger.info(f"\n3. 模拟多TSE执行流程:")
        
        for i, tse_path in enumerate(tse_paths, 1):
            logger.info(f"\n--- 处理第 {i}/{len(tse_paths)} 个TSE文件 ---")
            
            # 获取TSE文件名（不含路径和扩展名）
            tse_name = os.path.splitext(os.path.basename(tse_path))[0]
            logger.info(f"TSE文件名: {tse_name}")
            
            # 根据TSE名称获取对应的测试用例
            enabled_case_names = get_enabled_test_cases(task_config, tse_name)
            
            if enabled_case_names:
                logger.info(f"为TSE文件 {tse_name} 找到 {len(enabled_case_names)} 个启用的测试用例:")
                for j, case_name in enumerate(enabled_case_names, 1):
                    logger.info(f"  {j}. {case_name}")
                
                # 这里应该调用 canoe_interface.select_test_cases(enabled_case_names)
                # 但由于我们只是测试逻辑，所以只记录日志
                logger.info(f">>> 应该调用 select_test_cases({enabled_case_names})")
                
            else:
                logger.warning(f"TSE文件 {tse_name} 没有找到匹配的测试用例")
        
        logger.info(f"\n=== 测试完成 ===")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        raise

def main():
    """
    主函数
    """
    test_multi_tse_selection()

if __name__ == "__main__":
    main()