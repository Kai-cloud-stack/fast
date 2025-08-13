# _*_coding:utf-8_*_
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : temp_main
@date     : 2025/8/13 
@author   : <kai.ren@freetech.com>
@describe : 优化后的测试框架主程序
"""
import json
import logging
import os
import time
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Optional

from test_framework.checkers.environment_checker import EnvironmentChecker
from test_framework.interfaces.canoe_interface import CANoeInterface
from test_framework.services.notification_service import NotificationService

# 常量定义
ENVIRONMENT_CHECK_CASE = 'Check_Environment'
PASS_RESULT = 'PASS'
FAIL_RESULT = 'FAIL'
SKIP_RESULT = 'SKIP'
DEFAULT_ENCODING = 'utf-8'

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_task_config(task_config_path: str) -> Dict:
    """加载任务配置文件"""
    try:
        with open(task_config_path, encoding=DEFAULT_ENCODING) as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"任务配置文件未找到: {task_config_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"任务配置文件JSON格式错误: {e}")
        raise


def run_tasks(canoe_obj: CANoeInterface, task_config_path: str) -> List:
    """执行测试任务"""
    try:
        # 加载任务配置
        task_config = load_task_config(task_config_path)
        
        # 获取启用的测试用例
        enabled_tasks = [task for task in task_config['test_cases'] if task['enabled']]
        enabled_case_names = [task['name'] for task in enabled_tasks]
        
        if not enabled_case_names:
            logging.warning("没有启用的测试用例")
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


def load_main_config(config_path: str) -> Dict:
    """加载主配置文件"""
    try:
        with open(config_path, encoding=DEFAULT_ENCODING) as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"主配置文件未找到: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"主配置文件JSON格式错误: {e}")
        raise


def check_environment(canoe_obj: CANoeInterface) -> bool:
    """检查环境是否准备就绪"""
    try:
        tester = EnvironmentChecker(canoe_obj, None)
        tester.check_environment()
        env_results = tester.get_check_results()
        
        for result in env_results:
            if result.test_case == ENVIRONMENT_CHECK_CASE:
                env_status = result.result.name
                logging.info(f"环境检查结果: {env_status}")
                return env_status == PASS_RESULT
        
        logging.warning("未找到环境检查结果")
        return False
        
    except Exception as e:
        logging.error(f"环境检查时发生错误: {e}")
        return False


def process_test_results(test_results: List) -> Dict:
    """处理测试结果"""
    results_dict = {}
    failed_cases = set()
    
    for result in test_results:
        results_dict[result.test_case] = result.result
        
        # 打印非跳过的结果
        if result.result.name != SKIP_RESULT:
            pprint(result)
            
        # 收集失败的测试用例
        if result.result.name == FAIL_RESULT:
            failed_cases.add(result.test_case)
    
    return results_dict, failed_cases


def send_notification(config: Dict, results: Dict, failed_cases: set):
    """发送通知"""
    try:
        email_config = config.get('email')
        wechat_config = config.get('wechat')
        
        if not email_config:
            logging.warning("未配置邮件通知")
            return
            
        notification_service = NotificationService(email_config, wechat_config)
        notification_service.send_email(
            subject='测试执行结果',
            results=results,
            failed_keywords=failed_cases
        )
        logging.info("通知发送成功")
        
    except Exception as e:
        logging.error(f"发送通知时发生错误: {e}")


def main(main_config_path: str, task_config_path: str):
    """主函数"""
    try:
        # 加载配置
        config = load_main_config(main_config_path)
        
        # 初始化CANoe接口
        canoe = CANoeInterface(canoe_config=config)
        
        # 检查环境
        if not check_environment(canoe):
            logging.error("环境检查失败，终止执行")
            return
        
        # 执行测试任务
        start_time = time.time()
        test_results = run_tasks(canoe, task_config_path)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logging.info(f"测试执行耗时: {execution_time:.2f} 秒")
        
        # 处理测试结果
        results_dict, failed_cases = process_test_results(test_results)
        
        # 发送通知
        send_notification(config, results_dict, failed_cases)
        
        logging.info("测试执行完成")
        
    except Exception as e:
        logging.error(f"主程序执行时发生错误: {e}")
        raise


def get_config_paths() -> tuple[str, str]:
    """获取配置文件路径"""
    # 使用相对路径，基于当前脚本所在目录
    current_dir = Path(__file__).parent
    main_config_path = current_dir / 'test_framework' / 'config' / 'main_config.json'
    task_config_path = current_dir / 'test_framework' / 'config' / 'task_config.json'
    
    # 验证文件是否存在
    if not main_config_path.exists():
        raise FileNotFoundError(f"主配置文件不存在: {main_config_path}")
    if not task_config_path.exists():
        raise FileNotFoundError(f"任务配置文件不存在: {task_config_path}")
    
    return str(main_config_path), str(task_config_path)


if __name__ == '__main__':
    try:
        main_config_path, task_config_path = get_config_paths()
        logging.info("开始执行测试框架")
        main(main_config_path, task_config_path)
    except Exception as e:
        logging.error(f"程序执行失败: {e}")
        exit(1)


