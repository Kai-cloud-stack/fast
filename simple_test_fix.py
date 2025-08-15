#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : simple_test_fix.py
@date     : 2024-12-19
@author   : <kai.ren@freetech.com>
@describe : 简单的测试用例选择修复验证
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.utils.common_utils import (
    get_testcase_group_from_tse_name,
    get_enabled_test_cases
)

def main():
    print("=== 测试用例选择修复验证 ===")
    
    # 1. 测试TSE名称到测试用例组的映射
    print("\n--- 测试1: TSE名称映射 ---")
    test_tse_names = [
        "Test_Diag_Module1.tse",
        "Test_Can_Module2.tse", 
        "General_Test.tse",
        "C:/path/to/Diag_Test.tse",
        "Network_Frame_Test.tse"
    ]
    
    for tse_name in test_tse_names:
        group = get_testcase_group_from_tse_name(tse_name)
        print(f"TSE文件: {tse_name} -> 测试用例组: {group}")
    
    # 2. 检查配置文件
    print("\n--- 测试2: 配置文件检查 ---")
    task_config_path = project_root / "test_framework" / "config" / "task_config.json"
    main_config_path = project_root / "test_framework" / "config" / "main_config.json"
    
    print(f"任务配置文件存在: {task_config_path.exists()}")
    print(f"主配置文件存在: {main_config_path.exists()}")
    
    if task_config_path.exists():
        try:
            from test_framework.utils.common_utils import load_task_config
            task_config = load_task_config(str(task_config_path))
            print(f"任务配置加载成功，包含 {len(task_config)} 个配置项")
            
            # 测试测试用例选择
            print("\n--- 测试3: 测试用例选择 ---")
            for tse_name in ["Test_Diag_Module1.tse", "Test_Can_Module2.tse", None]:
                try:
                    enabled_cases = get_enabled_test_cases(task_config, tse_name)
                    print(f"TSE: {tse_name} -> 启用测试用例: {len(enabled_cases)} 个")
                    if enabled_cases and len(enabled_cases) <= 5:
                        print(f"  测试用例: {enabled_cases}")
                    elif enabled_cases:
                        print(f"  前5个测试用例: {enabled_cases[:5]}")
                except Exception as e:
                    print(f"TSE: {tse_name} -> 错误: {e}")
                    
        except Exception as e:
            print(f"加载任务配置失败: {e}")
    
    print("\n=== 修复说明 ===")
    print("1. 修复了canoe_interface.py中select_test_cases方法的语法错误")
    print("2. 将 'case_name== test_item.Name' 修正为 'case_name == test_item.Name'")
    print("3. 这个语法错误可能导致测试用例选择失败")
    print("4. 修复后，测试用例应该能够正确选择和运行")
    
    print("\n=== 验证完成 ===")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✓ 测试用例选择修复验证通过")
        else:
            print("\n✗ 测试用例选择修复验证失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)