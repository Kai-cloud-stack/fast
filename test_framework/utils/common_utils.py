#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数模块
Common Utility Functions Module

提供测试框架中常用的通用函数，包括：
- 配置文件加载
- 测试结果处理
- 文件路径处理
- 时间计算等
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any, Optional
from pprint import pprint

# 常量定义
DEFAULT_ENCODING = 'utf-8'
PASS_RESULT = 'PASS'
FAIL_RESULT = 'FAIL'
SKIP_RESULT = 'SKIP'
ENVIRONMENT_CHECK_CASE = 'Check_Environment'


def load_json_config(config_path: str, config_type: str = "配置") -> Dict[str, Any]:
    """
    加载JSON配置文件的通用函数
    
    Args:
        config_path: 配置文件路径
        config_type: 配置类型描述，用于错误日志
    
    Returns:
        Dict: 配置文件内容
    
    Raises:
        FileNotFoundError: 配置文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    try:
        with open(config_path, encoding=DEFAULT_ENCODING) as f:
            config = json.load(f)
        logging.info(f"成功加载{config_type}文件: {config_path}")
        return config
    except FileNotFoundError:
        error_msg = f"{config_type}文件未找到: {config_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"{config_type}文件JSON格式错误: {e}"
        logging.error(error_msg)
        raise json.JSONDecodeError(error_msg, e.doc, e.pos)


def load_task_config(task_config_path: str) -> Dict[str, Any]:
    """
    加载任务配置文件
    
    Args:
        task_config_path: 任务配置文件路径
    
    Returns:
        Dict: 任务配置内容
    """
    return load_json_config(task_config_path, "任务配置")


def load_main_config(config_path: str) -> Dict[str, Any]:
    """
    加载主配置文件
    
    Args:
        config_path: 主配置文件路径
    
    Returns:
        Dict: 主配置内容
    """
    return load_json_config(config_path, "主配置")


def get_testcase_group_from_tse_name(tse_name: str) -> str:
    """
    根据TSE文件名称推断对应的测试用例组名称
    
    Args:
        tse_name: TSE文件名称（可以是完整路径或文件名）
    
    Returns:
        str: 对应的测试用例组名称，如 'testcases_Diag', 'testcases_Can' 等
    """
    # 提取文件名（去掉路径和扩展名）
    import os
    filename = os.path.splitext(os.path.basename(tse_name))[0]
    
    # 根据文件名中的关键词匹配测试用例组
    filename_lower = filename.lower()
    
    if 'diag' in filename_lower:
        return 'testcases_Diag'
    elif 'can' in filename_lower:
        return 'testcases_Can'
    elif 'frame' in filename_lower:
        return 'testcases_Can'  # Frame相关测试通常属于CAN测试
    elif 'network' in filename_lower or 'net' in filename_lower:
        return 'testcases_Can'
    else:
        # 默认返回第一个找到的测试用例组
        logging.warning(f"无法从TSE文件名 '{tse_name}' 推断测试用例组，将使用默认组")
        return 'testcases_Diag'  # 默认使用Diag组


def get_enabled_test_cases(task_config: Dict[str, Any], tse_name: str = None) -> List[str]:
    """
    从任务配置中获取启用的测试用例名称列表
    
    Args:
        task_config: 任务配置字典
        tse_name: TSE文件名称，用于匹配对应的测试用例组（可选）
    
    Returns:
        List[str]: 启用的测试用例名称列表
    """
    enabled_case_names = []
    
    if tse_name:
        # 根据TSE名称匹配对应的测试用例组
        testcase_group = get_testcase_group_from_tse_name(tse_name)
        test_cases = task_config.get(testcase_group, [])
        
        if test_cases:
            enabled_tasks = [task for task in test_cases if task.get('enabled', False)]
            enabled_case_names = [task.get('name', '') for task in enabled_tasks if task.get('name')]
            logging.info(f"从 {testcase_group} 组中找到 {len(enabled_case_names)} 个启用的测试用例")
        else:
            logging.warning(f"在任务配置中未找到测试用例组: {testcase_group}")
    else:
        # 兼容原有逻辑：查找 'test_cases' 字段
        test_cases = task_config.get('test_cases', [])
        if test_cases:
            enabled_tasks = [task for task in test_cases if task.get('enabled', False)]
            enabled_case_names = [task.get('name', '') for task in enabled_tasks if task.get('name')]
        else:
            # 如果没有 'test_cases' 字段，则遍历所有可能的测试用例组
            for key, value in task_config.items():
                if key.startswith('testcases_') and isinstance(value, list):
                    enabled_tasks = [task for task in value if task.get('enabled', False)]
                    group_enabled_names = [task.get('name', '') for task in enabled_tasks if task.get('name')]
                    enabled_case_names.extend(group_enabled_names)
                    if group_enabled_names:
                        logging.info(f"从 {key} 组中找到 {len(group_enabled_names)} 个启用的测试用例")
    
    if not enabled_case_names:
        logging.warning("没有启用的测试用例")
    else:
        logging.info(f"总共找到 {len(enabled_case_names)} 个启用的测试用例: {enabled_case_names}")
    
    return enabled_case_names


def process_test_results(test_results: List[Any]) -> Tuple[Dict[str, Any], Set[str]]:
    """
    处理测试结果，提取结果字典和失败用例集合
    
    Args:
        test_results: 测试结果列表
    
    Returns:
        Tuple[Dict, Set]: (结果字典, 失败用例集合)
    """
    results_dict = {}
    failed_cases = set()
    
    for result in test_results:
        test_case_name = getattr(result, 'test_case', 'Unknown')
        test_result = getattr(result, 'result', None)
        
        if test_result:
            result_name = getattr(test_result, 'name', str(test_result))
            results_dict[test_case_name] = test_result
            
            # 打印非跳过的结果
            if result_name != SKIP_RESULT:
                pprint(result)
                
            # 收集失败的测试用例
            if result_name == FAIL_RESULT:
                failed_cases.add(test_case_name)
                logging.warning(f"测试用例失败: {test_case_name}")
    
    logging.info(f"处理完成 {len(results_dict)} 个测试结果，其中 {len(failed_cases)} 个失败")
    return results_dict, failed_cases


def calculate_execution_time(start_time: float, end_time: float) -> float:
    """
    计算执行时间
    
    Args:
        start_time: 开始时间戳
        end_time: 结束时间戳
    
    Returns:
        float: 执行时间（秒）
    """
    execution_time = end_time - start_time
    logging.info(f"执行耗时: {execution_time:.2f} 秒")
    return execution_time


def validate_file_exists(file_path: str, file_description: str = "文件") -> bool:
    """
    验证文件是否存在
    
    Args:
        file_path: 文件路径
        file_description: 文件描述，用于日志
    
    Returns:
        bool: 文件是否存在
    
    Raises:
        FileNotFoundError: 文件不存在时抛出异常
    """
    path = Path(file_path)
    if not path.exists():
        error_msg = f"{file_description}不存在: {file_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    logging.debug(f"{file_description}存在: {file_path}")
    return True


def get_config_paths(base_dir: Optional[str] = None) -> Tuple[str, str]:
    """
    获取配置文件路径
    
    Args:
        base_dir: 基础目录，如果不提供则使用当前脚本所在目录
    
    Returns:
        Tuple[str, str]: (主配置文件路径, 任务配置文件路径)
    
    Raises:
        FileNotFoundError: 配置文件不存在时抛出异常
    """
    if base_dir is None:
        # 获取调用此函数的文件所在目录
        import inspect
        frame = inspect.currentframe().f_back
        caller_file = frame.f_globals['__file__']
        current_dir = Path(caller_file).parent
    else:
        current_dir = Path(base_dir)
    
    main_config_path = current_dir / 'test_framework' / 'config' / 'main_config.json'
    task_config_path = current_dir / 'test_framework' / 'config' / 'task_config.json'
    
    # 验证文件是否存在
    validate_file_exists(str(main_config_path), "主配置文件")
    validate_file_exists(str(task_config_path), "任务配置文件")
    
    return str(main_config_path), str(task_config_path)


def check_environment_result(env_results: List[Any]) -> bool:
    """
    检查环境检查结果
    
    Args:
        env_results: 环境检查结果列表
    
    Returns:
        bool: 环境是否准备就绪
    """
    for result in env_results:
        test_case = getattr(result, 'test_case', '')
        if test_case == ENVIRONMENT_CHECK_CASE:
            test_result = getattr(result, 'result', None)
            if test_result:
                env_status = getattr(test_result, 'name', str(test_result))
                logging.info(f"环境检查结果: {env_status}")
                return env_status == PASS_RESULT
    
    logging.warning("未找到环境检查结果")
    return False


def format_test_summary(results_dict: Dict[str, Any], failed_cases: Set[str], execution_time: float) -> str:
    """
    格式化测试摘要信息
    
    Args:
        results_dict: 测试结果字典
        failed_cases: 失败用例集合
        execution_time: 执行时间
    
    Returns:
        str: 格式化的摘要信息
    """
    total_cases = len(results_dict)
    failed_count = len(failed_cases)
    passed_count = total_cases - failed_count
    
    summary = f"""
测试执行摘要:
==================
总测试用例: {total_cases}
通过用例: {passed_count}
失败用例: {failed_count}
执行时间: {execution_time:.2f} 秒
通过率: {(passed_count/total_cases*100):.2f}% (如果总数大于0)
"""
    
    if failed_cases:
        summary += f"\n失败用例列表:\n{', '.join(failed_cases)}"
    
    return summary


def safe_execute(func, *args, error_message: str = "执行函数时发生错误", **kwargs):
    """
    安全执行函数，捕获异常并记录日志
    
    Args:
        func: 要执行的函数
        *args: 函数参数
        error_message: 错误消息
        **kwargs: 函数关键字参数
    
    Returns:
        函数执行结果，如果发生异常则返回None
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"{error_message}: {e}")
        return None


def create_directory_if_not_exists(directory_path: str) -> bool:
    """
    如果目录不存在则创建目录
    
    Args:
        directory_path: 目录路径
    
    Returns:
        bool: 创建是否成功
    """
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        logging.debug(f"目录已确保存在: {directory_path}")
        return True
    except Exception as e:
        logging.error(f"创建目录失败 {directory_path}: {e}")
        return False