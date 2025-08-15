# _*_coding:utf-8_*_
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : temp_main
@date     : 2025/8/13 
@author   : <kai.ren@freetech.com>
@describe : 优化后的测试框架主程序
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from test_framework.utils import (
    load_main_config,
    execute_complete_test_workflow,
    validate_test_configuration,
    execute_multi_tse_workflow
)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main(main_config_path: str, task_config_path: str = None, execution_mode: str = 'single'):
    """主函数
    
    Args:
        main_config_path: 主配置文件路径
        task_config_path: 任务配置文件路径（单TSE模式需要）
        execution_mode: 执行模式，'single'为单TSE模式，'multi'为多TSE模式
    """
    try:
        if execution_mode == 'multi':
            # 多TSE执行模式
            logging.info("开始执行多TSE文件测试")
            success = execute_multi_tse_workflow(main_config_path, task_config_path)
            
            if success:
                logging.info("多TSE文件测试执行完成")
            else:
                logging.error("多TSE文件测试执行失败")
                
        else:
            # 单TSE执行模式（原有逻辑）
            if not task_config_path:
                logging.error("单TSE模式需要提供任务配置文件路径")
                return
                
            logging.info("开始执行单TSE文件测试")
            
            # 加载配置
            config = load_main_config(main_config_path)
            
            # 验证配置
            if not validate_test_configuration(config, task_config_path):
                logging.error("配置验证失败，终止执行")
                return
            
            # 创建CANoe接口对象
            from test_framework.interfaces.canoe_interface import CANoeInterface
            canoe_obj = CANoeInterface(config)
            
            # 执行完整的测试工作流程
            workflow_result = execute_complete_test_workflow(canoe_obj, task_config_path, config)
            
            if workflow_result['success']:
                logging.info("单TSE文件测试执行完成")
                if workflow_result['failed_cases']:
                    logging.warning(f"存在失败的测试用例: {workflow_result['failed_cases']}")
            else:
                logging.error("单TSE文件测试执行失败")
            
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        raise


if __name__ == '__main__':
    # 直接在脚本中设置参数，不从外部传入
    execution_mode = 'multi'  # 执行模式: 'single' 或 'multi'
    main_config_path = 'test_framework/config/main_config.json'  # 主配置文件路径
    task_config_path = 'test_framework/config/task_config.json'  # 任务配置文件路径
    verbose = True  # 是否启用详细日志输出
    
    # 设置日志级别
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        logging.info(f"开始执行测试框架 - 模式: {execution_mode}")
        logging.info(f"主配置文件: {main_config_path}")
        if task_config_path:
            logging.info(f"任务配置文件: {task_config_path}")
        
        main(main_config_path, task_config_path, execution_mode)
        
    except Exception as e:
        logging.error(f"程序执行失败: {e}")
        exit(1)


