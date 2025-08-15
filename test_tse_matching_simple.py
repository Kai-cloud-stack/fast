#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版TSE名称与测试用例匹配功能测试

这个脚本只测试TSE文件名与测试用例组的匹配逻辑，不依赖CANoe相关模块
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def get_testcase_group_from_tse_name(tse_name: str) -> str:
    """
    根据TSE文件名推断测试用例组名称
    
    Args:
        tse_name: TSE文件名（不含扩展名）
        
    Returns:
        str: 对应的测试用例组名称
    """
    tse_name_lower = tse_name.lower()
    
    if 'diag' in tse_name_lower:
        return 'testcases_Diag'
    elif 'can' in tse_name_lower:
        return 'testcases_Can'
    else:
        return 'test_cases'

def load_task_config(config_path: str) -> dict:
    """
    加载任务配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 配置内容
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return {}

def get_enabled_test_cases(task_config: dict, tse_name: str = None) -> list:
    """
    获取启用的测试用例列表
    
    Args:
        task_config: 任务配置字典
        tse_name: TSE文件名（可选），用于匹配特定的测试用例组
        
    Returns:
        list: 启用的测试用例名称列表
    """
    enabled_cases = []
    
    if tse_name:
        # 根据TSE名称获取对应的测试用例组
        testcase_group = get_testcase_group_from_tse_name(tse_name)
        
        if testcase_group in task_config:
            test_cases = task_config[testcase_group]
            enabled_cases = [case['name'] for case in test_cases if case.get('enabled', False)]
    else:
        # 如果没有指定TSE名称，遍历所有测试用例组
        for key, test_cases in task_config.items():
            if key.startswith('testcases_') or key == 'test_cases':
                if isinstance(test_cases, list):
                    enabled_cases.extend([case['name'] for case in test_cases if case.get('enabled', False)])
    
    return enabled_cases

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
        
        # 根据匹配结果显示不同的描述
        if testcase_group == 'testcases_Diag':
            description = "诊断相关测试用例组"
        elif testcase_group == 'testcases_Can':
            description = "CAN通信相关测试用例组"
        else:
            description = "默认通用测试用例组"
        
        print(f"TSE文件: {tse_name:<25} → 测试用例组: {testcase_group} ({description})")
    
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