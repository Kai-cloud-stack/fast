#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试执行工具模块
Test Execution Utility Functions Module

提供测试执行相关的工具函数，包括：
- 测试任务执行
- 环境检查
- 通知发送
- 测试结果汇总
"""

import logging
from typing import Dict, List, Set, Any

from ..checkers.environment_checker import EnvironmentChecker
from ..interfaces.canoe_interface import CANoeInterface
from ..services.notification_service import NotificationService
from .common_utils import (
    load_task_config,
    get_enabled_test_cases,
    check_environment_result,
    process_test_results,
    format_test_summary
)


def run_test_tasks(canoe_obj: CANoeInterface, task_config_path: str, tse_name: str = None) -> List[Any]:
    """
    执行测试任务
    
    Args:
        canoe_obj: CANoe接口对象
        task_config_path: 任务配置文件路径
        tse_name: TSE文件名称，用于匹配对应的测试用例组（可选）
    
    Returns:
        List: 测试结果列表
    
    Raises:
        Exception: 执行过程中的任何异常
    """
    try:
        # 加载任务配置
        task_config = load_task_config(task_config_path)
        
        # 获取启用的测试用例（根据TSE名称匹配对应的测试用例组）
        enabled_case_names = get_enabled_test_cases(task_config, tse_name)
        
        if not enabled_case_names:
            logging.warning("没有启用的测试用例，跳过执行")
            return []
        
        logging.info(f"开始执行 {len(enabled_case_names)} 个测试用例")
        
        # 执行测试
        canoe_obj.select_test_cases(enabled_case_names)
        canoe_obj.start_measurement()
        canoe_obj.run_test_modules()
        canoe_obj.stop_measurement()
        
        results = canoe_obj.test_results
        logging.info(f"测试执行完成，共 {len(results)} 个结果")
        
        return results
        
    except Exception as e:
        logging.error(f"执行测试任务时发生错误: {e}")
        raise


def perform_environment_check(canoe_obj: CANoeInterface, config: Dict[str, Any] = None) -> bool:
    """
    执行环境检查
    
    Args:
        canoe_obj: CANoe接口对象
        config: 配置字典
    
    Returns:
        bool: 环境是否准备就绪
    """
    try:
        logging.info("开始环境检查...")
        tester = EnvironmentChecker(canoe_obj, None, config)
        tester.check_environment()
        env_results = tester.get_check_results()
        
        is_ready = check_environment_result(env_results)
        
        if is_ready:
            logging.info("环境检查通过")
        else:
            logging.error("环境检查失败")
            
        return is_ready
        
    except Exception as e:
        logging.error(f"环境检查时发生错误: {e}")
        return False


def execute_multi_tse_workflow(config_file: str = None, task_config_path: str = None) -> bool:
    """
    执行多TSE文件测试工作流程的便捷函数
    
    Args:
        config_file: 配置文件路径，默认使用main_config.json
        task_config_path: 任务配置文件路径，用于根据TSE名称匹配测试用例
    
    Returns:
        bool: 执行是否成功
    """
    from ..executors.multi_tse_executor import MultiTSEExecutor
    from .common_utils import load_main_config
    
    try:
        # 加载配置
        if config_file:
            config = load_main_config(config_file)
        else:
            config = load_main_config()
        
        # 创建CANoe接口对象进行环境检查
        canoe_obj = CANoeInterface(config)
        
        # 执行环境检查
        logging.info("开始环境检查")
        env_check_passed = perform_environment_check(canoe_obj, config)
        
        if not env_check_passed:
            logging.error("环境检查失败，终止多TSE执行")
            canoe_obj.cleanup()
            return False
        
        logging.info("环境检查通过，开始执行多TSE文件测试")
        
        # 清理环境检查使用的CANoe对象
        canoe_obj.cleanup()
        
        # 创建多TSE执行器
        executor = MultiTSEExecutor(config_file)
        
        # 如果提供了task_config_path，将其添加到配置中
        if task_config_path:
            executor.config['task_config_path'] = task_config_path
            logging.info(f"设置任务配置文件路径: {task_config_path}")
        
        return executor.execute()
    except Exception as e:
        logging.error(f"多TSE执行工作流程失败: {e}")
        return False


def create_multi_tse_executor(config_file: str = None) -> 'MultiTSEExecutor':
    """
    创建多TSE执行器实例的便捷函数
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        MultiTSEExecutor: 多TSE执行器实例
    """
    from ..executors.multi_tse_executor import MultiTSEExecutor
    
    return MultiTSEExecutor(config_file)


def send_test_notification(config: Dict[str, Any], results_dict: Dict[str, Any], 
                          failed_cases: Set[str], execution_time: float = 0.0) -> bool:
    """
    发送测试结果通知
    
    Args:
        config: 主配置字典
        results_dict: 测试结果字典
        failed_cases: 失败用例集合
        execution_time: 执行时间
    
    Returns:
        bool: 通知是否发送成功
    """
    try:
        email_config = config.get('email')
        wechat_config = config.get('wechat')
        
        if not email_config:
            logging.warning("未配置邮件通知，跳过通知发送")
            return False
            
        # 生成测试摘要
        summary = format_test_summary(results_dict, failed_cases, execution_time)
        logging.info(f"测试摘要:\n{summary}")
        
        # 发送通知
        notification_config = {
            'email': email_config or {},
            'wechat': wechat_config or {}
        }
        notification_service = NotificationService(notification_config)
        notification_service.send_email(
            subject='测试执行结果通知',
            results=results_dict,
            failed_keywords=failed_cases
        )
        
        logging.info("测试结果通知发送成功")
        return True
        
    except Exception as e:
        logging.error(f"发送通知时发生错误: {e}")
        return False


def execute_complete_test_workflow(canoe_obj: CANoeInterface, task_config_path: str, 
                                 config: Dict[str, Any], skip_env_check: bool = False) -> Dict[str, Any]:
    """
    执行完整的测试工作流程
    
    Args:
        canoe_obj: CANoe接口对象
        task_config_path: 任务配置文件路径
        config: 主配置字典
        skip_env_check: 是否跳过环境检查
    
    Returns:
        Dict: 包含执行结果的字典
    """
    workflow_result = {
        'success': False,
        'env_check_passed': False,
        'test_results': [],
        'results_dict': {},
        'failed_cases': set(),
        'execution_time': 0.0,
        'notification_sent': False,
        'error_message': None
    }
    
    try:
        # 环境检查
        if not skip_env_check:
            workflow_result['env_check_passed'] = perform_environment_check(canoe_obj, config)
            if not workflow_result['env_check_passed']:
                workflow_result['error_message'] = "环境检查失败，终止执行"
                logging.error(workflow_result['error_message'])
                return workflow_result
        else:
            workflow_result['env_check_passed'] = True
            logging.info("跳过环境检查")
        
        # 执行测试任务
        import time
        start_time = time.time()
        test_results = run_test_tasks(canoe_obj, task_config_path)
        end_time = time.time()
        
        workflow_result['test_results'] = test_results
        workflow_result['execution_time'] = end_time - start_time
        
        # 处理测试结果
        if test_results:
            results_dict, failed_cases = process_test_results(test_results)
            workflow_result['results_dict'] = results_dict
            workflow_result['failed_cases'] = failed_cases
            
            # 发送通知
            workflow_result['notification_sent'] = send_test_notification(
                config, results_dict, failed_cases, workflow_result['execution_time']
            )
        
        workflow_result['success'] = True
        logging.info("测试工作流程执行完成")
        
    except Exception as e:
        workflow_result['error_message'] = str(e)
        logging.error(f"测试工作流程执行失败: {e}")
    
    return workflow_result


def validate_test_configuration(config: Dict[str, Any], task_config_path: str) -> bool:
    """
    验证测试配置的有效性
    
    Args:
        config: 主配置字典
        task_config_path: 任务配置文件路径
    
    Returns:
        bool: 配置是否有效
    """
    try:
        # 检查主配置必要字段
        required_main_fields = ['canoe_config', 'project_info']
        for field in required_main_fields:
            if field not in config:
                logging.error(f"主配置缺少必要字段: {field}")
                return False
        
        # 检查任务配置
        task_config = load_task_config(task_config_path)
        if 'test_cases' not in task_config:
            logging.error("任务配置缺少test_cases字段")
            return False
        
        # 检查是否有启用的测试用例
        enabled_cases = get_enabled_test_cases(task_config)
        if not enabled_cases:
            logging.warning("没有启用的测试用例")
            return False
        
        logging.info("测试配置验证通过")
        return True
        
    except Exception as e:
        logging.error(f"验证测试配置时发生错误: {e}")
        return False