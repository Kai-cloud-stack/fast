#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TSE名称与测试用例匹配功能

这个脚本用于测试和演示TSE文件名与测试用例组的匹配逻辑
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from test_framework.utils.common_utils import (
    get_testcase_group_from_tse_name,
    get_enabled_test_cases,
    load_task_config
)

def test_tse_name_matching():
    """
    测试TSE名称匹配功能
    """
    print("=" * 60)
    print("TSE名称与测试用例匹配功能测试")
    print("=" * 60)
    
    # 测试用例：不同的TSE文件名
    test_cases = [
        "Test_Diag_Module1.tse",
        "Test_Can_Module2.tse", 
        "FrameCheck_Diag_Test.tse",
        "SWTDmessage_Can_normal.tse",
        "UnusedBit_Test.tse",
        "CRCCheck_Test.tse",
        "General_Test.tse",
        "MyTest.tse"
    ]
    
    print("\n1. TSE文件名匹配测试用例组：")
    print("-" * 40)
    
    for tse_name in test_cases:
        # 获取TSE文件名（不含扩展名）
        base_name = Path(tse_name).stem
        
        # 获取匹配的测试用例组
        testcase_group = get_testcase_group_from_tse_name(base_name)
        
        print(f"TSE文件: {tse_name:<25} → 测试用例组: {testcase_group}")
    
    # 测试加载任务配置并获取启用的测试用例
    task_config_path = "test_framework/config/task_config.json"
    
    if Path(task_config_path).exists():
        print(f"\n2. 从任务配置文件获取启用的测试用例：")
        print("-" * 40)
        
        try:
            task_config = load_task_config(task_config_path)
            
            for tse_name in test_cases[:4]:  # 只测试前4个
                base_name = Path(tse_name).stem
                enabled_cases = get_enabled_test_cases(task_config, base_name)
                
                print(f"\nTSE文件: {tse_name}")
                print(f"匹配的测试用例组: {get_testcase_group_from_tse_name(base_name)}")
                print(f"启用的测试用例数量: {len(enabled_cases)}")
                
                if enabled_cases:
                    print("启用的测试用例:")
                    for case in enabled_cases[:3]:  # 只显示前3个
                        print(f"  - {case}")
                    if len(enabled_cases) > 3:
                        print(f"  ... 还有 {len(enabled_cases) - 3} 个测试用例")
                else:
                    print("  没有启用的测试用例")
                    
        except Exception as e:
            print(f"加载任务配置时出错: {e}")
    else:
        print(f"\n任务配置文件不存在: {task_config_path}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_tse_name_matching()