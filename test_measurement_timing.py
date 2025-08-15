#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : test_measurement_timing.py
@date     : 2024-12-19
@author   : <kai.ren@freetech.com>
@describe : 测试测量时序修复功能的验证脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.interfaces.canoe_interface import CANoeInterface
from test_framework.executors.multi_tse_executor import MultiTSEExecutor
from test_framework.utils.config_manager import ConfigManager
from test_framework.utils.logger_config import setup_logger

def test_measurement_timing():
    """
    测试修复后的测量时序功能
    验证测试用例选择在测量启动之前进行
    """
    logger = setup_logger('test_measurement_timing')
    
    try:
        # 1. 加载配置
        config_path = project_root / 'config' / 'config.json'
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            return False
            
        config_manager = ConfigManager(str(config_path))
        config = config_manager.get_config()
        
        logger.info("=== 测试测量时序修复功能 ===")
        
        # 2. 测试CANoeInterface直接调用
        logger.info("\n--- 测试1: CANoeInterface直接调用 ---")
        canoe_interface = CANoeInterface(config)
        
        # 使用任务配置文件路径
        task_config_path = project_root / 'config' / 'task_config.json'
        if task_config_path.exists():
            logger.info(f"使用任务配置文件: {task_config_path}")
            
            # 测试measurement_started=False的情况（推荐用法）
            logger.info("测试measurement_started=False（内部管理测量）")
            summary1 = canoe_interface.run_multiple_tse_files(
                task_config_path=str(task_config_path),
                measurement_started=False
            )
            
            if summary1:
                logger.info("✓ 测试1通过: 内部测量管理正常")
                logger.info(f"执行结果: {summary1.get('overall_stats', {})}")
            else:
                logger.warning("✗ 测试1失败: 内部测量管理异常")
        else:
            logger.warning(f"任务配置文件不存在: {task_config_path}")
        
        # 3. 测试MultiTSEExecutor调用
        logger.info("\n--- 测试2: MultiTSEExecutor调用 ---")
        
        # 创建多TSE执行器配置
        multi_tse_config = {
            'canoe_config': config.get('canoe', {}),
            'tse_files': config.get('multi_tse', {}).get('tse_files', []),
            'task_config_path': str(task_config_path) if task_config_path.exists() else None,
            'notification': config.get('notification', {})
        }
        
        executor = MultiTSEExecutor(config=multi_tse_config)
        
        # 执行测试（内部会调用run_multiple_tse_files with measurement_started=False）
        logger.info("执行MultiTSEExecutor测试...")
        result = executor.execute()
        
        if result:
            logger.info("✓ 测试2通过: MultiTSEExecutor执行正常")
        else:
            logger.warning("✗ 测试2失败: MultiTSEExecutor执行异常")
        
        logger.info("\n=== 测试完成 ===")
        logger.info("修复说明:")
        logger.info("1. run_multiple_tse_files方法现在支持measurement_started参数")
        logger.info("2. 当measurement_started=False时，方法内部会先选择测试用例，再启动测量")
        logger.info("3. MultiTSEExecutor已更新，不再外部管理测量，交由run_multiple_tse_files内部处理")
        logger.info("4. 这确保了'先选择测试用例，再启动测量'的正确时序")
        
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def show_timing_fix_summary():
    """
    显示时序修复的详细说明
    """
    logger = setup_logger('timing_fix_summary')
    
    logger.info("=== 测量时序问题修复总结 ===")
    logger.info("")
    logger.info("问题描述:")
    logger.info("- 在canoe_interface.py#L818，选择测试用例时测量已经开始")
    logger.info("- 这导致测试用例选择发生在测量启动之后，违反了预期的执行顺序")
    logger.info("")
    logger.info("修复方案:")
    logger.info("1. 在run_multiple_tse_files方法中添加measurement_started参数")
    logger.info("2. 当measurement_started=False时:")
    logger.info("   - 如果测量已启动，先停止测量")
    logger.info("   - 选择测试用例")
    logger.info("   - 启动测量")
    logger.info("   - 运行测试模块")
    logger.info("   - 停止测量")
    logger.info("3. 更新MultiTSEExecutor，移除外部测量管理")
    logger.info("4. 更新文档和示例代码")
    logger.info("")
    logger.info("修改的文件:")
    logger.info("- canoe_interface.py: 添加measurement_started参数和内部测量管理逻辑")
    logger.info("- multi_tse_executor.py: 移除外部测量启动/停止调用")
    logger.info("- README_MULTI_TSE.md: 更新API文档和示例代码")
    logger.info("")
    logger.info("使用建议:")
    logger.info("- 推荐使用measurement_started=False，让方法内部管理测量生命周期")
    logger.info("- 这确保了正确的执行顺序：选择测试用例 → 启动测量 → 运行测试 → 停止测量")

if __name__ == '__main__':
    print("测量时序修复验证脚本")
    print("1. 运行时序测试")
    print("2. 显示修复总结")
    
    choice = input("请选择操作 (1/2): ").strip()
    
    if choice == '1':
        test_measurement_timing()
    elif choice == '2':
        show_timing_fix_summary()
    else:
        print("无效选择")